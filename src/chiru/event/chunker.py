from __future__ import annotations

import math
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import NoReturn, final

import anyio
import structlog
from anyio import Event, create_task_group
from structlog.stdlib import BoundLogger

from chiru.event.dispatcher import ChannelDispatcher, DispatchChannel, start_consumer_task
from chiru.event.model import (
    AnyGuildJoined,
    GuildAvailable,
    GuildJoined,
    GuildMemberChunk,
    GuildStreamed,
)
from chiru.gateway.collection import GatewayCollection
from chiru.gateway.event import GatewayMemberChunkRequest

# TODO: Manual per-user chunking.

# when I first wrote Curious' chunker in 2017, things were a lot different.
# message events didn't have member info, so you *had* to cache all guild members to do anything.
# this was fine because the guild member request payload supported having multiple ids...
# but now you can only send one guild ID at a time.
#
# there's a few ways to get around this; the /members endpoint has a 10/10 ratelimit so alongside
# the 120/60 ratelimit for the gateway, we could achieve much higher throughput.
#
# but luckily... most of the member data that we need is already there. message object now contain
# full member data on their ``member`` field, and contain member data in their ``mentions`` field
# (to some degree). so chunking is less essential than it was in 2017, as we can use that data as
# the secondary source, and not block the entire bot on guild member chunking.


logger: BoundLogger = structlog.get_logger(name=__name__)


@final
class GuildChunker:
    """
    Automatically requests member chunks for incoming guilds.
    """

    def __init__(
        self,
    ) -> None:
        self._pending_chunk_write, self._pending_chunk_recv = anyio.create_memory_object_stream[
            tuple[int, GatewayMemberChunkRequest]
        ](math.inf)

        self._guild_fully_chunked: dict[int, Event] = {}

    async def wait_for_guild(self, guild_id: int) -> None:
        """
        Waits for a guild to be fully chunked.
        """

        if guild_id not in self._guild_fully_chunked:
            raise ValueError(f"No such guild: {guild_id}")

        return await self._guild_fully_chunked[guild_id].wait()

    async def send_to_outgoing(
        self,
        *,
        collection: GatewayCollection,
    ) -> NoReturn:
        """
        Runs forever in a loop, receiving outgoing chunking messages from the chunker.
        """

        async with self._pending_chunk_recv:
            async for shard_id, msg in self._pending_chunk_recv:
                await collection.send_to_shard(shard_id, msg)

    async def handle_member_chunk(self, channel: DispatchChannel[GuildMemberChunk]) -> None:
        """
        Event handler that handles all incoming member chunks.
        """

        async for _, evt in channel:
            # the parser is responsible for actually loading all of the members...
            # this mostly just tracks guilds that are fully chunked

            logger.debug(
                "Received member chunk",
                chunk_index=evt.chunk_index,
                chunk_count=evt.chunk_count,
                guild_id=evt.guild.id,
            )

            if evt.chunk_index + 1 >= evt.chunk_count:
                logger.debug("Fully chunked", guild_id=evt.guild.id)
                self._guild_fully_chunked[evt.guild.id].set()

    async def handle_joined_guild(
        self,
        channel: DispatchChannel[AnyGuildJoined],
    ) -> None:
        """
        Event handler that handles all incoming joined guilds.
        """

        async for ctx, evt in channel:
            guild = evt.guild
            if guild.id in self._guild_fully_chunked:
                return

            self._guild_fully_chunked[guild.id] = Event()

            logger.debug("Joined guild", guild=guild.id, large=guild.large)

            # non-large guilds never need chunking, so set their event immediately
            if not guild.large:
                self._guild_fully_chunked[guild.id].set()
                continue

            evt = GatewayMemberChunkRequest(guild_id=guild.id, query="", limit=0, presences=False)
            self._pending_chunk_write.send_nowait((ctx.shard_id, evt))


@asynccontextmanager
async def create_chunker(
    collection: GatewayCollection,
    dispatcher: ChannelDispatcher,
) -> AsyncGenerator[GuildChunker, None]:
    """
    Creates a new :class:`.GuildChunker` that will send outgoing member chunks automatically.

    .. code-block:: python

        async def main():
            dispatcher = ChannelDispatcher()

            async with (
                open_bot(TOKEN) as bot,
                bot.start_receiving_events() as collection,
                create_chunker(collection, dispatcher)
            ):
                await dispatcher.run(bot, collection)

    :param collection: The :class:`.GatewayCollection` to send outgoing member chunk events to.
    :param dispatcher: The :class:`.ChannelDispatcher` to register events into.
    """

    async with create_task_group() as group:
        chunker = GuildChunker()
        p = partial(chunker.send_to_outgoing, collection=collection)
        group.start_soon(p)

        start_consumer_task(group, dispatcher, GuildMemberChunk, chunker.handle_member_chunk)

        for type in (GuildJoined, GuildStreamed, GuildAvailable):
            start_consumer_task(group, dispatcher, type, chunker.handle_joined_guild)

        yield chunker
