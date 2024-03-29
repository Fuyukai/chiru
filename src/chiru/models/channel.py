from __future__ import annotations

import abc
import enum
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Literal, TypeAlias, cast

import attr
import cattr
from cattr import Converter

from chiru.exc import HttpApiRequestError
from chiru.mentions import AllowedMentions
from chiru.models.base import DiscordObject, StatefulMixin
from chiru.models.embed import Embed
from chiru.models.user import RawUser, User

if TYPE_CHECKING:
    from chiru.models.guild import Guild
    from chiru.models.message import Message
else:
    Message: TypeAlias[object] = object
    Guild: TypeAlias[object] = object


class ChannelType(enum.Enum):
    """
    Enumeration of the supported channel types.
    """

    #: A regular guild text channel.
    GUILD_TEXT = 0

    #: A private channel, such as a DM.
    DM = 1

    #: A regular guild voice channel.
    GUILD_VOICE = 2

    #: A group chat.
    GROUP_DM = 3

    #: A category channel; a parent of other channels.
    GUILD_CATEGORY = 4

    #: A news channel that users can follow.
    GUILD_NEWS = 5

    #: A store channel for selling games.
    GUILD_STORE = 6

    #: A temporary subchannel within a news channel.
    GUILD_NEWS_THREAD = 10

    #: A temporary subchannel within a text channel.
    GUILD_PUBLIC_THREAD = 11

    GUILD_PRIVATE_THREAD = 12
    GUILD_STAGE_VOICE = 13
    GUILD_DIRECTORY = 14
    GUILD_FORUM = 15
    GUILD_MEDIA = 16


@attr.s(kw_only=True)
class RawChannel(DiscordObject):
    """
    A single channel - a container of message events.
    """

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:  # noqa: D102
        for klass in (
            cls,
            BaseChannel,
            TextualChannel,
            TextualGuildChannel,
            UnsupportedChannel,
            UnsupportedGuildChannel,
            CategoryChannel,
            DirectMessageChannel,
        ):
            converter.register_structure_hook(
                klass,
                cattr.gen.make_dict_structure_fn(
                    klass,  # type: ignore  # wtf mypy?
                    converter,
                    _cattrs_forbid_extra_keys=False,
                ),
            )

    #: The type of channel this channel is.
    type: ChannelType = attr.ib()

    #: The name of this channel, if any.
    name: str | None = attr.ib(default=None)

    #: The guild ID for this channel, if any.
    guild_id: int | None = attr.ib(default=None)

    #: The sorting position for this channel. For DM channels, this will always be zero.
    position: int = attr.ib(default=0)

    #: The topic for this channel, if any.
    topic: str | None = attr.ib(default=None)

    #: The parent for this channel, if any.
    parent_id: int | None = attr.ib(default=None)

    #: If this channel is NSFW or not. Defaults to False.
    nsfw: bool = attr.ib(default=False)

    #: The list of recipients for this channel. This will be empty if this is not a direct message
    #: channel.
    recipients: Sequence[RawUser] = attr.ib(factory=list)

    #: The ID of the last message that was sent in this channel. This may be None if the channel
    #: has no messages in it.
    #:
    #: .. warning::
    #:
    #:      This may not be a valid message ID if the most recent message was deleted. Consider it
    #:      a cursor rather than absolute truth.
    last_message_id: int | None = attr.ib(default=None)


@attr.s(kw_only=True)
class BaseChannel(RawChannel, StatefulMixin, metaclass=abc.ABCMeta):
    """
    The base class for a single channel, either in a guild or a DM. This is an abstract class;
    see :class:`.TextualChannel`, :class:`.VoiceChannel`, or :class:`.CategoryChannel`.
    """


@attr.s(kw_only=True)
class AnyGuildChannel(BaseChannel, metaclass=abc.ABCMeta):
    """
    Base class for any channel that is within a guild.
    """

    #: The ID of the guild that this channel is in.
    guild_id: int = attr.ib(init=False)

    @property
    def guild(self) -> Guild:
        """
        The :class:`.Guild` for this channel.

        :rtype: :class:`.Guild`
        """

        guild = self._client.object_cache.get_available_guild(self.guild_id)
        assert guild, "missing guild in cache"
        return guild

    @property
    def parent(self) -> CategoryChannel | None:
        """
        Gets the category channel parent of this channel, if any.
        """

        if not self.parent_id:
            return None

        return cast(CategoryChannel, self.guild.channels[self.parent_id])


@attr.s(kw_only=True)
class UnsupportedChannel(BaseChannel):
    """
    Stub class for any channel that is not otherwise supported.
    """


@attr.s(kw_only=True)
class UnsupportedGuildChannel(UnsupportedChannel, AnyGuildChannel):
    """
    Like a :class:`.UnsupportedChannel`, but within a guild.
    """


@attr.s(kw_only=True)
class CategoryChannel(AnyGuildChannel):
    """
    A channel that contains other channels.
    """

    type: Literal[ChannelType.GUILD_CATEGORY] = attr.ib()

    @property
    def children(self) -> Iterable[AnyGuildChannel]:
        """
        An iterable of the channels that this category owns.
        """

        for channel in self.guild.channels.values():
            if channel.parent_id == self.parent_id:
                yield channel


@attr.s(kw_only=True)
class TextualChannel(BaseChannel):
    """
    The base type for a channel that can have messages to sent to it.
    """

    async def get_single_message(
        self,
        message_id: int,
    ) -> Message | None:
        """
        Gets a single message in this channel by ID, or None if there is no such message.
        """

        try:
            return await self._client.http.get_message(
                channel_id=self.id,
                message_id=int(message_id),
                factory=self._client.stateful_factory,
            )
        except HttpApiRequestError as e:
            if e.error_code == 10008:
                return None

            raise

    async def send_message(
        self,
        content: str | None = None,
        embed: Embed | Iterable[Embed] | None = None,
        allowed_mentions: AllowedMentions | None = None,
    ) -> Message:
        """
        Sends a single message to this channel.

        :param content: The textual content to send. Optional if this message contains an embed or
            an attachment(s).

        :param embed: A :class:`.Embed` instance, or iterable of such instances, to send. Optional
            if the message contains regular textual content or attachments.

        :param allowed_mentions: A :class:`.AllowedMentions` instance to control what this message
            is allowed to mention. For more information, see :ref:`allowed-mentions`.

        :rtype: :class:`.Message`
        """

        return await self._client.http.send_message(
            channel_id=self.id,
            content=content,
            embed=embed,
            allowed_mentions=allowed_mentions,
            factory=self._client.stateful_factory,
        )


@attr.s(kw_only=True)
class DirectMessageChannel(TextualChannel):
    """
    A channel that acts as a direct message to another user.
    """

    type: Literal[ChannelType.DM] = attr.ib()

    #: The list of recipients to this channel.
    recipients: Sequence[User] = attr.ib()

    @property
    def other_user(self) -> User:
        """
        Gets the other user in this direct message.
        """

        assert len(self.recipients) == 1, "naughty userbot..."
        return self.recipients[0]


@attr.s(kw_only=True)
class TextualGuildChannel(TextualChannel, AnyGuildChannel):
    """
    Mixin type of both :class:`.TextualChannel` and :class:`.AnyGuildChannel`.
    """

    type: Literal[ChannelType.GUILD_TEXT] = attr.ib()
