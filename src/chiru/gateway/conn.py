import contextlib
import enum
import json
import logging
import zlib
from functools import partial
from typing import Any

import anyio
import attr
from anyio import WouldBlock
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from furl import furl
from stickney import WebsocketClient, WebsocketClosedError, open_ws_connection
from stickney.frame import BinaryMessage, CloseMessage, TextualMessage

from chiru.gateway.event import (
    GatewayDispatch,
    GatewayHeartbeatAck,
    GatewayHeartbeatSent,
    GatewayHello,
    GatewayInvalidateSession,
    GatewayReconnectRequested,
    IncomingGatewayEvent,
    OutgoingGatewayEvent,
)

INTENTS = (1 << 22) - 1
PRIVILEGED_INTENTS_MESSAGE = (
    "Chiru requires privileged intents to function properly. "
    "Please make sure that they are enabled in your bot page."
)


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

    logger: logging.Logger = attr.ib(init=False)

    def __attrs_post_init__(self):
        self.logger = logging.getLogger(f"chiru.gateway:shard-{self.shard_id}")

    def reset(self):
        self.session_id = None
        self.sequence = 0
        self.heartbeat_acks = 0
        self.heartbeat_number = 0


class GatewaySenderWrapper:
    """
    Wraps several common operations for sending on the gateway.
    """

    def __init__(self, ws: WebsocketClient, logger: logging.Logger):
        self._ws = ws
        self.logger = logger

    async def send_heartbeat(self, *, seq: int):
        self.logger.debug(f"CLI -> SRV: Heartbeat (seq: {seq})")

        body = {"op": GatewayOp.HEARTBEAT, "d": seq}

        return await self._ws.send_message(json.dumps(body))

    async def send_identify(
        self,
        *,
        token: str,
        shard_id: int,
        shard_count: int,
    ):
        self.logger.debug("CLI -> SRV: Identify")

        body = {
            "op": GatewayOp.IDENTIFY,
            "d": {
                "token": token,
                "properties": {"os": "System V", "browser": "Chiru", "device": "Chiru"},
                "compress": True,
                "shard": [shard_id, shard_count],
                "intents": INTENTS,
                "large_threshold": 50,
            },
        }

        return await self._ws.send_message(json.dumps(body))

    async def send_resume(self, *, token: str, session_id: str, seq: int):
        self.logger.debug(f"CLI -> SRV: Resume (seq: {seq})")

        body = {
            "op": GatewayOp.RESUME,
            "d": {
                "token": token,
                "session_id": session_id,
                "seq": seq,
            },
        }

        return await self._ws.send_message(json.dumps(body))


async def _gw_receive_pump(ws: WebsocketClient, channel: MemoryObjectSendStream):
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
    external_chan: MemoryObjectReceiveStream[OutgoingGatewayEvent],
    loop_chan: MemoryObjectSendStream,
):
    """
    The Gateway send pumper. Takes incoming messages from the bot and passes them along to our
    internal channel.
    """

    while True:
        incoming_message = await external_chan.receive()
        await loop_chan.send(incoming_message)


async def _super_loop(
    shared_state: GatewaySharedState,
    ws: WebsocketClient,
    central_channel: MemoryObjectReceiveStream,
    event_channel: MemoryObjectSendStream[IncomingGatewayEvent],
):
    """
    The main super loop process that deals with the websocket.
    """

    shared_state.logger.debug("Starting websocket main loop!")
    wrapped = GatewaySenderWrapper(ws, shared_state.logger)

    # 45_000 is a reasonable default value. It's what Discord has used for... a very long time.
    time_inbetween_heartbeats = 41.250
    # We use the absolute time with deadlines to ensure we don't lag on our heartbeats.
    next_heartbeat_time = anyio.current_time() + time_inbetween_heartbeats

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
            shared_state.logger.debug(
                f"Sending heartbeat #{shared_state.heartbeat_number} with sequence "
                f"{shared_state.sequence}"
            )

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
        if isinstance(next_message, OutgoingGatewayEvent):
            # TODO!
            continue

        # Incoming messages are either regular textual messages which contain a JSON body, or
        # binary-encoded messages that may contain either Erlang Term Format, or compressed data.
        # TODO: consider erlpack (again).
        decoded_content: dict[str, Any]
        if isinstance(next_message, TextualMessage):
            # Regular, JSON-encoded textual messages.

            shared_state.logger.debug(
                f"SRV -> CLI: [Websocket Text ({len(next_message.body)} chars)]"
            )
            decoded_content = json.loads(next_message.body)

        elif isinstance(next_message, BinaryMessage):
            # These are payload compressed messages (for now) - as opposed to transport
            # compression, which compresses *all* messages; we don't support that (yet).

            shared_state.logger.debug(
                f"SRV -> CLI: [Websocket Binary ({len(next_message.body)} bytes)]"
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

            time_inbetween_heartbeats: float = raw_data["heartbeat_interval"] / 1000.0
            shared_state.logger.debug("SRV -> CLI: Hello")

            shared_state.logger.info(f"Heartbeating every {time_inbetween_heartbeats} seconds...")
            shared_state.logger.debug(f"Trace: {raw_data.get('_trace')}")

            if shared_state.session_id is not None:
                shared_state.logger.debug("Resuming our previous session...")
                await wrapped.send_resume(
                    token=shared_state.token,
                    session_id=shared_state.session_id,
                    seq=shared_state.sequence,
                )
            else:
                shared_state.logger.debug("No session found, asking for a new one.")
                await wrapped.send_identify(
                    token=shared_state.token,
                    shard_id=shared_state.shard_id,
                    shard_count=shared_state.shard_count,
                )

            evt = GatewayHello(
                shard_id=shared_state.shard_id,
                heartbeat_interval=time_inbetween_heartbeats,
            )
            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(evt)

        elif opcode == GatewayOp.RECONNECT:
            # Discord wants us to reconnect. Okay.

            shared_state.logger.debug("SRV -> CLI: Reconnect")
            await ws.close(code=1001, reason="Gateway is reconnecting!")

            evt = GatewayReconnectRequested(shard_id=shared_state.shard_id)
            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(evt)

            raise WebsocketClosedError(code=1001, reason="Gateway is reconnecting!")

        elif opcode == GatewayOp.HEARTBEAT_ACK:
            # We keep track of our ack count so that we can easily detect zombied connections.

            shared_state.logger.debug(
                f"SRV -> CLI: Heartbeat Ack (count: {shared_state.heartbeat_acks})"
            )
            shared_state.logger.debug(f"Received heartbeat ack #{shared_state.heartbeat_acks}")
            shared_state.heartbeat_acks += 1

            evt = GatewayHeartbeatAck(
                shard_id=shared_state.shard_id,
                heartbeat_ack_count=shared_state.heartbeat_acks,
            )

            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(evt)

        elif opcode == GatewayOp.HEARTBEAT:
            # Occasionally, Discord asks us for a heartbeat. I don't really know why, but they do.
            # So we need to send one back.

            shared_state.logger.debug("SRV -> CLI: Heartbeat")
            await wrapped.send_heartbeat(seq=shared_state.sequence)
            shared_state.heartbeat_number += 1

            evt = GatewayHeartbeatSent(
                shard_id=shared_state.shard_id,
                heartbeat_count=shared_state.heartbeat_number,
                sequence=shared_state.sequence,
            )
            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(evt)

        elif opcode == GatewayOp.DISPATCH:
            # Dispatches update the sequence data, which is needed for heartbeats.

            seq = int(decoded_content["s"])
            assert seq >= shared_state.sequence, "sequence went backwards!"
            shared_state.sequence = seq

            dispatch_name = decoded_content["t"]
            shared_state.logger.debug(f"SRV -> CLI: Dispatch (evt: {dispatch_name}, seq: {seq})")

            if dispatch_name == "READY":
                id = raw_data["user"]["id"]
                username = raw_data["user"]["username"]

                shared_state.reconnect_url = raw_data["resume_gateway_url"]
                shared_state.session_id = raw_data["session_id"]

                shared_state.logger.info(
                    f"We have been issued a session for user {username} ({id})"
                )

            event = GatewayDispatch(
                shard_id=shared_state.shard_id,
                event_name=dispatch_name,
                sequence=seq,
                body=raw_data,
            )
            await event_channel.send(event)

        elif opcode == GatewayOp.INVALIDATE_SESSION:
            # Discord is telling us that we need to get a new session.
            # If the data is true, then we can resume...
            # If it's not, then we have to issue a second identify.
            # Note that in some cases when there's an outage, we will get stuck in a loop of
            # IDENTIFY -> INVALIDATE_SESSION -> IDENTIFY -> ...

            shared_state.logger.debug(f"SRV -> CLI: Invalidate Session (resumable: {raw_data})")

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
                )

            evt = GatewayInvalidateSession(shard_id=shared_state.shard_id, resumable=raw_data)
            with contextlib.suppress(WouldBlock):
                event_channel.send_nowait(evt)

        else:
            shared_state.logger.warning("Unknown event...")


# TODO: Add the ability to reconfigure shard data.
async def run_gateway_loop(
    *,
    initial_url: str,
    token: str,
    shard_id: int,
    shard_count: int,
    outbound_channel: MemoryObjectReceiveStream[OutgoingGatewayEvent],
    inbound_channel: MemoryObjectSendStream[IncomingGatewayEvent],
):
    """
    Runs the gateway loop forever. This should be ran in its own task.

    :param initial_url: The initial URL to connect to the gateway to.
    :param token: The Bot token to use when identifying.
    :param shard_id: The shard ID that this gateway will use.
    :param shard_count: The number of shards in total that will be spawned, including this one.
    :param outbound_channel: The channel to receive outbound events on.
    :param inbound_channel: The channel to inbound publish gateway events on.
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
        shared_state.logger.info(f"Opening new WebSocket connection to {parsed_url!s}")

        async with (
            open_ws_connection(str(parsed_url)) as ws,
            anyio.create_task_group() as nursery,
        ):
            write, read = anyio.create_memory_object_stream[Any]()

            nursery.start_soon(partial(_gw_receive_pump, ws, write))
            nursery.start_soon(partial(_gw_send_pump, outbound_channel, write))

            try:
                await _super_loop(shared_state, ws, read, inbound_channel)
            except WebsocketClosedError as e:
                match e.code:
                    case 4004:
                        raise ValueError("Invalid token!") from e
                    case 4010 | 4011:
                        raise RuntimeError("Resharding not yet impl'd") from e
                    case 4013 | 4014:
                        raise RuntimeError(PRIVILEGED_INTENTS_MESSAGE) from e
                    case _:
                        shared_state.logger.warning(
                            f"Received unexpected close {e.code} ({e.reason}), reconnecting..."
                        )
            finally:
                # kill both the pumping tasks, close the websocket, and retry.
                nursery.cancel_scope.cancel()
