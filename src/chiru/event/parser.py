from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

import attr
import structlog

from chiru.cache import ObjectCache
from chiru.event.chunker import GuildChunker
from chiru.event.model import (
    Connected,
    DispatchedEvent,
    GuildAvailable,
    GuildEmojiUpdate,
    GuildJoined,
    GuildMemberAdd,
    GuildMemberChunk,
    GuildMemberRemove,
    GuildMemberUpdate,
    GuildStreamed,
    InvalidGuildChunk,
    MessageCreate,
    MessageUpdate,
    ShardReady,
)
from chiru.gateway.event import GatewayDispatch
from chiru.models.factory import ModelObjectFactory
from chiru.models.guild import GuildEmojis, UnavailableGuild

if TYPE_CHECKING:
    pass

logger: structlog.stdlib.BoundLogger = structlog.get_logger(name=__name__)


@attr.s(slots=True)
class PerShardState:
    is_ready: bool = attr.ib(default=False)
    guilds_remaining: int = attr.ib(default=0)


class CachedEventParser:
    """
    Deals with parsing incoming dispatch events and converting them into high-level events. This
    will cache objects as appropriate to ensure that state (e.g. members) is kept between event
    invocations.

    Each parsing function here is a generator that may yield any number of events, including zero.
    """

    def __init__(
        self,
        cache: ObjectCache,
        shard_count: int,
        chunker: GuildChunker | None = None,
    ) -> None:
        """
        :param cache: The :class:`.ObjectCache` to store the created objects in.
        :param shard_count: The number of shards that the bot is using. Used primarily for handling
            guild streaming and per-shard READY.

        :param chunker: The :class:`.GuildChunker` to use for automatically chunking incoming
            guilds. This may be None if you don't want to have automatic member chunking.

            See :ref:`guild-chunking` for more information.
        """

        self._cache: ObjectCache = cache

        self._chunker: GuildChunker | None = chunker

        #: A list of per-shard shared mutable state.
        self.per_shard_state: list[PerShardState] = [PerShardState()] * shard_count

    def get_parsed_events(
        self, factory: ModelObjectFactory, event: GatewayDispatch
    ) -> list[DispatchedEvent]:
        """
        Gets a list of parsed events from the provided :class:`.GatewayDispatch` gateway event.

        :param factory: The :class:`.ModelObjectFactory` that cached objects will be stored into.
        :param event: The :class:`.GatewayDispatch` event that high-level events will be parsed
            from.
        :return: A list of :class:`.DispatchedEvent` instances that this event produced, if any.
        """

        fn = getattr(self, f"_parse_{event.event_name.lower()}", None)
        if fn is None:
            return []

        return list(fn(event, factory))

    def _parse_ready(
        self,
        event: GatewayDispatch,
        factory: ModelObjectFactory,
    ) -> Iterable[DispatchedEvent]:
        """
        Parses the READY event, which signals that a connection is open.
        """

        guilds = [factory.make_guild(g) for g in event.body["guilds"]]
        shard_state = self.per_shard_state[event.shard_id]
        if len(guilds) <= 0:
            # if there's no guilds for this shard (what?), make sure that the bot doesn't get stuck
            # waiting for guild streams forever.
            shard_state.is_ready = True

            yield Connected()
            yield ShardReady()

        else:
            mapped_guilds = {g.id: g for g in guilds}
            self._cache.guilds = {**mapped_guilds, **self._cache.guilds}

            if not shard_state.is_ready:
                shard_state.guilds_remaining = len(guilds)

            yield Connected()

    def _parse_guild_create(
        self, event: GatewayDispatch, factory: ModelObjectFactory
    ) -> Iterable[DispatchedEvent]:
        """
        Parses a GUILD_CREATE event, either from guild streaming or from joining a new guild.
        """

        created_guild = factory.make_guild(event.body)
        assert not created_guild.unavailable, "what the fuck, discord!"
        assert not isinstance(created_guild, UnavailableGuild)

        guild_existed = created_guild.id in self._cache.guilds
        self._cache.guilds[created_guild.id] = created_guild

        # A few cases here:
        # 1) The guild never existed, not even in stub form. This can happen even during streaming,
        #    so yield a Joined event.
        # 2) The guild did exist, but we haven't fired ready yet. This means we're doing guild
        #    streaming.
        # 2) The guild did exist, but we have fired startup. This means it came available after an
        #    outage.

        if not guild_existed:
            yield GuildJoined(created_guild)
        else:
            per_shard_state = self.per_shard_state[event.shard_id]

            if not per_shard_state.is_ready:
                yield GuildStreamed(created_guild)
                per_shard_state.guilds_remaining -= 1

                if per_shard_state.guilds_remaining <= 0:
                    per_shard_state.is_ready = True
                    yield ShardReady()

            else:
                yield GuildAvailable(created_guild)

        if self._chunker is not None:
            self._chunker.handle_joined_guild(event.shard_id, created_guild)

    def _parse_guild_members_chunk(
        self, event: GatewayDispatch, factory: ModelObjectFactory
    ) -> Iterable[DispatchedEvent]:
        """
        Parses a single incoming member chunk.
        """

        guild_id = int(event.body["guild_id"])

        if event.body.get("not_found"):
            yield InvalidGuildChunk(guild_id=guild_id)
            return

        guild = factory.object_cache.get_available_guild(guild_id)
        if guild is None:
            logger.warning("Sent member chunk for invalid guild", guild_id=guild_id)
            return

        members = [factory.make_member(m) for m in event.body["members"]]
        for member in members:
            guild.members._members[member.id] = member

        evt = GuildMemberChunk(
            guild=guild,
            members=members,
            chunk_index=event.body["chunk_index"],
            chunk_count=event.body["chunk_count"],
            nonce=event.body.get("nonce"),
        )

        if self._chunker:
            self._chunker.handle_member_chunk(event.shard_id, evt)

        yield evt

    @staticmethod
    def _parse_message_create(
        event: GatewayDispatch, factory: ModelObjectFactory
    ) -> Iterable[DispatchedEvent]:
        message = factory.make_message(event.body)

        # backfill member data from the message, in case we couldn't chunk.

        if (guild := message.guild) is not None:
            # we already constructed the member object in the message, it's a waste to do it twice,
            # so just copy over the field data instead of making a stateful one.

            mentions: list[dict[str, Any]] = event.body["mentions"]
            for mention in mentions:
                # kinda jank field. this is a user object with an additional "member" field.
                mention_member = mention.pop("member")
                mention_user = factory.make_user(mention)
                guild.members._backfill_member_data(factory, mention_member, mention_user)

            guild.members._backfill_member_data(factory, event.body["member"], message.raw_author)

        yield MessageCreate(message=message)

    @staticmethod
    def _parse_message_update(
        event: GatewayDispatch,
        factory: ModelObjectFactory,
    ) -> Iterable[DispatchedEvent]:
        message = factory.make_message(event.body)

        yield MessageUpdate(message=message)

    def _parse_guild_member_add(
        self, event: GatewayDispatch, factory: ModelObjectFactory
    ) -> Iterable[DispatchedEvent]:
        guild_id = int(event.body["guild_id"])
        guild = self._cache.get_available_guild(guild_id)
        assert guild, "STOP SENDING US INVALID GUILDS"
        member = guild.members._backfill_member_data(factory, event.body)

        yield GuildMemberAdd(guild=member.guild, member=member)

    def _parse_guild_member_remove(
        self, event: GatewayDispatch, factory: ModelObjectFactory
    ) -> Iterable[DispatchedEvent]:
        guild_id = int(event.body["guild_id"])
        guild = self._cache.get_available_guild(guild_id)
        user = factory.make_user(event.body["user"])

        yield GuildMemberRemove(guild_id=guild_id, user=user, guild=guild)

    def _parse_guild_member_update(
        self, event: GatewayDispatch, factory: ModelObjectFactory
    ) -> Iterable[DispatchedEvent]:
        guild_id = int(event.body["guild_id"])
        guild = self._cache.get_available_guild(guild_id)

        assert guild, "received member update for an invalid guild!"
        created_member = guild.members._backfill_member_data(factory, event.body)
        yield GuildMemberUpdate(member=created_member)

    def _parse_guild_emojis_update(
        self, event: GatewayDispatch, factory: ModelObjectFactory
    ) -> Iterable[DispatchedEvent]:
        guild_id = int(event.body["guild_id"])
        guild = self._cache.get_available_guild(guild_id)

        assert guild, "received emoji update for an invalid guild!"
        previous_emojis = list(guild.emojis.values())
        new_emojis = GuildEmojis.from_update_packet(event.body["emojis"], factory)
        guild.emojis = new_emojis

        yield GuildEmojiUpdate(
            guild=guild, previous_emojis=previous_emojis, new_emojis=list(new_emojis.values())
        )
