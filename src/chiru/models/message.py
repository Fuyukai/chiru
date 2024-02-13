from __future__ import annotations

import enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypeAlias, cast

import attr
from cattrs import Converter
from cattrs.gen import make_dict_structure_fn, override
from whenever import UTCDateTime

from chiru.models.base import DiscordObject, StatefulMixin
from chiru.models.channel import AnyGuildChannel, TextualChannel
from chiru.models.embed import Embed
from chiru.models.emoji import UnicodeEmoji
from chiru.models.member import Member, RawMember
from chiru.models.user import RawUser, User

if TYPE_CHECKING:
    from chiru.models.guild import Guild
else:
    Guild: TypeAlias[object] = object


# If only Python enums didn't suck!
class MessageType(enum.Enum):
    """
    Represents the type of a message.
    """

    #: The default (i.e. user message) type.
    DEFAULT = 0

    # 1 through 5 are groups only
    #: The recipient add type, used when a recipient is added to a group.
    RECIPIENT_ADD = 1

    #: The recipient remove type, used when a recipient is added to a group.
    RECIPIENT_REMOVE = 2

    #: The call type, used when a call is started.
    CALL = 3

    #: The channel name change type, used when a group channel name is changed.
    CHANNEL_NAME_CHANGE = 4

    #: The channel icon change type, used when a group channel icon is changed.
    CHANNEL_ICON_CHANGE = 5

    #: The channel pinned message type, used when a message is pinned.
    CHANNEL_PINNED_MESSAGE = 6

    #: The guild member join type, used when a member joins a guild.
    GUILD_MEMBER_JOIN = 7

    # TODO: Document these
    USER_PREMIUM_GUILD_SUBSCRIPTION = 8
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_1 = 9
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_2 = 10
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_3 = 11
    CHANNEL_FOLLOW_ADD = 12
    GUILD_DISCOVERY_DISQUALIFIED = 14
    GUILD_DISCOVERY_REQUALIFIED = 15
    GUILD_DISCOVERY_GRACE_PERIOD_INITIAL_WARNING = 16
    GUILD_DISCOVERY_GRACE_PERIOD_FINAL_WARNING = 17
    THREAD_CREATED = 18
    REPLY = 19
    APPLICATION_COMMAND = 20
    THREAD_STARTER_MESSAGE = 21
    GUILD_INVITE_REMINDER = 22
    CONTEXT_MENU_COMMAND = 23
    AUTO_MODERATION_ACTION = 24
    ROLE_SUBSCRIPTION_PURCHASE = 25
    INTERACTION_PREMIUM_UPSELL = 26
    STAGE_START = 27
    STAGE_END = 28
    STAGE_SPEAKER = 29
    # no 30
    STAGE_TOPIC = 31
    GUILD_APPLICATION_PREMIUM_SUBSCRIPTION = 32


@attr.s(slots=True, kw_only=True)
class ReactionCountDetails:
    """
    Detailed statistics for a single reaction to a message.
    """

    #: The counter for super reactions within this reaction.
    burst: int = attr.ib()

    #: The counter for normal reactions within this reaction.
    normal: int = attr.ib()


@attr.s(kw_only=True)
class RawMessageReaction:
    """
    A single reaction for a message.
    """

    @staticmethod
    def decode_emoji_reference(data: Any, type: type[Any]) -> UnicodeEmoji | int:  # noqa: D102
        if (id := data["id"]) is not None:
            return cast(int, id)

        return UnicodeEmoji(data["name"])

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:  # noqa: D102
        converter.register_structure_hook(
            cls,
            make_dict_structure_fn(
                cls,
                converter,
                _cattrs_forbid_extra_keys=False,
                emoji=override(struct_hook=RawMessageReaction.decode_emoji_reference),
            ),
        )

    #: The counter for this reaction, as seen alongside the emoji.
    count: int = attr.ib()

    #: The extra details for this reaction's counter, subdivided into the super reaction counter
    #: and the regular reaction counter.
    count_details: ReactionCountDetails = attr.ib()

    #: If True, then the current user has used this reaction on a message.
    me: bool = attr.ib()

    #: If True, then the current user has used this reaction on a message as a super reaction.
    me_burst: bool = attr.ib()

    #: A reference to the emoji object that this reaction is for. This may either be the emoji ID
    #: for custom emojis, or the unicode text for the emoji if it is not a custom emoji.
    emoji: UnicodeEmoji | int = attr.ib()


@attr.s(kw_only=True)
class RawMessage(DiscordObject):
    """
    A single message sent in a channel.
    """

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:  # noqa: D102
        for klass in (RawMessage, Message):
            converter.register_structure_hook(
                klass,
                make_dict_structure_fn(
                    klass,
                    converter,
                    raw_author=override(rename="author"),
                    raw_member=override(rename="member"),
                    _cattrs_forbid_extra_keys=False,
                ),
            )

        converter.register_structure_hook(MessageType, lambda it, klass: MessageType(it))

    #: The Snowflake ID of the channel that this message was sent in.
    channel_id: int = attr.ib()

    #: The Snowflake ID of the guild that this message was sent in, if any. This is null for
    #: messages created or retrieved over the HTTP API.
    guild_id: int | None = attr.ib(default=None)

    #: The :class:`.RawUser` that sent this message. Immutable snapshot generated by Discord.
    raw_author: RawUser = attr.ib()

    #: The member data for this message. May be empty for non-Guild members or webhooks.
    #: This is an immutable snapshot sent by Discord in some events, and may be outdated if the
    #: current member has changed their details since this message was sent.
    raw_member: RawMember | None = attr.ib(default=None)

    #: The textual content of this message. This may be empty in the case that a message has only
    #: embeds or attachments.
    content: str = attr.ib()

    #: The list of :class:`.Embed` instances contained within this message.
    embeds: list[Embed] = attr.ib(factory=list)

    #: The list of :class:`.RawMessageReaction` instances to this message.
    reactions: list[RawMessageReaction] = attr.ib(factory=list)

    # not overridden in the inherited object because mentions may not be in the guild still.
    #: The list of :class:`.RawUser` instances that this message mentions.
    mentions: list[RawUser] = attr.ib()

    #: The timestamp for this message.
    timestamp: UTCDateTime = attr.ib()

    #: The type of message this is.
    type: MessageType = attr.ib()


@attr.s(slots=False)
class Message(RawMessage, StatefulMixin):
    """
    The stateful variant of :class:`.RawMessage`.
    """

    #: The :class:`.User` that sent this message. Immutable snapshot generated by Discord.
    raw_author: User = attr.ib()

    @property
    def guild(self) -> Guild | None:
        """
        Gets the guild that this message was sent in, if any.

        :rtype: :class:`.Guild` | None
        """

        if self.guild_id is not None:
            return self._client.object_cache.get_available_guild(self.guild_id)

        if isinstance(self.channel, AnyGuildChannel):
            self.guild_id: int | None = self.channel.guild_id
            return self.channel.guild

        return None

    @cached_property
    def channel(self) -> TextualChannel:
        """
        Gets the channel that this message is for.
        """

        if self.guild_id:
            guild = self._client.object_cache.get_available_guild(self.guild_id)
            if guild is not None:
                return cast(TextualChannel, guild.channels[self.channel_id])

        if channel := self._client.object_cache.find_channel(self.channel_id):
            return cast(TextualChannel, channel)

        raise RuntimeError(f"Couldn't find channel {self.channel_id}")

    @property
    def author(self) -> User | Member:
        """
        The author of this message. May be either a :class:`.User` (if this message is in a
        DM channel) or a :class:`.Member` (if this message is in a guild channel).

        This should be preferred over :attr:`.RawMessage.raw_member` as this will look up the
        member from the cache which has the latest version of the member data.
        """

        if not self.channel.guild_id:
            return self.raw_author

        assert isinstance(
            self.channel, AnyGuildChannel
        ), "guild_id exists but channel is not a guild channel?"

        guild = self.channel.guild
        member = guild.members.get(self.raw_author.id)
        if not member:
            # kicked?
            return self.raw_author

        return member

    async def delete(self) -> None:
        """
        Deletes this individual message from the channel.
        """

        # TODO: local permissions check
        await self._client.http.delete_message(channel_id=self.channel_id, message_id=self.id)
