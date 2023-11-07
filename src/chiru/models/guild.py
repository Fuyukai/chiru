from __future__ import annotations

from collections.abc import Iterator, Sequence
from functools import partial
from typing import TYPE_CHECKING, Any, Mapping, Type, TypeVar, final

import attr
import cattr
from cattr import Converter, override

from chiru.models.base import DiscordObject, StatefulMixin
from chiru.models.channel import Channel, RawChannel

if TYPE_CHECKING:
    from chiru.models.factory import StatefulObjectFactory

DObjT = TypeVar("DObjT", bound=DiscordObject)


@final
class GuildChannelList(Mapping[int, Channel]):
    """
    A more stateful container for the channels in a guild.
    """

    def __init__(self, channels: dict[int, Channel] | None = None) -> None:
        super().__init__()

        self._channels = channels or {}

    @classmethod
    def from_guild_packet(
        cls,
        packet: Mapping[str, Any],
        factory: StatefulObjectFactory,
    ) -> GuildChannelList:
        """
        Creates a new channel list from a ``GUILD_CREATE`` packet.
        """

        channels = [factory.make_channel(c) for c in packet["channels"]]
        channels = {c.id: c for c in channels}
        return GuildChannelList(channels)

    def __getitem__(self, __key: int) -> Channel:
        return self._channels[__key]

    def __iter__(self) -> Iterator[int]:
        return iter(self._channels)

    def __len__(self) -> int:
        return len(self._channels)


@attr.s(slots=True, kw_only=True)
class UnavailableGuild(DiscordObject):
    """
    A single raw unavailable guild.
    """

    #: If this guild is unavailable or not. Always True.
    unavailable: bool = attr.ib(default=True)


@attr.s(kw_only=True)
class RawGuild(DiscordObject):
    """
    A single raw guild object (or server, in more common nomenclature).
    """

    @staticmethod
    def unmap_to_id(
        converter: Converter,
        type: Type[DObjT],
        data: Any,
        _,
    ) -> Mapping[int, DObjT]:
        items = [converter.structure(item, type) for item in data]
        return {i.id: i for i in items}

    @classmethod
    def configure_converter(cls, converter: Converter):
        raw_channel_fn = override(struct_hook=partial(cls.unmap_to_id, converter, RawChannel))

        converter.register_structure_hook(
            RawGuild,
            cattr.gen.make_dict_structure_fn(
                RawGuild,
                converter,
                channels=raw_channel_fn,
                _cattrs_forbid_extra_keys=False,
            ),
        )

        converter.register_structure_hook(
            cl=Guild,
            func=cattr.gen.make_dict_structure_fn(
                Guild,
                converter,
                _cattrs_forbid_extra_keys=False,
            ),
        )

    #: The name of this guild.
    name: str = attr.ib()

    #: The icon hash for this guild.
    icon: str = attr.ib()

    #: If this guild is unavailable or not. Always False.
    unavailable: bool = attr.ib(default=False)

    #: The mapping of channels that this guild contains.
    channels: Mapping[int, RawChannel] = attr.ib(factory=dict)


@attr.s(slots=True, kw_only=True)
class Guild(RawGuild, StatefulMixin):
    """
    Stateful version of :class:`.RawGuild`. Please note that this object does not support any form
    of manual creation; it *must* go through a :class:`.StatefulObjectFactory` to be created.
    """

    #: If this guild is available or not. May be False if there is an outage.
    unavailable: bool = attr.ib(default=True)

    #: The list of stateful channels that this guild contains.
    channels: GuildChannelList = attr.ib(init=False)
