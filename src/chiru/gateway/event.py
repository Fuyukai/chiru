import abc
from collections.abc import Mapping
from typing import Any

import attr


class OutgoingGatewayEvent(abc.ABC):
    """
    Marker interface for outgoing events towards the Discord gateway.
    """


@attr.s(frozen=True, slots=True, kw_only=True)
class IncomingGatewayEvent:
    """
    Marker interface for incoming events from the Discord gateway.
    """

    #: The shard ID this event came from.
    shard_id: int = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
class GatewayDispatch(IncomingGatewayEvent):
    """
    A single dispatch event from the gateway.
    """

    #: The name of the event being dispatched.
    event_name: str = attr.ib()

    #: The sequence number for this dispatch.
    sequence: int = attr.ib()

    #: The raw event body for this dispatch.
    body: Mapping[str, Any] = attr.ib()
