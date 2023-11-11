from collections.abc import Mapping
from typing import Any

import attr


class OutgoingGatewayEvent:
    """
    Marker interface for outgoing events towards the Discord gateway.
    """


@attr.s(frozen=True, slots=True, kw_only=True)
class GatewayMemberChunkRequest(OutgoingGatewayEvent):
    """
    Requests the member chunk for the provided guild.
    """

    #: The ID of the guild that chunks are being requested for.
    guild_id: int = attr.ib()

    #: The IDs of the users to get member data for.
    user_ids: list[int] = attr.ib(factory=list)

    #: The username prefix to request a member chunk for. Ignored if ``user_ids`` is non-empty.
    query: str | None = attr.ib(default=None)

    #: The maximum number of members to return. Ignored if ``user_ids`` is passed.
    limit: int | None = attr.ib(default=None)

    #: If True, presence data will be included.
    presences: bool = attr.ib(default=False)

    #: A 32 character nonce to identify this payload at the receiving end.
    nonce: str | None = attr.ib(default=None)

    def __attrs_post_init__(self):
        if not self.user_ids and self.query is None:
            raise ValueError("One of user_ids or query must be passed")

        if self.query and self.limit is None:
            raise ValueError("Limit must not be None if query is specified")


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
