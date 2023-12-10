from collections.abc import Iterable
from typing import final

import attr

from chiru.models.channel import BaseChannel, TextualChannel
from chiru.models.emoji import RawCustomEmoji
from chiru.models.guild import Guild
from chiru.models.member import Member
from chiru.models.message import Message
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
@attr.s(slots=True, frozen=True, kw_only=True)
class GuildMemberAdd(DispatchedEvent):
    """
    Published when a new member joins a guild.
    """

    #: The guild that this member joined.
    guild: Guild = attr.ib()

    #: The new member that just joined.
    member: Member = attr.ib()


@final
@attr.s(slots=True, frozen=True, kw_only=True)
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


@final
@attr.s(frozen=True, slots=True, kw_only=True)
class GuildMemberUpdate(DispatchedEvent):
    """
    Published when a member updates information about their profile in a guild.
    """

    #: The old member that was replaced, if any.
    old_member: Member | None = attr.ib()

    #: The member that was updated.
    member: Member = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
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


@final
@attr.s(frozen=True, slots=True, kw_only=True)
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


@final
@attr.s(frozen=True, slots=True, kw_only=True)
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
        :class:`.MessageDelete` event. This allows unifiying the code paths for both individual and
        bulk deletions, like so:

        .. code-block:: python

            async def handle_single_deletion(ctx: EventContext, evt: MessageDelete) -> None:
                ...

            async def handle_bulk_deletion(ctx: EventContext, e: MessageBulkDelete) -> None:
                for evt in e.as_single_events():
                    await handle_single_deletion(ctx, evt)

            dispatcher.add_event_handler(MessageDelete, handle_single_deletion)
            dispatcher.add_event_handler(MessageBulkDelete, handle_bulk_deletion)

        """

        for id in self.messages:
            yield MessageDelete(message_id=id, channel=self.channel, guild=self.guild)


@attr.s(slots=True, frozen=True, kw_only=True)
@final
class ChannelCreate(DispatchedEvent):
    """
    Published when a single channel is created.
    """

    #: The newly created :class:`.BaseChannel`.
    channel: BaseChannel = attr.ib()


@attr.s(slots=True, frozen=True, kw_only=True)
class ChannelUpdate(DispatchedEvent):
    """
    Published when a single channel is updated.
    """

    #: The old :class:`.BaseChannel` object, if any existed and was cached.
    old_channel: BaseChannel | None = attr.ib()

    #: The updated :class:`.BaseChannel` object.
    new_channel: BaseChannel = attr.ib()
