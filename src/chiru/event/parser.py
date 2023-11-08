from typing import List

from chiru.cache import ObjectCache
from chiru.event.model import (
    Connected,
    DispatchedEvent,
    GuildAvailable,
    GuildJoined,
    GuildStreamed,
    MessageCreate,
)
from chiru.gateway.event import GatewayDispatch
from chiru.models.factory import StatefulObjectFactory
from chiru.models.guild import UnavailableGuild


class CachedEventParser:
    """
    Deals with parsing incoming dispatch events and converting them into high-level events. This
    will cache objects as appropriate to ensure that state (e.g. members) is kept between event
    invocations.

    Each parsing function here is a generator that may yield any number of events, including zero.
    """

    def __init__(self, cache: ObjectCache):
        self._cache = cache

        self._has_fired_startup_before = False

    def get_parsed_events(
        self, factory: StatefulObjectFactory, event: GatewayDispatch
    ) -> List[DispatchedEvent]:
        """
        Gets a list of parsed events from the provided :class:`.GatewayDispatch` gateway event.
        """

        fn = getattr(self, f"parse_{event.event_name.lower()}", None)
        if fn is None:
            return []

        return list(fn(event, factory))

    def parse_ready(
        self,
        event: GatewayDispatch,
        factory: StatefulObjectFactory,
    ):
        """
        Parses the READY event, which signals that a connection is open.
        """

        guilds = [factory.make_guild(g) for g in event.body["guilds"]]
        self._cache.guilds = {g.id: g for g in guilds}

        yield Connected()

    def parse_guild_create(self, event: GatewayDispatch, factory: StatefulObjectFactory):
        """
        Parses a GUILD_CREATE event, either from guild streaming or from joining a new guild.
        """

        created_guild = factory.make_guild(event.body)
        assert not created_guild.unavailable, "what the fuck, discord!"
        assert not isinstance(created_guild, UnavailableGuild)

        self._cache.guilds[created_guild.id] = created_guild

        if not self._has_fired_startup_before:
            yield GuildStreamed(created_guild)
        else:
            if created_guild.id not in self._cache.guilds:
                yield GuildJoined(created_guild)
            else:
                yield GuildAvailable(created_guild)

    @staticmethod
    def parse_message_create(event: GatewayDispatch, factory: StatefulObjectFactory):
        """
        Parses a MESSAGE_CREATE event.
        """

        message = factory.make_message(event.body)
        yield MessageCreate(message=message)
