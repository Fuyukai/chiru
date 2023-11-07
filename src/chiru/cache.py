from __future__ import annotations

from typing import TYPE_CHECKING

import attr

if TYPE_CHECKING:
    from chiru.models.channel import Channel
    from chiru.models.guild import Guild, UnavailableGuild
    from chiru.models.user import User


@attr.s(slots=False, frozen=False)
class ObjectCache:
    """
    Caches certain Discord objects to avoid needing to constantly re-create them.
    """

    guilds: dict[int, UnavailableGuild | Guild] = {}
    channels: dict[int, Channel] = {}
