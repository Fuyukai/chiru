import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from functools import partial
from typing import AsyncGenerator, Callable, Type, TypeVar, overload, Awaitable, Any

import attr
import bitarray

from chiru.bot import ChiruBot
from chiru.event.model import DispatchedEvent
from chiru.event.parser import CachedEventParser
from chiru.gateway.event import IncomingGatewayEvent, GatewayDispatch
from chiru.util import CapacityLimitedNursery, open_limiting_nursery

GwEventT = TypeVar("GwEventT", bound=IncomingGatewayEvent)
DsEventT = TypeVar("DsEventT", bound=DispatchedEvent)

# roughly equiv to state.py in curious.
# TODO: split out the actual event dispatching and the actual event parsing, maybe?

logger = logging.getLogger(__name__)


@attr.s(frozen=True, slots=True, kw_only=True)
class EventContext:
    """
    Contains additional context for a single dispatched event.
    """

    #: The shard that this event was received on.
    shard_id: int = attr.ib()

    #: The name of the dispatch event that caused this event, if any.
    dispatch_name: str | None = attr.ib()

    #: The sequence number for this event.
    sequence: int = attr.ib()


class StatefulEventDispatcher:
    """
    An event dispatcher that uses the client's object
    """

    def __init__(
        self,
        bot: ChiruBot,
        nursery: CapacityLimitedNursery,
    ):
        self._nursery = nursery

        self._parser = CachedEventParser(bot.object_cache)

        # no point type hinting this, too annoying.
        self._events = defaultdict(list)

        # use a string here bc the default is "uninitialised" (wtf could that mean?)
        self._ready_shards = bitarray.bitarray('0' * bot.cached_gateway_info.shards)

        self._has_fired_all_ready = False

    @staticmethod
    async def _run_safely(fn: Callable[[], Awaitable[None]]):
        try:
            await fn()
        except Exception as e:
            logger.exception("Unhandled exception caught!", exc_info=e)

    async def _dispatch_event(
        self,
        event_klass: Type[Any],
        ctx: EventContext | None,
        event: Any,
    ):
        """
        Spawns a single event into the nursery.
        """

        if ctx:
            fns = [
                partial(
                    self._run_safely, partial(fn, ctx, event)
                ) for fn in self._events[event_klass]
            ]
        else:
            fns = [
                partial(self._run_safely, partial(fn, event)) for fn in self._events[event_klass]
            ]

        for fn in fns:
            await self._nursery.start(fn)


    @overload
    def add_event_handler(
        self, event: Type[GwEventT], handler: Callable[[GwEventT], Awaitable[None]]
    ) -> None:
        ...

    @overload
    def add_event_handler(
        self,
        event: Type[DsEventT],
        handler: Callable[[EventContext, DsEventT], Awaitable[None]]
    ) -> None:
        ...

    def add_event_handler(
        self, event, handler
    ):
        """
        Adds an event handler for a low-level gateway event.
        """

        logger.debug(f"Registered event callable {handler} handling type '{event}'")

        self._events[event].append(handler)

    async def run_forever(self, client: ChiruBot):
        """
        Runs the event dispatcher forever for the provided client.
        """

        async with client.start_receiving_events() as stream:
            async for event in stream:
                # all gateway events need to be dispatched normally to potential handlers
                await self._dispatch_event(type(event), ctx=None, event=event)

                if not isinstance(event, GatewayDispatch):
                    continue

                context = EventContext(
                    shard_id=event.shard_id,
                    dispatch_name=event.event_name,
                    sequence=event.sequence
                )

                for dispatched in self._parser.get_parsed_events(client.stateful_factory, event):
                    await self._dispatch_event(type(dispatched), context, dispatched)

                if not self._has_fired_all_ready and event.event_name == "READY":
                    self._ready_shards[event.shard_id] = True

                    if self._ready_shards.all():
                        self._has_fired_all_ready = True
                        # await self._dispatch_event()


@asynccontextmanager
async def create_stateful_dispatcher(
    bot: ChiruBot,
    *,
    max_tasks: int = 16
) -> AsyncGenerator[StatefulEventDispatcher, None]:
    """
    Creates a new :class:`.StatefulEventDispatcher`.

    :param bot: The :class:`.ChiruBot` instance to dispatch events from.
    :param max_tasks: The maximum number of event tasks that can run in parallel before the
                      dispatcher stops reading from the channel temporarily.
    """

    async with open_limiting_nursery(max_tasks=max_tasks) as n:
        try:
            yield StatefulEventDispatcher(bot, n)
        finally:
            n.cancel_scope.cancel()
