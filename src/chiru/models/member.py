from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import attr
import cattr
from cattr import Converter, override
from whenever import UTCDateTime

from chiru.models.base import DiscordObject, StatefulMixin
from chiru.models.permissions import ReadOnlyPermissions
from chiru.models.role import Role
from chiru.models.user import RawUser, User

if TYPE_CHECKING:
    from chiru.models.guild import Guild


@attr.s(kw_only=True)
class RawMember:
    """
    A single member in a guild.
    """

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:  # noqa: D102
        for klass in (cls, Member):
            converter.register_structure_hook(
                klass,
                func=cattr.gen.make_dict_structure_fn(
                    klass,
                    converter,
                    role_ids=override(rename="roles"),
                    _cattrs_forbid_extra_keys=False,
                ),
            )

    # may be None e.g. on message objects
    #: The raw user object for this member.
    user: RawUser | None = attr.ib(default=None)

    #: The nickname for this member.
    nick: str | None = attr.ib(default=None)

    #: The avatar hash for this member, if unspecified in the RawUser field.
    avatar: str | None = attr.ib(default=None)

    #: The list of role IDs that this member has.
    role_ids: list[int] = attr.ib(factory=list)

    #: When this member joined the guild.
    joined_at: UTCDateTime = attr.ib()


@attr.s(slots=True, kw_only=True)
class Member(DiscordObject, RawMember, StatefulMixin):
    """
    Stateful version of :class:`.RawMember`.
    """

    #: The ID for this member. Backfilled automatically.
    id: int = attr.ib(init=False)

    user: User | None = attr.ib(default=None)

    #: The guild ID that this member is for.
    guild_id: int = attr.ib(init=False)

    def __attrs_post_init__(self) -> None:
        if self.user is not None:
            self.id = self.user.id

    @property
    def guild(self) -> Guild:
        """
        Gets the :class:`.Guild` this member is from.
        """

        guild = self._client.object_cache.get_available_guild(self.guild_id)
        assert guild, f"Somehow got a member for a non-existent guild {self.guild_id}"
        return guild

    @property
    def roles(self) -> Sequence[Role]:
        """
        Gets the list of :class:`.Role` instances this member has. This is sorted from the lowest
        role's position to the highest role's position.
        """

        return sorted(
            [self.guild.roles[it] for it in self.role_ids], key=lambda role: role.position
        )

    @property
    def default_permissions(self) -> ReadOnlyPermissions:
        """
        Calculates the default permissions for this member in this guild, ignoring the Administrator
        bit.
        """

        base_permissions = self.guild.default_role.permissions._bitfield

        for role in self.roles:
            base_permissions |= role.permissions._bitfield

        return ReadOnlyPermissions(bitfield=base_permissions)

    @property
    def effective_permissions(self) -> ReadOnlyPermissions:
        """
        Calculates the *effective* permissions for this member in this guild, taking into account
        the Administrator bit.
        """

        if self.id == self.guild.owner_id:
            return ReadOnlyPermissions.all()

        perms = self.default_permissions
        if perms.administrator:
            return ReadOnlyPermissions.all()

        return perms

    @property
    def top_role(self) -> Role:
        """
        Gets the top-most role for this member. If the member has no custom roles, this will return
        the guild's default role.
        """

        if not self.role_ids:
            return self.guild.default_role

        return self.roles[-1]

    async def kick(self, *, reason: str | None = None) -> None:
        """
        Kicks this member from the guild.
        """

        await self._client.http.kick(guild_id=self.guild_id, member_id=self.id, reason=reason)
