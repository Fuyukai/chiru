import logging
from functools import partial
from typing import AsyncIterator

import attr
from anyio import CancelScope
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from chiru.gateway.conn import run_gateway_loop
from chiru.gateway.event import IncomingGatewayEvent, OutgoingGatewayEvent
from chiru.util import open_channel_pair

logger = logging.getLogger(__name__)


@attr.s()
class GatewayWrapper:
    """
    Wraps state about an open Gateway connection.
    """

    write_channel: MemoryObjectSendStream[OutgoingGatewayEvent] = attr.ib()
    scope: CancelScope = attr.ib()


class GatewayCollection:
    """
    Wraps a series of running gateway tasks
    """

    def __init__(self, nursery: TaskGroup, token: str, initial_url: str, shard_count: int):
        #: The list of (shard id -> outgoing event) for all the connected gateways.
        self._gateway_ctl_channels: list[GatewayWrapper | None] = [None] * shard_count

        #: The nursery to spawn gateway loops into.
        self._nursery = nursery

        self._token = token
        self._initial_url = initial_url
        self._shard_count = shard_count

        self._event_read, self._event_write = open_channel_pair(item_type=IncomingGatewayEvent)

    def __aiter__(self) -> AsyncIterator[IncomingGatewayEvent]:
        return aiter(self._event_read)  # type: ignore

    async def _run_gateway_loop(
        self,
        *,
        shard_id: int,
    ):
        with CancelScope() as scope, self._event_write.clone() as event_channel:
            outbound_read, outbound_write = open_channel_pair(item_type=OutgoingGatewayEvent)
            wrapped = GatewayWrapper(outbound_write, scope)
            self._gateway_ctl_channels[shard_id] = wrapped

            try:
                await run_gateway_loop(
                    token=self._token,
                    initial_url=self._initial_url,
                    shard_id=shard_id,
                    shard_count=self._shard_count,
                    outbound_channel=outbound_read,
                    inbound_channel=event_channel,
                )
            finally:
                logger.debug(f"Terminated gateway connection for shard {shard_id}")
                outbound_read.close()
                outbound_write.close()
                self._gateway_ctl_channels[shard_id] = None

    def _start_shard(self, shard_id: int):
        self._nursery.start_soon(partial(self._run_gateway_loop, shard_id=shard_id))

    async def drain_forever(self):
        """
        Drains all events on the gateway channels forever.
        """

        async for _ in self:
            pass
