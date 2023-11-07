import enum

import attr
import cattr
from cattr import Converter

from chiru.models.base import DiscordObject, StatefulMixin


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
    def configure_converter(cls, converter: Converter):
        for klass in (cls, Channel):
            converter.register_structure_hook(
                klass,
                cattr.gen.make_dict_structure_fn(
                    klass,
                    converter,
                    _cattrs_forbid_extra_keys=False,
                ),
            )

    #: The type of channel this channel is.
    type: ChannelType = attr.ib()

    #: The name of this channel, if any.
    name: str | None = attr.ib()

    #: The guild ID for this channel, if any.
    guild_id: int | None = attr.ib(default=None)

    #: The sorting position for this channel. For DM channels, this will always be zero.
    position: int = attr.ib(default=0)

    #: The topic for this channel, if any.
    topic: str = attr.ib(default=None)

    #: If this channel is NSFW or not. Defaults to False.
    nsfw: bool = attr.ib(default=False)


class Channel(RawChannel, StatefulMixin):
    """
    The stateful version of :class:`.RawChannel`.
    """
