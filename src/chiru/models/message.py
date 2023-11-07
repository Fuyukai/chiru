import enum

import arrow
import attr
from cattrs import Converter
from cattrs.gen import make_dict_structure_fn, override

from chiru.models.base import DiscordObject, StatefulMixin
from chiru.models.member import Member, RawMember
from chiru.models.user import RawUser, User


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


@attr.s()
class RawMessage(DiscordObject):
    """
    A single message sent in a channel.
    """

    @classmethod
    def configure_converter(cls, converter: Converter):
        for klass in (RawMessage, Message):
            converter.register_structure_hook(
                klass,
                make_dict_structure_fn(
                    klass,
                    converter,
                    _cattrs_forbid_extra_keys=False,
                ),
            )

        converter.register_structure_hook(MessageType, lambda it, klass: MessageType(it))

    #: The Snowflake ID of the channel that this message was sent in.
    channel_id: int = attr.ib()

    #: The author :class:`.RawUser` for this message.
    author: RawUser = attr.ib()

    #: The content of this message.
    content: str = attr.ib()

    #: The timestamp for this message.
    timestamp: arrow.Arrow = attr.ib()

    #: The type of message this is.
    type: MessageType = attr.ib()

    #: The member data for this message. May be empty for non-Guild members or webhooks.
    member: RawMember | None = attr.ib(default=None)


@attr.s(slots=True)
class Message(RawMessage, StatefulMixin):
    #: The author :class:`.User` for this message.
    author: User = attr.ib()

    #: The member data for this message. May be empty for non-Guild members or webhooks.
    member: Member | None = attr.ib(default=None)
