from __future__ import annotations

from typing import TYPE_CHECKING, cast

import attr

if TYPE_CHECKING:
    from chiru.models.channel import Channel
    from chiru.models.guild import Guild, UnavailableGuild
else:
    Guild = None


@attr.s(slots=False, frozen=False)
class ObjectCache:
    """
    Caches certain Discord objects to avoid needing to constantly re-create them.
    """

    guilds: dict[int, UnavailableGuild | Guild] = attr.ib(factory=dict)
    dm_channels: dict[int, Channel] = attr.ib(factory=dict)

    def get_available_guild(self, guild_id: int) -> Guild | None:
        """
        Gets an available guild, or None if the guild is not available.
        """

        guild = self.guilds[guild_id]
        # if ``unavailable`` is False, this is always a Guild.
        if not guild.unavailable:
            return cast(Guild, guild)

        return None

    def find_channel(self, channel_id: int) -> Channel | None:
        """
        Looks up a channel in the cache.
        """

        try:
            return self.dm_channels[channel_id]
        except KeyError:
            pass

        for _id, guild in self.guilds.items():
            if guild.unavailable:
                continue

            guild = cast(Guild, guild)
            try:
                return guild.channels[channel_id]
            except KeyError:
                continue

        return None
