from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, overload

from chiru.cache import ObjectCache
from chiru.models.channel import (
    AnyGuildChannel,
    BaseChannel,
    ChannelType,
    TextualGuildChannel,
    UnsupportedChannel,
    UnsupportedGuildChannel,
)
from chiru.models.guild import (
    Guild,
    GuildChannelList,
    GuildEmojis,
    GuildMemberList,
    UnavailableGuild,
)
from chiru.models.member import Member
from chiru.models.message import Message
from chiru.models.user import User
from chiru.serialise import CONVERTER

if TYPE_CHECKING:
    from chiru.bot import ChiruBot


_StructType = TypeVar("_StructType")


class ModelObjectFactory:
    """
    Produces both stateful and non-stateful objects from incoming data. This requires passing a
    :class:`.ChiruBot` for applying to stateful classes.

    This should be preferred over using the raw :class:`~.Converter` wherever possible to avoid
    creating a tangle of circular imports.
    """

    def __init__(self, client: ChiruBot) -> None:
        self._client: ChiruBot = client

        self.object_cache: ObjectCache = ObjectCache()

    def structure(self, data: Any, what: type[_StructType]) -> _StructType:
        """
        Deserialises the provided raw data into the provided type.
        """

        return CONVERTER.structure(data, what)

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

    def make_member(self, member_data: Mapping[str, Any], user: User | None = None) -> Member:
        """
        Creates a new stateful :class:`.Member` from a member body.

        :param user_data: The raw member data to create objects from, as provided by Discord.
        :param user: If the ``user`` property of ``member_data`` is None or non-existent then this
            must be a :class:`.User` that will be set onto the member object.
        """

        obb = CONVERTER.structure(member_data, Member)
        if obb.user is None:
            if user is None:
                raise ValueError("Expected some sort of user object")

            obb.user = user

        obb.id = obb.user.id

        obb._chiru_set_client(self._client)
        obb.user._chiru_set_client(self._client)
        return obb

    def make_message(
        self,
        message_data: Mapping[str, Any],
    ) -> Message:
        """
        Creates a new stateful :class:`.Message` from a message body. This will also create
        stateful :class:`.User` instances for :attr:`.Message.author`.
        """

        obb = CONVERTER.structure(message_data, Message)
        obb._chiru_set_client(self._client)

        if obb.guild_id is None:
            channel = self.object_cache.find_channel(obb.channel_id)

            if channel and isinstance(channel, AnyGuildChannel):
                obb.guild_id = channel.id

        # fill child fields
        obb.raw_author._chiru_set_client(bot=self._client)

        return obb

    # this is a gross static type trick.
    # ``from_guild`` is always True if ``guild_id`` is in the channel data.
    @overload
    def make_channel(
        self,
        channel_data: Mapping[str, Any],
    ) -> BaseChannel: ...

    @overload
    def make_channel(
        self, channel_data: Mapping[str, Any], from_guild: Literal[True]
    ) -> AnyGuildChannel: ...

    def make_channel(
        self,
        channel_data: Mapping[str, Any],
        from_guild: bool = False,
    ) -> BaseChannel | AnyGuildChannel:
        """
        Creates a new stateful :class:`.Channel`.
        """

        type: ChannelType = ChannelType(channel_data["type"])
        guild_id: str | None = channel_data.get("guild_id")
        from_guild = from_guild or guild_id is not None

        obb: BaseChannel
        match type:
            case ChannelType.GUILD_TEXT:
                obb = CONVERTER.structure(channel_data, TextualGuildChannel)

            case _:
                if from_guild:
                    obb = CONVERTER.structure(channel_data, UnsupportedGuildChannel)
                else:
                    obb = CONVERTER.structure(channel_data, UnsupportedChannel)

        if guild_id:
            obb.guild_id = int(guild_id)

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

        base_guild.channels = GuildChannelList.from_guild_packet(base_guild.id, guild_data, self)
        base_guild.members = GuildMemberList.from_guild_packet(base_guild.id, guild_data, self)
        base_guild.emojis = GuildEmojis.from_guild_packet(base_guild.id, guild_data, self)

        return base_guild
