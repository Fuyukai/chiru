from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import anyio
from anyio import Event

from chiru.event.model import GuildMemberChunk
from chiru.gateway.collection import GatewayCollection
from chiru.gateway.event import GatewayMemberChunkRequest
from chiru.models.guild import Guild

if TYPE_CHECKING:
    from chiru.event.dispatcher import StatefulEventDispatcher

# when I first wrote Curious' chunker in 2017, things were a lot different.
# message events didn't have member info, so you *had* to cache all guild members to do anything.
# this was fine becausee the guild member request payload supported having multiple ids...
# but now you can only send one guild ID at a time.
#
# there's a few ways to get around this; the /members endpoint has a 10/10 ratelimit so alongside
# the 120/60 ratelimit for the gateway, we could achieve much higher throughput.
#
# but luckily... most of the member data that we need is already there. message object now contain
# full member data on their ``member`` field, and contain member data in their ``mentions`` field
# (to some degree). so chunking is less essential than it was in 2017, as we can use that data as
# the secondary source, and not block the entire bot on guild member chunking.


logger = logging.getLogger(__name__)


class GuildChunker:
    """
    Chunks the members of incoming streamed guilds.

    This class is intrinsically tied to :class:`.StatefulEventDispatcher`, and can't reasonably
    be used outside of it.
    """

    def __init__(
        self,
        dispatcher: StatefulEventDispatcher,
        shard_count: int,
    ):
        self._dispatcher = dispatcher

        self._pending_chunk_write, self._pending_chunk_recv = anyio.create_memory_object_stream[
            tuple[int, GatewayMemberChunkRequest]
        ](math.inf)

        self._guild_fully_chunked: dict[int, Event] = {}

    async def wait_for_guild(self, guild_id: int):
        """
        Waits for a guild to be fully chunked.
        """

        if guild_id not in self._guild_fully_chunked:
            raise ValueError(f"No such guild: {guild_id}")

        return await self._guild_fully_chunked[guild_id].wait()

    async def send_to_outgoing(
        self,
        collection: GatewayCollection,
    ):
        async with self._pending_chunk_recv:
            while True:
                shard_id, msg = await self._pending_chunk_recv.receive()
                await collection.send_to_shard(shard_id, msg)

    def handle_member_chunk(self, shard_id: int, evt: GuildMemberChunk):
        """
        Handles a single incoming member chunk.
        """

        # the parser is responsible for actually loading all of the members...
        # this mostly just tracks guilds that are fully chunked

        logger.debug(f"Received chunk {evt.chunk_index + 1} / {evt.chunk_count} for {evt.guild.id}")

        if evt.chunk_index + 1 >= evt.chunk_count:
            logger.debug(f"Guild {evt.guild.id} is fully chunked!")
            self._guild_fully_chunked[evt.guild.id].set()

    def handle_joined_guild(
        self,
        shard_id: int,
        guild: Guild,
    ):
        """
        Handles a single incoming guild.
        """

        if guild.id in self._guild_fully_chunked:
            return

        self._guild_fully_chunked[guild.id] = Event()

        # non-large guilds never need chunking, so set their event immediately
        if not guild.large:
            logger.debug(f"Guild {guild.id} is not large, skipping chunk request")
            self._guild_fully_chunked[guild.id].set()
            return

        logger.debug(f"Guild {guild.id} is large, sending a member chunk request")

        evt = GatewayMemberChunkRequest(guild_id=guild.id, query="", limit=0, presences=False)
        self._pending_chunk_write.send_nowait((shard_id, evt))