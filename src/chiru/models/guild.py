from __future__ import annotations

from collections.abc import Iterator, Mapping
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar, final

import attr
import cattr
from cattr import Converter, override

from chiru.models.base import DiscordObject, HasIcon, StatefulMixin
from chiru.models.channel import AnyGuildChannel, RawChannel
from chiru.models.emoji import RawCustomEmoji
from chiru.models.member import Member, RawMember
from chiru.models.role import RawRole, Role
from chiru.models.user import User

if TYPE_CHECKING:
    from chiru.models.factory import ModelObjectFactory

DObjT = TypeVar("DObjT")


@attr.s(slots=True)
@final
class GuildChannelList(Mapping[int, AnyGuildChannel]):
    """
    A more stateful container for the channels in a guild.
    """

    _channels: dict[int, AnyGuildChannel] = attr.ib(factory=dict, repr=False)

    @classmethod
    def from_guild_packet(
        cls,
        guild_id: int,
        packet: Mapping[str, Any],
        factory: ModelObjectFactory,
    ) -> GuildChannelList:
        """
        Creates a new channel list from a ``GUILD_CREATE`` packet.
        """

        channels: dict[int, AnyGuildChannel] = {}
        for data in packet.get("channels", []):
            created_channel = factory.make_channel(data, from_guild=True)
            created_channel.guild_id = guild_id
            channels[created_channel.id] = created_channel

        return GuildChannelList(channels)

    def __getitem__(self, __key: int) -> AnyGuildChannel:
        return self._channels[__key]

    def __iter__(self) -> Iterator[int]:
        return iter(self._channels)

    def __len__(self) -> int:
        return len(self._channels)


@attr.s(slots=True, kw_only=True)
@final
class GuildMemberList(Mapping[int, Member]):
    """
    A more stateful container for the members in a guild.
    """

    _members: dict[int, Member] = attr.ib(factory=dict, alias="members", repr=False)
    _guild_id: int = attr.ib(alias="guild_id", repr=False)

    @classmethod
    def from_guild_packet(
        cls,
        guild_id: int,
        packet: Mapping[str, Any],
        factory: ModelObjectFactory,
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

        return GuildMemberList(members=members, guild_id=guild_id)

    def _update_member_data(
        self,
        factory: ModelObjectFactory,
        member_data: Mapping[str, Any],
        user: User | None = None,
    ) -> tuple[Member | None, Member]:
        """
        Backfills member data from the provided dict. Returns a tuple of (old | None, new) members.
        """

        new_member = factory.make_member(member_data, user)
        new_member.guild_id = self._guild_id
        old_member = self._members.get(new_member.id)
        self._members[new_member.id] = new_member
        return (old_member, new_member)

    def __getitem__(self, __key: int) -> Member:
        return self._members[__key]

    def __iter__(self) -> Iterator[int]:
        return iter(self._members)

    def __len__(self) -> int:
        return len(self._members)


@attr.s(slots=True)
@final
class GuildEmojis(Mapping[int, RawCustomEmoji]):
    """
    A stateful container for the emojis in a guild.
    """

    _emojis: dict[int, RawCustomEmoji] = attr.ib(factory=dict, repr=False)

    @classmethod
    def from_update_packet(
        cls,
        body: list[Mapping[str, Any]],
        factory: ModelObjectFactory,
    ) -> GuildEmojis:
        """
        Creates the guild emoji wrapper from the provided ``GUILD_EMOJIS_UPDATE`` packet.
        """

        emojis: dict[int, RawCustomEmoji] = {}
        for emoji_data in body:
            emoji = factory.structure(emoji_data, RawCustomEmoji)
            emojis[emoji.id] = emoji

        return GuildEmojis(emojis)

    @classmethod
    def from_guild_packet(
        cls,
        guild_id: int,
        body: Mapping[str, Any],
        factory: ModelObjectFactory,
    ) -> GuildEmojis:
        """
        Creates the guild emoji wrapper from the provided ``GUILD_CREATE`` packet.
        """

        return cls.from_update_packet(body["emojis"], factory)

    def __getitem__(self, key: int) -> RawCustomEmoji:
        return self._emojis[key]

    def __iter__(self) -> Iterator[int]:
        return iter(self._emojis)

    def __len__(self) -> int:
        return len(self._emojis)

    def __repr__(self) -> str:
        return repr(self._emojis)


@attr.s(slots=True, kw_only=True)
class GuildRolesList(Mapping[int, Role]):
    """
    A stateful container for the roles in a guild.
    """

    _roles: dict[int, Role] = attr.ib(factory=dict, alias="roles")

    @classmethod
    def from_guild_packet(
        cls,
        body: Mapping[str, Any],
        factory: ModelObjectFactory,
    ) -> GuildRolesList:
        """
        Creates a new :class:`.GuildRolesList` from the provided ``GUILD_CREATE`` packet.
        """

        roles: dict[int, Role] = {}
        for role_data in body["roles"]:
            role = factory.make_role(role_data)
            roles[role.id] = role

        return GuildRolesList(roles=roles)

    def __getitem__(self, key: int) -> Role:
        return self._roles[key]

    def __iter__(self) -> Iterator[int]:
        return iter(self._roles)

    def __len__(self) -> int:
        return len(self._roles)


@attr.s(slots=True, kw_only=True)
class UnavailableGuild(DiscordObject):
    """
    A single raw unavailable guild.
    """

    #: If this guild is unavailable or not. Always True.
    unavailable: bool = attr.ib(default=True)


@attr.s(kw_only=True)
class RawGuild(DiscordObject, HasIcon):
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
        raw_emoji_fn = override(struct_hook=partial(cls.unmap_to_id, converter))
        raw_roles_fn = override(struct_hook=partial(cls.unmap_to_id, converter))

        converter.register_structure_hook(
            RawGuild,
            cattr.gen.make_dict_structure_fn(
                RawGuild,
                converter,
                channels=raw_channel_fn,
                members=raw_member_fn,
                emojis=raw_emoji_fn,
                roles=raw_roles_fn,
                _cattrs_forbid_extra_keys=False,
                icon_hash=override(rename="icon"),
            ),
        )

        converter.register_structure_hook(
            cl=Guild,
            func=cattr.gen.make_dict_structure_fn(
                Guild, converter, _cattrs_forbid_extra_keys=False, icon_hash=override(rename="icon")
            ),
        )

    #: The name of this guild.
    name: str = attr.ib()

    #: The icon hash for this guild, if one is set.
    icon_hash: str | None = attr.ib()

    #: If this guild is unavailable or not. Always False.
    unavailable: bool = attr.ib(default=False)

    #: The mapping of :class:`.RawChannel` instances that this guild contains.
    channels: Mapping[int, RawChannel] = attr.ib(factory=dict)

    #: The mapping of :class:`.RawMember` instances that this guild contains.
    members: Mapping[int, RawMember] = attr.ib(factory=dict)

    #: The mapping of :class:`.RawCustomEmoji` instances that this guild contains.
    emojis: Mapping[int, RawCustomEmoji] = attr.ib(factory=dict)

    #: The mapping of :class:`.RawRole` instances that this guild contains.
    roles: Mapping[int, RawRole] = attr.ib()

    #: If this guild is a large guild, i.e. needs member chunking. Always False on the HTTP API.
    large: bool = attr.ib(default=False)

    #: The number of members in this guild. Always zero on the HTTP API.
    member_count: int = attr.ib(default=0)

    @property
    def default_role(self) -> RawRole:
        """
        Gets the default (the ``@everyone`` role) for this guild.
        """

        return self.roles[self.id]

    @property
    def icon_url(self) -> str | None:
        if not self.icon_hash:
            return None

        return f"https://cdn.discordapp.com/icons/{self.id}/{self.icon_hash}.webp"


@attr.s(slots=True, kw_only=True)
class Guild(RawGuild, StatefulMixin):
    """
    Stateful version of :class:`.RawGuild`. Please note that this object does not support any form
    of manual creation; it *must* go through a :class:`.ModelObjectFactory` to be created.
    """

    #: If this guild is unavailable or not. May be True if there is an outage.
    unavailable: bool = attr.ib(default=False)

    #: The list of stateful channels that this guild contains.
    channels: GuildChannelList = attr.ib(init=False)

    #: The list of stateful members that this guild contains.
    members: GuildMemberList = attr.ib(init=False)

    #: The list of :class:`.RawCustomEmoji`s that this guild contains. These emojis will not
    #: contain ownership information; see :meth:`.ChiruHttpClient.get_emojis` for retrieving
    #: emoji with ownership information.
    emojis: GuildEmojis = attr.ib(init=False)

    #: The list of stateful roles that this guild contains.
    roles: GuildRolesList = attr.ib(init=False)

    @property
    def default_role(self) -> Role:
        """
        Gets the default :class:`.Role` for this guild (the @everyone role).
        """

        # i'm sure that docstring will annoy somebody.
        return self.roles[self.id]
