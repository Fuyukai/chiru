from collections import defaultdict
from collections.abc import Awaitable, Callable, MutableMapping
from functools import partial
from typing import (
    Any,
    NoReturn,
    TypeVar,
    final,
    overload,
)

import anyio
import attr
import structlog
from anyio.abc import ObjectReceiveStream, ObjectSendStream, TaskGroup
from bitarray.util import zeros

from chiru.bot import ChiruBot
from chiru.event.model import DispatchedEvent, Ready, ShardReady
from chiru.event.parser import CachedEventParser
from chiru.gateway.collection import GatewayCollection
from chiru.gateway.event import GatewayDispatch, IncomingGatewayEvent, OutgoingGatewayEvent

logger: structlog.stdlib.BoundLogger = structlog.get_logger(name=__name__)

GwEventT = TypeVar("GwEventT", bound=IncomingGatewayEvent)
DsEventT = TypeVar("DsEventT", bound=DispatchedEvent)

type Dispatch[T: DispatchedEvent] = tuple[EventContext, T]
type DispatchChannel[T: DispatchedEvent] = ObjectReceiveStream[Dispatch[T]]
type GatewayChannel[T: IncomingGatewayEvent] = ObjectReceiveStream[T]


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class EventContext:
    """
    Contains additional context for a single dispatched event.
    """

    _collection: GatewayCollection = attr.ib(alias="collection")

    #: A reference to the shared client that this event was dispatched from.
    client: ChiruBot = attr.ib()

    #: The shard that this event was received on.
    shard_id: int = attr.ib()

    #: The name of the dispatch event that caused this event, if any.
    dispatch_name: str | None = attr.ib()

    #: The sequence number for this event.
    sequence: int = attr.ib()

    async def send_to_gateway(self, /, evt: OutgoingGatewayEvent) -> None:
        """
        Sends a single event to the gateway on this shard.
        """

        await self._collection.send_to_shard(self.shard_id, evt)


# conceptually, I can't say I'm a fan of having this own a bunch of the tasks.
# but in practice, I can't see anyone not using a wrapper to automatically spawn the tasks.
# so i'll just merge them.


@final
class ChannelDispatcher:
    """
    An event dispatcher that works by publishing constructed events to the provided channels.
    """

    # TODO: Automatically restart spawned tasks
    @staticmethod
    async def _owns_channel_wrapper[T: DispatchedEvent](
        channel: DispatchChannel[T], next_fn: Callable[[DispatchChannel[T]], Awaitable[NoReturn]]
    ) -> NoReturn:
        async with channel:
            await next_fn(channel)

    def __init__(self) -> None:
        # un type hinted because there's no nice way of type hinting this.
        self._channels: MutableMapping[type[Any], list[ObjectSendStream[Any]]] = defaultdict(list)

        self._to_run_tasks: list[
            tuple[
                type[DispatchedEvent],
                Callable[[DispatchChannel[DispatchedEvent]], Awaitable[NoReturn]],
                float,
            ]
        ] = []

    @overload
    def register_channel[T: IncomingGatewayEvent](
        self, evt: type[T], channel: ObjectSendStream[T]
    ) -> None:
        ...

    @overload
    def register_channel[T: DispatchedEvent](
        self, evt: type[T], channel: ObjectSendStream[tuple[EventContext, T]]
    ) -> None:
        ...

    def register_channel[Dispatched: DispatchedEvent, GwEvt: IncomingGatewayEvent](
        self,
        evt: type[GwEvt] | type[Dispatched],
        channel: ObjectSendStream[GwEvt] | ObjectSendStream[tuple[EventContext, Dispatched]],  # type: ignore  # pyright bug?
    ) -> None:
        """
        Registers a single channel with the channel dispatcher. This is the low-level machinery
        for event handling; see :func:`.register_event_handling_task` for dealing with dispatched
        events.

        :param evt: The :class:`.DispatchedEvent` or :class:`.IncomingGatewayEvent` to listen to.
        :param channel: A :class:`.ObjectSendStream` that will have incoming events published on.
        """

        self._channels[evt].append(channel)

    def register_event_handling_task[Dispatched: DispatchedEvent](
        self,
        evt: type[Dispatched],
        task: Callable[[DispatchChannel[Dispatched]], Awaitable[NoReturn]],
        *,
        buffer_size: float = 0,
    ) -> None:
        """
        Registers a single event handler that will be automatically spawned with a channel when
        the dispatcher starts. This is a more convenient, high-level alternative to
        :func:`.register_channel` that automatically registers the channel for you.

        :param evt: The type of the :class:`.DispatchedEvent` to listen for.
        :param task: A callable that will be spawned upon calling :func:`.run_forever`. This
            callable should receive on the provided channel forever, and never exit.

        :param buffer_size: The maximum buffer size of the created channel. This defaults to zero;
            i.e. the channel acts as a transfer queue and will pass items directly from receiver
            to sender without any buffering in order to apply backpressure.
        """

        self._to_run_tasks.append((evt, task, buffer_size))  # type: ignore  # whatever

    def _setup_tasks(self, nursery: TaskGroup) -> None:
        for type, task, buf_size in self._to_run_tasks:
            (write, read) = anyio.create_memory_object_stream[tuple[EventContext, DispatchedEvent]](
                max_buffer_size=buf_size
            )
            self.register_channel(type, write)

            fn = partial(
                self._owns_channel_wrapper,
                read,
                task,
            )
            nursery.start_soon(fn)

    async def _dispatch(
        self,
        event: IncomingGatewayEvent | DispatchedEvent,
        context: EventContext | None = None,
    ):
        """
        Dispatches a single incoming event.
        """

        # no runtime type checking here!
        handlers = self._channels[type(event)]
        if not handlers:
            return

        logger.debug("Dispatching event", event_type=type(event).__name__)
        to_send = event if context is None else (context, event)

        for handler in handlers:
            try:
                await handler.send(to_send)
            except anyio.BrokenResourceError as e:
                logger.warning("Handler channel closed", exc_info=e, handling=type(event))

                # a bit slower but it also means we don't allocate a set() every single dispatch
                # or something similar. also no fucking about with mutating during iteration
                self._channels[type(event)] = [c for c in handlers if c != handler]

    async def run_forever(
        self,
        bot: ChiruBot,
        collection: GatewayCollection,
    ) -> NoReturn:
        """
        Runs the dispatcher forever using the provided :class:`.ChiruBot` instance.
        """

        parser = CachedEventParser(bot.object_cache, bot.cached_gateway_info.shards)
        ready_shards = zeros(bot.cached_gateway_info.shards)
        has_fired_ready = False

        async with anyio.create_task_group() as nursery:
            self._setup_tasks(nursery)

            async for message in collection:
                await self._dispatch(message)

                if isinstance(message, GatewayDispatch):
                    events = parser.get_parsed_events(bot.stateful_factory, message)
                    context = EventContext(
                        collection=collection,
                        client=bot,
                        shard_id=message.shard_id,
                        dispatch_name=message.event_name,
                        sequence=message.sequence,
                    )

                    for event in events:
                        if isinstance(event, ShardReady):
                            ready_shards[message.shard_id] = True

                            if ready_shards.all() and not has_fired_ready:
                                await self._dispatch(Ready(), context)
                                has_fired_ready = True

                        await self._dispatch(event, context=context)


def start_consumer_task[T: DispatchedEvent](
    nursery: TaskGroup,
    dispatcher: ChannelDispatcher,
    evt: type[T],
    fn: Callable[[DispatchChannel[T]], Awaitable[None]],
) -> None:
    """
    Helper for registering a new consumer task. Like
    :func:`.ChannelDispatcher.register_event_handling_task`, but allows you to bring along your
    own :class:`.TaskGroup` instead.
    """

    (write, read) = anyio.create_memory_object_stream[tuple[EventContext, T]]()

    async def _task():
        async with read:
            await fn(read)

    dispatcher.register_channel(evt, write)
    nursery.start_soon(_task)
