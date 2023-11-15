from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from chiru.cache import ObjectCache
from chiru.models.channel import Channel
from chiru.models.guild import (
    Guild,
    GuildChannelList,
    GuildMemberList,
    UnavailableGuild,
)
from chiru.models.member import Member
from chiru.models.message import Message
from chiru.models.user import User
from chiru.serialise import CONVERTER

if TYPE_CHECKING:
    from chiru.bot import ChiruBot


class StatefulObjectFactory:
    """
    Produces stateful objects from raw JSON bodies. This requires a :class:`.ChiruBot` to be
    provided which will be set on the stateful objects.
    """

    def __init__(self, client: ChiruBot):
        self._client: ChiruBot = client

        self.object_cache: ObjectCache = ObjectCache()

    def make_user(
        self,
        user_data: Mapping[str, Any],
    ) -> User:
        """
        Creates a new stateful :class:`.User` from a user body.
        """

        obb = CONVERTER.structure(user_data, User)
        obb._chiru_set_client(self._client)
        return obb

    def make_member(self, user_data: Mapping[str, Any], user: User | None = None) -> Member:
        """
        Creates a new stateful :class:`.Member` from a member body.
        """

        obb = CONVERTER.structure(user_data, Member)
        if obb.user is None:
            if user is None:
                raise ValueError("Expected some sort of user object")

            obb.user = user

        obb.id = obb.user.id

        obb._chiru_set_client(self._client)
        return obb

    def make_message(self, message_data: Mapping[str, Any]) -> Message:
        """
        Creates a new stateful :class:`.Message` from a message body. This will also create
        stateful :class:`.User` instances for :attr:`.Message.author`.
        """

        obb = CONVERTER.structure(message_data, Message)
        obb._chiru_set_client(self._client)

        # fill child fields
        obb.raw_author._chiru_set_client(bot=self._client)

        return obb

    def make_channel(self, channel_data: Mapping[str, Any]) -> Channel:
        """
        Creates a new stateful :class:`.Channel`.
        """

        obb: Channel = CONVERTER.structure(channel_data, Channel)
        obb._chiru_set_client(bot=self._client)

        return obb

    def make_guild(
        self,
        guild_data: Mapping[str, Any],
    ) -> Guild | UnavailableGuild:
        """
        Creates a new stateful :class:`.Guild`.
        """

        if guild_data.get("unavailable", False):
            return CONVERTER.structure(guild_data, UnavailableGuild)

        base_guild = CONVERTER.structure(guild_data, Guild)
        base_guild._chiru_set_client(self._client)

        channel_list = GuildChannelList.from_guild_packet(guild_data, self)
        base_guild.channels = channel_list
        member_list = GuildMemberList.from_guild_packet(guild_data, self)
        base_guild.members = member_list

        return base_guild
