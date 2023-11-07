from pprint import pprint
from typing import List

from chiru.cache import ObjectCache
from chiru.event.model import Connected, DispatchedEvent, MessageCreate
from chiru.gateway.event import GatewayDispatch
from chiru.models.factory import StatefulObjectFactory


class CachedEventParser:
    """
    Deals with parsing incoming dispatch events and converting them into high-level events. This
    will cache objects as appropriate to ensure that state (e.g. members) is kept between event
    invocations.

    Each parsing function here is a generator that may yield any number of events, including zero.
    """

    def __init__(self, cache: ObjectCache):
        self._cache = cache

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

    @staticmethod
    def parse_ready(
        event: GatewayDispatch,
        factory: StatefulObjectFactory,
    ):
        """
        Parses the READY event, which signals that a connection is open.
        """

        yield Connected()

    @staticmethod
    def parse_message_create(event: GatewayDispatch, factory: StatefulObjectFactory):
        """
        Parses a MESSAGE_CREATE event.
        """

        message = factory.make_message(event.body)
        yield MessageCreate(message=message)
