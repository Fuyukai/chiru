from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

import attr
import cattr
from cattr import Converter, override

from chiru.models.base import DiscordObject, HasIcon, StatefulMixin
from chiru.models.emoji import UnicodeEmoji
from chiru.util import maybe_int

# TODO: permissions...


@attr.s(slots=True, frozen=True, kw_only=True)
class RoleAdditionalMetadata:
    """
    Additional metadata about a role that isn't included in the main role.
    """

    #: The ID of the bot that this automatically created role belongs to.
    bot_id: int | None = attr.ib(default=None)

    #: The ID of the integration that this automatically created role belongs to.
    integration_id: int | None = attr.ib(default=None)

    #: If True, this is the role's booster role (?).
    booster_role: bool = attr.ib(default=False)

    #: The id of this role's subscription SKU (?).
    subscription_listing_id: int | None = attr.ib(default=None)

    #: If this role is available for purchase or not.
    purchasable: bool = attr.ib(default=False)

    #: If this is a guild's linked role (?).
    guild_connections: bool = attr.ib(default=False)

    @classmethod
    def struct_hook(cls, data: Mapping[str, int | Literal[None]], _: Any) -> RoleAdditionalMetadata:
        # what the everliving fuck is this structure.
        # "booleans are represented with null" what? what the fuck?
        # why not just make the fields always there?
        # what the fuck!

        bot_id = maybe_int(data.get("bot_id"))
        integration_id = maybe_int(data.get("integration_id"))
        is_booster_role = "premium_subscriber" in data
        subscription_id = maybe_int(data.get("subscription_listing_id"))
        purchasable = "available_for_purchase" in data
        guild_connections = "guild_connections" in data

        return RoleAdditionalMetadata(
            bot_id=bot_id,
            integration_id=integration_id,
            booster_role=is_booster_role,
            subscription_listing_id=subscription_id,
            purchasable=purchasable,
            guild_connections=guild_connections,
        )


@attr.s(kw_only=True)
class RawRole(DiscordObject, HasIcon):
    """
    A single role in a guild. A role controls the permissions for a user as well as their name
    colour, and the ability to be seen in the sidebar separately (called hoisting).
    """

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:
        for klass in (cls, Role):
            converter.register_structure_hook(
                klass,
                cattr.gen.make_dict_structure_fn(
                    klass,
                    converter,
                    _cattrs_forbid_extra_keys=False,
                    colour=override(rename="color"),
                    icon_hash=override(rename="icon"),
                    emoji=override(rename="unicode_emoji"),
                    role_metadata=override(
                        rename="tags", struct_hook=RoleAdditionalMetadata.struct_hook
                    ),
                ),
            )

            converter.register_unstructure_hook(
                klass,
                cattr.gen.make_dict_unstructure_fn(
                    klass,
                    converter,
                    colour=override(rename="color"),
                    icon_hash=override(rename="icon"),
                    emoji=override(rename="unicode_emoji"),
                ),
            )

    #: The name for this role.
    name: str = attr.ib()

    #: The RGB colour of this role.
    colour: int = attr.ib()

    #: If True, then members of this role will display separately to regular 'Online' members
    #: in the member list.
    hoist: bool = attr.ib()

    #: The position for this role in the list of roles.
    position: int = attr.ib()

    # no clue wtf either of these are
    #: The icon hash for this role.
    icon_hash: str | None = attr.ib(default=None)

    #: The emoji for this role.
    emoji: UnicodeEmoji | None = attr.ib(default=None)

    #: If True, then this role is managed by an integration such as a bot.
    managed: bool = attr.ib()

    #: If True, then this role can be mentioned.
    mentionable: bool = attr.ib()

    #: The additional metadata for this role.
    role_metadata: RoleAdditionalMetadata = attr.ib(default=RoleAdditionalMetadata())

    @property
    def icon_url(self) -> str | None:
        if self.icon_hash is None:
            return None

        return f"https://cdn.discordapp.com/roles/{self.id}/{self.icon_hash}.webp"


@attr.s(kw_only=True)
class Role(RawRole, StatefulMixin):
    """
    Stateful variant of :class:`.RawRole`.
    """
