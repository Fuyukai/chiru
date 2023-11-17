from __future__ import annotations

from collections.abc import Iterator, Mapping
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar, final

import attr
import cattr
from cattr import Converter, override

from chiru.models.base import DiscordObject, StatefulMixin
from chiru.models.channel import Channel, RawChannel
from chiru.models.member import Member, RawMember
from chiru.models.user import User

if TYPE_CHECKING:
    from chiru.models.factory import StatefulObjectFactory

DObjT = TypeVar("DObjT")


@final
@attr.s(slots=True)
class GuildChannelList(Mapping[int, Channel]):
    """
    A more stateful container for the channels in a guild.
    """

    _channels: dict[int, Channel] = attr.ib(factory=dict)

    @classmethod
    def from_guild_packet(
        cls,
        packet: Mapping[str, Any],
        factory: StatefulObjectFactory,
    ) -> GuildChannelList:
        """
        Creates a new channel list from a ``GUILD_CREATE`` packet.
        """

        guild_id = int(packet["id"])

        channels: dict[int, Channel] = {}
        for data in packet.get("channels", []):
            created_channel = factory.make_channel(data)
            created_channel.guild_id = guild_id
            channels[created_channel.id] = created_channel

        return GuildChannelList(channels)

    def __getitem__(self, __key: int) -> Channel:
        return self._channels[__key]

    def __iter__(self) -> Iterator[int]:
        return iter(self._channels)

    def __len__(self) -> int:
        return len(self._channels)


@final
@attr.s(slots=True)
class GuildMemberList(Mapping[int, Member]):
    """
    A more stateful container for the members in a guild.
    """

    _members: dict[int, Member] = attr.ib(factory=dict)

    @classmethod
    def from_guild_packet(
        cls,
        packet: Mapping[str, Any],
        factory: StatefulObjectFactory,
    ) -> GuildMemberList:
        """
        Creates a new member list from a ``GUILD_CREATE`` packet.
        """

        guild_id = int(packet["id"])

        members: dict[int, Member] = {}
        for data in packet.get("members", []):
            created_member = factory.make_member(data)
            created_member.guild_id = guild_id
            members[created_member.id] = created_member

        return GuildMemberList(members)

    def _backfill_member_data(
        self,
        factory: StatefulObjectFactory,
        member_data: Mapping[str, Any],
        user: User | None = None,
    ) -> Member:
        """
        Backfills member data from the provided dict.
        """

        new_member = factory.make_member(member_data, user)
        self._members[new_member.id] = new_member
        return new_member

    def __getitem__(self, __key: int) -> Member:
        return self._members[__key]

    def __iter__(self) -> Iterator[int]:
        return iter(self._members)

    def __len__(self) -> int:
        return len(self._members)


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
        data: Any,
        provided_type: type[DObjT],
    ) -> Mapping[int, DObjT]:
        items = [converter.structure(item, provided_type) for item in data]

        # can't access the generic type in the function body, so just slap a type: ignore on it.
        if provided_type is RawMember:
            return {i.raw_author.id: i for i in items}  # type: ignore

        assert issubclass(
            provided_type, DiscordObject
        ), f"expected DiscordObject, not {provided_type}"
        return {i.id: i for i in items}  # type: ignore

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:
        raw_channel_fn = override(struct_hook=partial(cls.unmap_to_id, converter))
        raw_member_fn = override(struct_hook=partial(cls.unmap_to_id, converter))

        converter.register_structure_hook(
            RawGuild,
            cattr.gen.make_dict_structure_fn(
                RawGuild,
                converter,
                channels=raw_channel_fn,
                members=raw_member_fn,
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

    #: The mapping of members that this guild contains.
    members: Mapping[int, RawMember] = attr.ib(factory=dict)

    #: If this guild is a large guild, i.e. needs member chunking. Always False on the HTTP API.
    large: bool = attr.ib(default=False)

    #: The number of members in this guild. Always zero on the HTTP API.
    member_count: int = attr.ib(default=0)


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

    #: The list of stateful members that this guild contains.
    members: GuildMemberList = attr.ib(init=False)
