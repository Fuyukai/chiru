from collections.abc import Mapping
from typing import Any, final

import attr

from chiru.models.presence import Activity, SendablePresenceStatus

# Not really a fan of bleeding over model code here...


class OutgoingGatewayEvent:
    """
    Marker interface for outgoing events towards the Discord gateway.
    """


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GatewayPresenceUpdate(OutgoingGatewayEvent):
    """
    Updates the presence for the current bot user on the current shard.
    """

    #: The status for this user.
    status: SendablePresenceStatus = attr.ib()

    #: The list of activities for this user.
    activities: list[Activity] = attr.ib(factory=list)

    # not sure what these fields are for. userbots? but why are they documented.
    #: The absolute Unix time (milliseconds) for when the client went idle, or None if not idle.
    since: int | None = attr.ib(default=None)

    #: If True, this client is considered AFK.
    afk: bool = attr.ib(default=False)


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GatewayMemberChunkRequest(OutgoingGatewayEvent):
    """
    Requests the member chunk for the provided guild. One of :attr:`.user_ids` or :attr:`.query`
    must be passed.
    """

    #: The ID of the guild that chunks are being requested for.
    guild_id: int = attr.ib()

    #: The IDs of the users to get member data for. This may be empty if this chunk request is for
    #: all users in the guild.
    user_ids: list[int] = attr.ib(factory=list)

    #: The username prefix to request a member chunk for. Ignored if ``user_ids`` is non-empty.
    query: str | None = attr.ib(default=None)

    #: The maximum number of members to return. Ignored if ``user_ids`` is passed.
    limit: int | None = attr.ib(default=None)

    #: If True, presence data will be included.
    presences: bool = attr.ib(default=False)

    #: A 32 character nonce to identify this payload at the receiving end.
    nonce: str | None = attr.ib(default=None)

    def __attrs_post_init__(self) -> None:
        if not self.user_ids and self.query is None:
            raise ValueError("One of user_ids or query must be passed")

        if self.query and self.limit is None:
            raise ValueError("Limit must not be None if query is specified")


@attr.s(frozen=True, slots=True, kw_only=True)
class IncomingGatewayEvent:
    """
    Marker interface for incoming events from the Discord gateway.
    """

    #: The shard ID this event came from. Used to uniquely identify events during multi-shard
    #: situations.
    shard_id: int = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GatewayHello(IncomingGatewayEvent):
    """
    The HELLO event from the gateway. This is a :ref:`voidable <voidable-events>` event.
    """

    #: The time, in seconds, between subsequent heartbeats.
    heartbeat_interval: float = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GatewayReconnectRequested(IncomingGatewayEvent):
    """
    Published when the gateway has a reconnect requested by the other side. This is a
    :ref:`voidable <voidable-events>` event.
    """


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GatewayHeartbeatSent(IncomingGatewayEvent):
    """
    Published when the gateway is sending a heartbeat. This is a :ref:`voidable <voidable-events>`
    event.
    """

    #: The number of heartbeats that we have sent, including this one.
    heartbeat_count: int = attr.ib()

    #: The sequence sent alongside this heartbeat.
    sequence: int = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GatewayHeartbeatAck(IncomingGatewayEvent):
    """
    Published when the gateway has received a heartbeat ack. This is a
    :ref:`voidable <voidable-events>` event.
    """

    #: The number of heartbeat acks that we have received, including this one.
    heartbeat_ack_count: int = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GatewayInvalidateSession(IncomingGatewayEvent):
    """
    Published when our IDENTIFY or RESUME failed. This is a :ref:`voidable <voidable-events>` event.
    """

    #: If we can resume after this or not.
    resumable: bool = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
@final
class GatewayDispatch(IncomingGatewayEvent):
    """
    A single dispatch event from the gateway.
    """

    #: The internal, Discord-provided name of the event being dispatched.
    event_name: str = attr.ib()

    #: The sequence number for this dispatch.
    sequence: int = attr.ib()

    #: The raw event body for this dispatch.
    body: Mapping[str, Any] = attr.ib()
