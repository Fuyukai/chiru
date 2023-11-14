from __future__ import annotations

from typing import TYPE_CHECKING

import arrow
import attr

if TYPE_CHECKING:
    from chiru.bot import ChiruBot
else:
    # only used as a type annotation, it's fine.
    ChiruBot = None

DISCORD_EPOCH = 1420070400000


@attr.s(kw_only=True)
class DiscordObject:
    """
    Base class for all objects that have a Snowflake-based ID.
    """

    #: The Snowflake-based ID for this object. See
    #: `Snowflakes <https://discord.com/developers/docs/reference#snowflakes>`_ for more information
    #: on the format of this field.
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
    A mixin that allows model classes to have a reference to the currently running client instance.

    Compared to raw models, stateful models can perform actions on the client directly via their
    own instance methods. Raw models only provide IDs of other models that the objects depend on,
    whereas stateful models can directly look up other objects from the object cache.
    """

    _client: ChiruBot = attr.ib(init=False)

    def _chiru_set_client(self, bot: ChiruBot) -> None:
        self._client = bot
