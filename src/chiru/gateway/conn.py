import contextlib
import enum
import json
import zlib
from collections.abc import Callable
from functools import partial
from typing import Any, NoReturn

import anyio
import attr
import structlog
from anyio import WouldBlock
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from furl import furl
from stickney import WebsocketClient, WebsocketClosedError, WsMessage, open_ws_connection
from stickney.frame import BinaryMessage, CloseMessage, TextualMessage

from chiru.gateway.event import (
    GatewayDispatch,
    GatewayHeartbeatAck,
    GatewayHeartbeatSent,
    GatewayHello,
    GatewayInvalidateSession,
    GatewayMemberChunkRequest,
    GatewayReconnectRequested,
    IncomingGatewayEvent,
    OutgoingGatewayEvent,
)

INTENTS = (1 << 22) - 1
PRIVILEGED_INTENTS_MESSAGE = (
    "Chiru requires privileged intents to function properly. "
    "Please make sure that they are enabled in your bot page."
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(name=__name__)


# Design notes.
# This is a CSP-based gateway system, using three tasks/processes.
# 1) The Incoming pumper, which receives new messages from the websocket constantly.
# 2) The Outgoing pumper, which receives messages that the client wants to send.
# 3) The super-loop, which is a state machine that handles all the intricate details of the
#    actual websocket connection.
#
# This is then wrapped in an automatic reconnection layer to isolate error handling.
#
# The obvious question is: is this a class? To that, I tell you: classes are a poor man's closure.
#
# In all honestly, this is some of the best code I've ever written in my entire life. It's a shame
# it's for a service that I hate.


class GatewayOp(enum.IntEnum):
    """
    An enumeration of possible gateway operation codes.
    """

    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE = 3
    VOICE_STATE = 4
    RESUME = 6
    RECONNECT = 7
    REQUEST_MEMBERS = 8
    INVALIDATE_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11


@attr.s(kw_only=True)
class GatewaySharedState:
    #: The URL to use whenever we need to reconnect to the gateway.
    reconnect_url: str = attr.ib()

    #: The session ID issued to us in a ready packet.
    session_id: str | None = attr.ib(default=None)

    #: The token to identify with.
    token: str = attr.ib()

    #: The shard ID to use for identifying.
    shard_id: int = attr.ib(default=0)

    #: The maximum shard count to use for identifying.
    shard_count: int = attr.ib(default=1)

    #: The current sequence number for heartbeats.
    sequence: int = attr.ib(default=0)

    #: The current heartbeat number.
    heartbeat_number: int = attr.ib(default=0)

    #: The number of heartbeat acknowledgements we've received.
    #: If this is more than two less than the heartbeat number, the connection is considered
    #: a zombie connection, and will be forcibly reconnected.
    heartbeat_acks: int = attr.ib(default=0)

    #: The buffered message we were trying to send over the websocket between closures.
    buffered_send_message: Any | None = attr.ib(default=None)

    logger: structlog.stdlib.BoundLogger = attr.ib(init=False)

    def __attrs_post_init__(self) -> None:
        self.logger = logger.bind(shard_id=self.shard_id)

    def reset(self) -> None:
        self.session_id = None
        self.sequence = 0
        self.heartbeat_acks = 0
        self.heartbeat_number = 0


class GatewaySenderWrapper:
    """
    Wraps several common operations for sending on the gateway.
    """

    def __init__(self, ws: WebsocketClient, logger: structlog.stdlib.BoundLogger) -> None:
        self._ws = ws
        self.logger = logger

    async def send_heartbeat(self, *, seq: int) -> None:
        self.logger.debug(
            "Outgoing message",
            message_type=GatewayOp.HEARTBEAT,
            seq=seq,
        )

        body = {"op": GatewayOp.HEARTBEAT, "d": seq}

        await self._ws.send_message(json.dumps(body))

    async def send_identify(
        self,
        *,
        token: str,
        shard_id: int,
        shard_count: int,
        intents: int,
    ) -> None:
        self.logger.debug("Outgoing message", message_type=GatewayOp.IDENTIFY)

        body = {
            "op": GatewayOp.IDENTIFY,
            "d": {
                "token": token,
                "properties": {"os": "System V", "browser": "Chiru", "device": "Chiru"},
                "compress": True,
                "shard": [shard_id, shard_count],
                "intents": intents,
                "large_threshold": 50,
            },
        }

        await self._ws.send_message(json.dumps(body))

    async def send_resume(self, *, token: str, session_id: str, seq: int) -> None:
        self.logger.debug(
            "Outgoing message",
            message_type=GatewayOp.RESUME,
            seq=seq,
        )

        body = {
            "op": GatewayOp.RESUME,
            "d": {
                "token": token,
                "session_id": session_id,
                "seq": seq,
            },
        }

        await self._ws.send_message(json.dumps(body))

    async def send_chunk_request(self, payload: GatewayMemberChunkRequest) -> None:
        self.logger.debug(
            "Outgoing message",
            message_type=GatewayOp.REQUEST_MEMBERS,
            guild_id=payload.guild_id,
            nonce=payload.nonce,
        )

        body: dict[str, Any] = {
            "op": GatewayOp.REQUEST_MEMBERS,
            "d": {
                "guild_id": str(payload.guild_id),
                "presences": payload.presences,
            },
        }

        if payload.user_ids:
            body["d"]["user_ids"] = payload.user_ids
        else:
            body["d"]["query"] = payload.query

        if payload.limit is not None:
            body["d"]["limit"] = payload.limit

        if payload.nonce is not None:
            body["d"]["nonce"] = payload.nonce

        await self._ws.send_message(json.dumps(body))


async def _gw_receive_pump(
    ws: WebsocketClient, channel: MemoryObjectSendStream[OutgoingGatewayEvent | WsMessage]
) -> None:
    """
    The Gateway receive pumper. Takes incoming messages from the Gateway and passes them along
    to our internal channel.
    """

    while True:
        next_message = await ws.receive_single_message(raise_on_close=False)
        await channel.send(next_message)

        if isinstance(next_message, CloseMessage):
            break


async def _gw_send_pump(
    shared_state: GatewaySharedState,
    external_chan: MemoryObjectReceiveStream[OutgoingGatewayEvent],
    loop_chan: MemoryObjectSendStream[OutgoingGatewayEvent | WsMessage],
) -> NoReturn:
    """
    The Gateway send pumper. Takes incoming messages from the bot and passes them along to our
    internal channel.
    """

    while True:
        if shared_state.buffered_send_message is None:
            shared_state.buffered_send_message = await external_chan.receive()

        await loop_chan.send(shared_state.buffered_send_message)
        shared_state.buffered_send_message = None


async def _super_loop(
    shared_state: GatewaySharedState,
    ws: WebsocketClient,
    central_channel: MemoryObjectReceiveStream[OutgoingGatewayEvent | WsMessage],
    event_channel: MemoryObjectSendStream[IncomingGatewayEvent],
    start_send_fn: Callable[[], None],
    intents: int,
) -> NoReturn:
    """
    The main super loop process that deals with the websocket.
    """

    shared_state.logger.debug("Starting websocket main loop")
    wrapped = GatewaySenderWrapper(ws, shared_state.logger)

    # 45_000 is a reasonable default value. It's what Discord has used for... a very long time.
    time_inbetween_heartbeats = 41.250
    # We use the absolute time with deadlines to ensure we don't lag on our heartbeats.
    next_heartbeat_time: float = anyio.current_time() + time_inbetween_heartbeats

    # We use this to track if we've received a Hello before needing to send our first heartbeat.
    has_received_hello = False

    while True:
        # Use a cancel scope with the absolute deadline as the heartbeat loop.
        # This ensures that heartbeating is tied to the lifetime of the superloop, as opposed to
        # the lifetime of a separate task as it was in Curious.
        with anyio.CancelScope(deadline=next_heartbeat_time) as scope:
            next_message = await central_channel.receive()

        if scope.cancelled_caught:
            if not has_received_hello:
                # We haven't received a Hello in the time it takes for us to send our first
                # heartbeat.
                # In all likelihood, some sort of network error happened and we're never going to
                # get that hello message, so let's just close the connection now.
                await ws.close(code=1006, reason="")

            # There were no messages in the time between heartbeats (or, more likely, the deadline
            # for the next one was in the future).
            # So, we need to send a heartbeat now.

            if shared_state.heartbeat_number > shared_state.heartbeat_acks + 2:
                # We haven't received a heartbeat ack in a while, so we can consider the connection
                # to be a zombie connection. Kill it.

                # Note that this is two heartbeats, in case Discord sends us a heartbeat request
                # and then our heartbeat timer expires on the next loop.
                # In that case, we might not get an ack for the first heartbeat, try to send the
                # second one, but realise we haven't gotten the ACK for the first one and die.

                with anyio.move_on_after(delay=5):
                    await ws.close(code=4100, reason="Zombie!")

                raise WebsocketClosedError(code=4100, reason="Zombie connection detected")

            await wrapped.send_heartbeat(seq=shared_state.sequence)
            next_heartbeat_time = next_heartbeat_time + time_inbetween_heartbeats
            shared_state.heartbeat_number += 1

            evt = GatewayHeartbeatSent(
                shard_id=shared_state.shard_id,
                heartbeat_count=shared_state.heartbeat_number,
                sequence=shared_state.sequence,
            )
            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(evt)

            continue

        # All incoming messages are WsMessages, all outgoing messages are not WsMessage.
        # Outgoing messages include presence updates, external closure requests (usually for
        # debugging), or guild member chunking.
        if isinstance(next_message, GatewayMemberChunkRequest):
            await wrapped.send_chunk_request(next_message)

        # Incoming messages are either regular textual messages which contain a JSON body, or
        # binary-encoded messages that may contain either Erlang Term Format, or compressed data.
        # TODO: consider erlpack (again).
        decoded_content: dict[str, Any]
        if isinstance(next_message, TextualMessage):
            # Regular, JSON-encoded textual messages.

            shared_state.logger.debug("Inbound websocket", type="text", size=len(next_message.body))
            decoded_content = json.loads(next_message.body)

        elif isinstance(next_message, BinaryMessage):
            # These are payload compressed messages (for now) - as opposed to transport
            # compression, which compresses *all* messages; we don't support that (yet).

            shared_state.logger.debug(
                "Inbound websocket", type="binary", size=len(next_message.body)
            )
            decompressed_message = zlib.decompress(next_message.body)
            decoded_content = json.loads(decompressed_message)

        elif isinstance(next_message, CloseMessage):
            # Normally the WS itself would do this for us, but since we're using a channel
            # instead we have to raise this ourselves.
            raise WebsocketClosedError(next_message.close_code, next_message.reason)

        else:
            # This covers frames like the connection accept message, or Ping/Pong frames.
            continue

        opcode = GatewayOp(decoded_content["op"])
        raw_data: Any = decoded_content["d"]

        # The "core" of any bot, the gateway operation switch.

        if opcode == GatewayOp.HELLO:
            # Sent at the start of every opened connection. This is the signal that we use to
            # log in to the remote connection.
            has_received_hello = True

            time_inbetween_heartbeats = raw_data["heartbeat_interval"] / 1000.0
            shared_state.logger.debug(
                "Inbound message",
                message_type=GatewayOp.HELLO,
                heartbeat_interval=time_inbetween_heartbeats,
            )

            if shared_state.session_id is not None:
                await wrapped.send_resume(
                    token=shared_state.token,
                    session_id=shared_state.session_id,
                    seq=shared_state.sequence,
                )
            else:
                await wrapped.send_identify(
                    token=shared_state.token,
                    shard_id=shared_state.shard_id,
                    shard_count=shared_state.shard_count,
                    intents=intents,
                )

            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(
                    GatewayHello(
                        shard_id=shared_state.shard_id,
                        heartbeat_interval=time_inbetween_heartbeats,
                    )
                )

        elif opcode == GatewayOp.RECONNECT:
            # Discord wants us to reconnect. Okay.

            shared_state.logger.debug("SRV -> CLI: Reconnect")
            shared_state.logger.debug("Inbound message", message_type=GatewayOp.RECONNECT)

            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(GatewayReconnectRequested(shard_id=shared_state.shard_id))

            raise WebsocketClosedError(code=1001, reason="Gateway is reconnecting!")

        elif opcode == GatewayOp.HEARTBEAT_ACK:
            # We keep track of our ack count so that we can easily detect zombied connections.

            shared_state.heartbeat_acks += 1
            shared_state.logger.debug(
                "Inbound message",
                message_type=GatewayOp.HEARTBEAT_ACK,
                count=shared_state.heartbeat_acks,
            )

            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(
                    GatewayHeartbeatAck(
                        shard_id=shared_state.shard_id,
                        heartbeat_ack_count=shared_state.heartbeat_acks,
                    )
                )

        elif opcode == GatewayOp.HEARTBEAT:
            # Occasionally, Discord asks us for a heartbeat. I don't really know why, but they do.
            # So we need to send one back.

            shared_state.logger.debug(
                "Inbound message", message_type=GatewayOp.HEARTBEAT, seq=shared_state.sequence
            )
            await wrapped.send_heartbeat(seq=shared_state.sequence)
            shared_state.heartbeat_number += 1

            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(
                    GatewayHeartbeatSent(
                        shard_id=shared_state.shard_id,
                        heartbeat_count=shared_state.heartbeat_number,
                        sequence=shared_state.sequence,
                    )
                )

        elif opcode == GatewayOp.DISPATCH:
            # Dispatches update the sequence data, which is needed for heartbeats.

            seq = int(decoded_content["s"])
            assert seq >= shared_state.sequence, "sequence went backwards!"
            shared_state.sequence = seq

            dispatch_name: str = decoded_content["t"]
            shared_state.logger.debug(
                "Inbound message",
                message_type=GatewayOp.DISPATCH,
                dispatched_event=dispatch_name,
                seq=seq,
            )

            if dispatch_name == "READY":
                id = raw_data["user"]["id"]
                username = raw_data["user"]["username"]

                shared_state.reconnect_url = raw_data["resume_gateway_url"]
                shared_state.session_id = raw_data["session_id"]

                shared_state.logger.debug("Issued session", username=username, id=id)

                start_send_fn()

            elif dispatch_name == "RESUME":
                start_send_fn()

            await event_channel.send(
                GatewayDispatch(
                    shard_id=shared_state.shard_id,
                    event_name=dispatch_name,
                    sequence=seq,
                    body=raw_data,
                )
            )

        elif opcode == GatewayOp.INVALIDATE_SESSION:
            # Discord is telling us that we need to get a new session.
            # If the data is true, then we can resume...
            # If it's not, then we have to issue a second identify.
            # Note that in some cases when there's an outage, we will get stuck in a loop of
            # IDENTIFY -> INVALIDATE_SESSION -> IDENTIFY -> ...

            shared_state.logger.debug(
                "Inbound message",
                message_type=GatewayOp.INVALIDATE_SESSION,
                resumable=raw_data,
            )

            if raw_data:
                # We can send a RESUME, so let's do so...
                await wrapped.send_resume(
                    token=shared_state.token,
                    session_id=shared_state.session_id,  # type: ignore
                    seq=shared_state.sequence,
                )
            else:
                # We can't, so discard our session state and try again.
                shared_state.reset()

                await wrapped.send_identify(
                    token=shared_state.token,
                    shard_id=shared_state.shard_id,
                    shard_count=shared_state.shard_count,
                    intents=intents,
                )

            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(
                    GatewayInvalidateSession(shard_id=shared_state.shard_id, resumable=raw_data)
                )

        else:
            shared_state.logger.warning("Unknown event", opcode=opcode)


# TODO: Add the ability to reconfigure shard data.
async def run_gateway_loop(
    *,
    initial_url: str,
    token: str,
    shard_id: int,
    shard_count: int,
    outbound_channel: MemoryObjectReceiveStream[OutgoingGatewayEvent],
    inbound_channel: MemoryObjectSendStream[IncomingGatewayEvent],
    intents: int = INTENTS,
) -> NoReturn:
    """
    Runs the gateway loop forever. This should be ran in its own task.

    :param initial_url: The initial URL to connect to the gateway to. This will only be used for
        the first connection; all subsequent connections will use the URL returned in the
        ``READY`` packet.

    :param token: The Bot token to use when identifying.
    :param shard_id: The shard ID that this gateway will use.
    :param shard_count: The number of shards in total that will be spawned, including this one.
    :param outbound_channel: The channel that outbound gateway events will be read from. This is
        the mechanism for sending control messages such as presence updates or user-initiated closes
        through the gateway.

        Incoming messages will be buffered automatically across reconnects, with messages that have
        failed to send being retried after reconnection.

    :param inbound_channel: The channel that incoming gateway events will be sent to.

        This channel should, ideally, have a buffer size of zero to prevent less important events
        from clogging up the channel (as they are sent without waiting, and simply discarded if
        nobody is listening).

    :param intents: The `Gateway Intents <https://discord.com/developers/docs/topics/gateway#gateway-intents>`_
        configuration that should be used for incoming events. By default, this is set to *all*
        intents.

        Note that Chiru's high-level functionality won't work without privileged intents, and the
        gateway code will fail unrecoverably if privileged intents are requested but not available.
    """

    shared_state = GatewaySharedState(
        reconnect_url=initial_url,
        token=token,
        shard_id=shard_id,
        shard_count=shard_count,
    )

    while True:
        parsed_url = furl(shared_state.reconnect_url)
        parsed_url.query.params = {"version": "10", "encoding": "json"}
        shared_state.logger.debug("Opening websocket connection", url=parsed_url)

        async with (
            open_ws_connection(str(parsed_url)) as ws,
            anyio.create_task_group() as nursery,
        ):
            write, read = anyio.create_memory_object_stream[Any]()

            nursery.start_soon(partial(_gw_receive_pump, ws, write))
            send_fn = partial(_gw_send_pump, shared_state, outbound_channel, write)
            start_send_fn = partial(nursery.start_soon, send_fn)

            try:
                await _super_loop(shared_state, ws, read, inbound_channel, start_send_fn, intents)
            except WebsocketClosedError as e:
                match e.code:
                    case 4004:
                        raise ValueError("Invalid token!") from e
                    case 4010 | 4011:
                        raise RuntimeError("Resharding not yet impl'd") from e
                    case 4013 | 4014:
                        raise RuntimeError(PRIVILEGED_INTENTS_MESSAGE) from e
                    case _:
                        shared_state.logger.warn("Unexpected close", code=e.code, reason=e.reason)
            finally:
                # kill both the pumping tasks, close the websocket, and retry.
                with anyio.move_on_after(5, shield=True):
                    await ws.close(code=1001)

                nursery.cancel_scope.cancel()
