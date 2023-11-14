from typing import final

import attr

from chiru.models.guild import Guild
from chiru.models.member import Member
from chiru.models.message import Message

__all__ = (
    "DispatchedEvent",
    "Connected",
    "ShardReady",
    "Ready",
    "GuildStreamed",
    "GuildAvailable",
    "GuildJoined",
    "InvalidGuildChunk",
    "GuildMemberChunk",
    "MessageCreate",
)


class DispatchedEvent:
    """
    Marker interface for dispatched events.
    """

    __slots__ = ()


@final
@attr.s(str=True, slots=True)
class Connected(DispatchedEvent):
    """
    Published when a single shard has successfully connected to the gateway.
    """


@final
@attr.s(str=True, slots=True)
class ShardReady(DispatchedEvent):
    """
    Published when a single shard has streamed all guilds.
    """


@final
@attr.s(str=True, slots=True)
class Ready(DispatchedEvent):
    """
    Published when all shards are ready.
    """


@final
@attr.s(slots=True, frozen=True)
class GuildStreamed(DispatchedEvent):
    """
    Published when a guild has been streamed during gateway startup.
    """

    #: The guild that has just been streamed.
    guild: Guild = attr.ib()


@final
@attr.s(slots=True, frozen=True)
class GuildJoined(DispatchedEvent):
    """
    Published when a bot joins a guild during non-startup operation.
    """

    #: The guild that has just been joined.
    guild: Guild = attr.ib()


@final
@attr.s(slots=True, frozen=True)
class GuildAvailable(DispatchedEvent):
    """
    Published when a guild becomes available e.g. after an outage and not during startup.
    """

    #: The guild that has just become available.
    guild: Guild = attr.ib()


@final
@attr.s(slots=True, frozen=True, kw_only=True)
class InvalidGuildChunk(DispatchedEvent):
    """
    Published when a guild chunk request failed.
    """

    #: The (invalid) ID of the guild that was requested.
    guild_id: int = attr.ib()


@final
@attr.s(slots=True, frozen=True, kw_only=True)
class GuildMemberChunk(DispatchedEvent):
    """
    Published when a member chunk is returned in response to Guild Request Members.
    """

    #: The guild that this chunk is for.
    guild: Guild = attr.ib()

    #: The members that were updated in this chunk.
    members: list[Member] = attr.ib()

    #: The zero-indexed chunk index in the sequence of member chunks that this specific event is.
    chunk_index: int = attr.ib()

    #: The total number of chunks that are being returned for this guild.
    chunk_count: int = attr.ib()

    #: The nonce returned from Discord, if one was provided in the requesting packet.
    nonce: str | None = attr.ib(default=None)


@final
@attr.s(frozen=True, slots=True, kw_only=True)
class MessageCreate(DispatchedEvent):
    """
    Published when a message is created a channel.
    """

    #: The message that was actually created.
    message: Message = attr.ib()
