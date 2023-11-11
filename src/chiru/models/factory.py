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

    def make_member(self, user_data: Mapping[str, Any]) -> Member:
        """
        Creates a new stateful :class:`.Member`.
        """

        obb = CONVERTER.structure(user_data, Member)
        assert obb.user is not None, "stateful member objects must have user data attached"
        obb.id = obb.user.id

        obb._chiru_set_client(self._client)
        return obb

    def make_message(self, message_data: Mapping[str, Any]) -> Message:
        """
        Creates a new stateful :class:`.Message`.
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

    def make_guild(self, guild_data: Mapping[str, Any]) -> Guild | UnavailableGuild:
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
