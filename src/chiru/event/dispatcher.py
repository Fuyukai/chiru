from collections import defaultdict
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import partial
from typing import Any, NoReturn, TypeVar, final, overload

import anyio
import attr
import bitarray
import structlog

from chiru.bot import ChiruBot
from chiru.event.chunker import GuildChunker
from chiru.event.model import DispatchedEvent, Ready, ShardReady
from chiru.event.parser import CachedEventParser
from chiru.gateway.event import GatewayDispatch, IncomingGatewayEvent
from chiru.util import CapacityLimitedNursery, cancel_on_close, open_limiting_nursery

GwEventT = TypeVar("GwEventT", bound=IncomingGatewayEvent)
DsEventT = TypeVar("DsEventT", bound=DispatchedEvent)

# roughly equiv to state.py in curious.
# TODO: split out the actual event dispatching and the actual event parsing, maybe?

logger: structlog.stdlib.BoundLogger = structlog.get_logger(name=__name__)


@final
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


@final
class StatefulEventDispatcher:
    """
    An event dispatcher that uses the client's object cache to store stateful objects.
    """

    def __init__(
        self,
        bot: ChiruBot,
        nursery: CapacityLimitedNursery,
    ):
        #: The client object that this event dispatcher uses.
        self.client: ChiruBot = bot

        #: The guild member chunker for this event dispatcher.
        self.chunker: GuildChunker = GuildChunker()

        #: The cache-based event parser for this dispatcher.
        self.parser: CachedEventParser = CachedEventParser(
            bot.object_cache, bot.cached_gateway_info.shards, self.chunker
        )

        # no point type hinting this, too annoying.
        self._events = defaultdict(list)  # type: ignore

        self._nursery: CapacityLimitedNursery = nursery

        # global ready state checking.
        # bit array of the shards that have fired a ShardReady or not.
        self._ready_shards = bitarray.bitarray("0" * bot.cached_gateway_info.shards)

    @staticmethod
    async def _run_safely(fn: Callable[[], Awaitable[None]]) -> None:
        try:
            await fn()
        except Exception as e:
            logger.exception("Unhandled exception caught!", exc_info=e)

    async def _dispatch_event(
        self,
        event_klass: type[Any],
        ctx: EventContext | None,
        event: Any,
    ) -> None:
        """
        Spawns a single event into the nursery.
        """

        if ctx is not None:
            logger.debug("Dispatching event", event_type=event_klass.__name__, shard=ctx.shard_id)
        else:
            logger.debug("Dispatching event", event_type=event_klass.__name__)

        if ctx:
            fns = [
                partial(self._run_safely, partial(fn, ctx, event))
                for fn in self._events[event_klass]
            ]
        else:
            fns = [
                partial(self._run_safely, partial(fn, event)) for fn in self._events[event_klass]
            ]

        for fn in fns:
            await self._nursery.start(fn)

    @overload
    def add_event_handler(
        self, event: type[GwEventT], handler: Callable[[GwEventT], Awaitable[None]]
    ) -> None: ...

    @overload
    def add_event_handler(
        self,
        event: type[DsEventT],
        handler: Callable[[EventContext, DsEventT], Awaitable[None]],
    ) -> None: ...

    def add_event_handler(
        self,
        event: type[GwEventT] | type[DsEventT],
        handler: Callable[[GwEventT], Awaitable[None]]
        | Callable[[EventContext, DsEventT], Awaitable[None]],
    ) -> None:
        """
        Adds an event handler for a low-level gateway event.

        :param event: Either an incoming :class:`.IncomingGatewayEvent` or a
            :class:`.DispatchedEvent` to listen for.

        :param handler: The event handler for said event. The type of this depends on the type of
            ``event``:

            - If ``event`` is a :class:`.GatewayEvent`, this only takes the event instance.
            - If ``event`` is a :class:`.DispatchedEvent`, this takes a :class:`.EventContext`
              as well as the event instance.

            The same function can be registered for multiple events. (You can type hint it with
            a union type.)
        """

        logger.info("Registered event", handler=handler.__name__, event_type=event.__name__)

        self._events[event].append(handler)

    async def run_forever(self, *, enable_chunking: bool = True) -> NoReturn:  # type: ignore[misc]
        """
        Runs the event dispatcher forever for the provided client.

        :param enable_chunking: If automatic guild member chunking will be enabled or not.
            See :ref:`guild-chunking` for more information.
        """

        async with (
            self.client.start_receiving_events() as stream,
            anyio.create_task_group() as group,
        ):
            if enable_chunking:
                group.start_soon(partial(self.chunker.send_to_outgoing, collection=stream))

            async for event in stream:
                # all gateway events need to be dispatched normally to potential handlers
                await self._dispatch_event(type(event), ctx=None, event=event)

                if not isinstance(event, GatewayDispatch):
                    continue

                context = EventContext(
                    shard_id=event.shard_id,
                    dispatch_name=event.event_name,
                    sequence=event.sequence,
                )

                for dispatched in self.parser.get_parsed_events(
                    self.client.stateful_factory, event
                ):
                    if isinstance(dispatched, ShardReady):
                        self._ready_shards[event.shard_id] = True

                        if self._ready_shards.all():
                            await self._dispatch_event(Ready, context, Ready())

                    await self._dispatch_event(type(dispatched), context, dispatched)


@asynccontextmanager
async def create_stateful_dispatcher(
    bot: ChiruBot,
    *,
    max_tasks: int = 16,
) -> AsyncGenerator[StatefulEventDispatcher, None]:
    """
    Creates a new :class:`.StatefulEventDispatcher`.

    :param bot: The :class:`.ChiruBot` instance to dispatch events from.
    :param max_tasks: The maximum number of event tasks that can run in parallel before the
                      dispatcher stops reading from the channel temporarily.
    """

    async with open_limiting_nursery(max_tasks=max_tasks) as n:
        yield StatefulEventDispatcher(bot, n)
