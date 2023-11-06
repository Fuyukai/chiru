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
class GatewayHello(IncomingGatewayEvent):
    """
    The HELLO event from the gateway. This is a :ref:`voidable <Voidable Events>` event.
    """

    #: The time, in seconds, between subsequent heartbeats.
    heartbeat_interval: float = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
class GatewayReconnectRequested(IncomingGatewayEvent):
    """
    Published when the gateway has a reconnect requested by the other side. This is a
    :ref:`voidable <Voidable Events>` event.
    """


@attr.s(frozen=True, slots=True, kw_only=True)
class GatewayHeartbeatSent(IncomingGatewayEvent):
    """
    Published when the gateway is sending a heartbeat. This is a :ref:`voidable <Voidable Events>`
    event.
    """

    #: The number of heartbeats that we have sent, including this one.
    heartbeat_count: int = attr.ib()

    #: The sequence sent alongside this heartbeat.
    sequence: int = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
class GatewayHeartbeatAck(IncomingGatewayEvent):
    """
    Published when the gateway has received a heartbeat ack. This is a
    :ref:`voidable <Voidable Events>` event.
    """

    #: The number of heartbeat acks that we have received, including this one.
    heartbeat_ack_count: int = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
class GatewayInvalidateSession(IncomingGatewayEvent):
    """
    Published when our IDENTIFY or RESUME failed. This is a :ref:`voidable <Voidable Events>` event.
    """

    #: If we can resume after this or not.
    resumable: bool = attr.ib()


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
