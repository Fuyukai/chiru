import abc
from collections.abc import Collection, Iterable
from typing import final

import attr

from chiru.models.channel import BaseChannel, RawChannel, TextualChannel
from chiru.models.emoji import RawCustomEmoji
from chiru.models.guild import Guild
from chiru.models.member import Member
from chiru.models.message import Message
from chiru.models.presence import Presence
from chiru.models.role import Role
from chiru.models.user import User

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


@attr.s(str=True, slots=True)
@final
class Connected(DispatchedEvent):
    """
    Published when a single shard has successfully connected to the gateway.
    """


@attr.s(str=True, slots=True)
@final
class ShardReady(DispatchedEvent):
    """
    Published when a single shard has streamed all guilds.
    """


@attr.s(str=True, slots=True)
@final
class Ready(DispatchedEvent):
    """
    Published when all shards are ready.
    """


class AnyGuildJoined(DispatchedEvent, abc.ABC):
    """
    Base type for any event that concerns joining a guild.
    """

    guild: Guild


@attr.s(slots=True, frozen=True)
@final
class GuildStreamed(AnyGuildJoined):
    """
    Published when a guild has been streamed during gateway startup.
    """

    #: The guild that has just been streamed.
    guild: Guild = attr.ib()


@attr.s(slots=True, frozen=True)
@final
class GuildJoined(AnyGuildJoined):
    """
    Published when a bot joins a guild during non-startup operation.
    """

    #: The guild that has just been joined.
    guild: Guild = attr.ib()


@attr.s(slots=True, frozen=True)
@final
class GuildAvailable(AnyGuildJoined):
    """
    Published when a guild becomes available e.g. after an outage and not during startup.
    """

    #: The guild that has just become available.
    guild: Guild = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class InvalidGuildChunk(DispatchedEvent):
    """
    Published when a guild chunk request failed.
    """

    #: The (invalid) ID of the guild that was requested.
    guild_id: int = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
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


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class GuildMemberAdd(DispatchedEvent):
    """
    Published when a new member joins a guild.
    """

    #: The guild that this member joined.
    guild: Guild = attr.ib()

    #: The new member that just joined.
    member: Member = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class GuildMemberRemove(DispatchedEvent):
    """
    Published when a user is removed from a guild.
    """

    #: The ID of the guild that this user was removed from.
    guild_id: int = attr.ib()

    #: The user data for the user that was just removed.
    user: User = attr.ib()

    #: If the provided member was cached, then the :class:`.Member` object that was previously
    #: cached.
    cached_member: Member | None = attr.ib()

    #: The guild object that the user was removed from, if it is available.
    guild: Guild | None = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GuildMemberUpdate(DispatchedEvent):
    """
    Published when a member updates information about their profile in a guild.
    """

    #: The old member that was replaced, if any.
    old_member: Member | None = attr.ib()

    #: The member that was updated.
    member: Member = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GuildEmojiUpdate(DispatchedEvent):
    """
    Published when guilds have their emojis updated.
    """

    #: The guild that the emojis were updated for.
    guild: Guild = attr.ib()

    #: The list of emojis that the guild previously had.
    previous_emojis: list[RawCustomEmoji] = attr.ib()

    #: The new list of emojis that the guild now has.
    new_emojis: list[RawCustomEmoji] = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class MessageCreate(DispatchedEvent):
    """
    Published when a message is created within a channel.

    The content field of messages with this event will be empty if the bot user does not have the
    ``MESSAGE_CONTENT`` intent (enabled by default).
    """

    #: The message that was actually created.
    message: Message = attr.ib()

    @property
    def channel(self) -> TextualChannel:
        """
        Gets the channel that this message was created in.
        """

        return self.message.channel

    @property
    def author(self) -> User | Member:
        """
        Gets the author that sent the message.
        """

        return self.message.author


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class MessageUpdate(DispatchedEvent):
    """
    Published when a message is updated within a channel (i.e. edited).

    .. warning::

        The message objects here may be missing additional data that would otherwise be included
        for regular message creation events.
    """

    #: The *new* message that was the result of the update.
    message: Message = attr.ib()

    @property
    def channel(self) -> TextualChannel:
        """
        Getts the channel that this message was updated within.
        """

        return self.message.channel


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class MessageDelete(DispatchedEvent):
    """
    Published when a single message is deleted within a channel.
    """

    #: The ID of the message that was deleted.
    message_id: int = attr.ib()

    #: The channel that the message was deleted from.
    channel: BaseChannel = attr.ib()

    #: The guild that the channel was in, if any.
    guild: Guild | None = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class MessageBulkDelete(DispatchedEvent):
    """
    Published when multiple messages are deleted simultaneously in a single channel.
    """

    #: The list of IDs of the deleted messages.
    messages: list[int] = attr.ib()

    #: The channel that the messages were deleted from.
    channel: BaseChannel = attr.ib()

    #: The guild that the channel was in, if any.
    guild: Guild | None = attr.ib()

    def as_single_events(self) -> Iterable[DispatchedEvent]:
        """
        Returns a generator that yields every message in this event as a single
        :class:`.MessageDelete` event.
        """

        for id in self.messages:
            yield MessageDelete(message_id=id, channel=self.channel, guild=self.guild)


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class ChannelCreate(DispatchedEvent):
    """
    Published when a single channel is created.

    .. note::

        This event is always fired if a user sends a direct message for the first time within
        a bot's individual *session*. It does not mean a new channel has been created.
    """

    #: The newly created :class:`.BaseChannel`.
    channel: BaseChannel = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class ChannelUpdate(DispatchedEvent):
    """
    Published when a single channel is updated.
    """

    #: The old :class:`.BaseChannel` object, if any existed and was cached.
    #: This may be None for old DM channels.
    old_channel: BaseChannel | None = attr.ib()

    #: The updated :class:`.BaseChannel` object.
    new_channel: BaseChannel = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class ChannelDelete(DispatchedEvent):
    """
    Published when a single channel is deleted.
    """

    #: The locally cached version of the channel, if it existed.
    old_channel: BaseChannel | None = attr.ib()

    #: The raw channel object that was carried along with the dispatched ``CHANNEL_DELETE`` event.
    dispatch_channel: RawChannel = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class PresenceUpdate(DispatchedEvent):
    """
    Published a single member's presence changes.
    """

    #: The :class:`.Guild` that this event was received in.
    guild: Guild = attr.ib()

    #: The ID of the user that this presence was for.
    user_id: int = attr.ib()

    #: The new presence for the member.
    presence: Presence = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class BulkPresences(DispatchedEvent):
    """
    Published when a large chunk of presences is received. This is published in one of three
    situations:

    1. When a new guild is joined (i.e. after a ``GUILD_JOINED``, ``GUILD_STREAMED``, or
       ``GUILD_AVAILABLE``).
    2. When a guild member chunk is received.
    3. (Rarely) when the (undocumented) ``PRESENCES_REPLACE`` event is received.
    """

    #: The guild that this is a set of presences for.
    guild: Guild = attr.ib()

    #: The collection of :class:`.PresenceUpdate` events that were created from the newly joined
    #: guild. This will always be non-empty.
    child_events: Collection[PresenceUpdate] = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class RoleCreate(DispatchedEvent):
    """
    Published when a role is created in a guild.
    """

    #: The guild that this role was created in.
    guild: Guild = attr.ib()

    #: The role that was created.
    role: Role = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class RoleUpdate(DispatchedEvent):
    """
    Published when a role is updated in a guild.
    """

    #: The guild that this role was updated in.
    guild: Guild = attr.ib()

    #: The old role object.
    old_role: Role = attr.ib()

    #: The new role object.
    new_role: Role = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class RoleDelete(DispatchedEvent):
    """
    Published when a role is deleted in a guild.
    """

    #: The guild that this role was deleted from.
    guild: Guild = attr.ib()

    #: The old role object.
    removed_role: Role = attr.ib()
