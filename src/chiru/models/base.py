from __future__ import annotations

from typing import TYPE_CHECKING

import arrow
import attr

if TYPE_CHECKING:
    from chiru.bot import ChiruBot

DISCORD_EPOCH = 1420070400000


@attr.s(kw_only=True)
class DiscordObject:
    """
    Base class for all objects that have a Snowflake-based ID.
    """

    #: The Snowflake-based ID for this object.
    id: int = attr.ib()

    @property
    def creation_time(self) -> arrow.Arrow:
        """
        Gets the creation time of this Discord object.
        """

        ts = ((int(self.id) >> 22) + DISCORD_EPOCH) / 1000
        return arrow.get(ts)


@attr.s(kw_only=True)
class StatefulMixin:
    """
    A mixin that allows data classes to have a reference to the currently running client instance.
    """

    _client = attr.ib(init=False)

    def _chiru_set_client(self, bot: ChiruBot):
        self._client = bot
