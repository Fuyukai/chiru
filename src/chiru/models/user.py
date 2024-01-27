from __future__ import annotations

import typing
from types import NotImplementedType
from typing import TYPE_CHECKING

import attr
import cattrs
from cattr import override
from cattr.gen import make_dict_unstructure_fn
from cattrs.gen import make_dict_structure_fn

from chiru.models.base import DiscordObject, HasIcon, StatefulMixin

if TYPE_CHECKING:
    from chiru.models.channel import DirectMessageChannel
else:
    type DirectMessageChannel = object


@attr.s(kw_only=True, hash=False, eq=False)
class RawUser(DiscordObject, HasIcon):
    """
    A single Discord user.
    """

    @classmethod
    def configure_converter(cls, converter: cattrs.Converter) -> None:  # noqa: D102
        for klass in (cls, User):
            converter.register_structure_hook(
                klass,
                make_dict_structure_fn(
                    klass,
                    converter,
                    _cattrs_forbid_extra_keys=False,
                    avatar_hash=override(rename="avatar"),
                ),
            )

            converter.register_unstructure_hook(
                klass,
                make_dict_unstructure_fn(klass, converter, avatar_hash=override(rename="avatar")),
            )

    #: The global username for this user. This may or may not be unique.
    username: str = attr.ib()

    #: The discriminator for this user. This is a deprecated field and is only kept for
    #: compatibility with legacy accounts.
    discriminator: str | None = attr.ib(default="0")

    #: The display name for this user. May be None if this user has no extra display name.
    global_name: str | None = attr.ib(default=None)

    #: The avatar hash for this user.
    avatar: str | None = attr.ib(default=None)

    #: If this user is a bot user or not.
    bot: bool = attr.ib(default=False)

    #: If this user is a system user or not.
    system: bool = attr.ib(default=False)

    @property
    @typing.override
    def icon_url(self) -> str | None:
        if not self.avatar:
            return None

        return f"https://cdn.discordapp.com/avatars/{self.id}/{self.avatar}.webp"

    @property
    def display_name(self) -> str:
        """
        Gets the display name for this user.
        """

        if self.global_name:
            return self.global_name

        return self.username

    @typing.override
    def __hash__(self) -> int:
        return hash(self.id)

    @typing.override
    def __eq__(self, other: object) -> bool | NotImplementedType:
        if not isinstance(other, RawUser):
            return NotImplemented

        return other.id == self.id


@attr.s(kw_only=True, hash=False, eq=False)
class User(RawUser, StatefulMixin):
    """
    Stateful version of :class:`.RawUser`.
    """

    async def open_direct_message_channel(self) -> DirectMessageChannel:
        """
        Opens a new :class:`.DirectMessageChannel` with the specified user.
        """

        return await self._client.http.create_direct_message_channel(
            user_id=self.id, factory=self._client.stateful_factory
        )
