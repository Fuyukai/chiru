from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from chiru.cache import ObjectCache
from chiru.models.message import Message
from chiru.models.user import User
from chiru.serialise import create_chiru_converter, CONVERTER

if TYPE_CHECKING:
    from chiru.bot import ChiruBot


# noinspection PyProtectedMember
class StatefulObjectFactory:
    """
    Produces stateful objects from raw JSON bodies.
    """

    def __init__(self, client: ChiruBot):
        self._client = client

        self.object_cache = ObjectCache()

    def make_user(
        self,
        user_data: Mapping[str, Any],
    ) -> User:
        """
        Creates a new stateful :class:`.User`.
        """

        obb = CONVERTER.structure(user_data, User)
        obb._chiru_set_client(self._client)
        return obb

    def make_message(self, message_data: Mapping[str, Any]) -> Message:
        """
        Creates a new stateful :class:`.Message`.
        """

        obb = CONVERTER.structure(message_data, Message)
        obb._chiru_set_client(self._client)
        return obb
