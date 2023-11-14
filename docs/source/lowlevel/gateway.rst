Gateway API
===========

Whilst the HTTP API is useful for writing and querying, it's unsuitable for creating responsive
bots that need to react to events as they happen. Discord provides a Gateway which allows for bots
to receive all relevant events in real time.

Chiru implements a CSP-based gateway wrapper which handles all of the tricky parts of the connection
(reconnecting, heartbeating, and dispatching) automatically, with the :func:`.run_gateway_loop`
function. This uses multiple channels to communicate between your bot and the inner workings of the
gateway code. 

.. code-block:: python

    # The gateway function is a ``NoReturn``, as it loops forever; it needs to be ran in its
    # own separate task. This task should be bound to the lifetime of your bot.
    async with anyio.create_task_group() as nursery:
        # Return type is Write/Read for this, so theirs is Read for Outbound, and Write for Inbound.
        outgoing_ours, outgoing_theirs = anyio.create_memory_object_stream[OutgoingGatewayEvent]()
        incoming_theirs, incoming_ours = anyio.create_memory_object_stream[IncomingGatewayEvent]()

        p = partial(
            run_gateway_loop,
            initial_url="wss://gateway.discord.gg/",
            token=BOT_TOKEN,
            shard_id=0,
            shard_count=1,
            outbound_channel=outgoing_theirs,
            inbound_channel=incoming_theirs,
        )
        nursery.start_soon(p)

        async for message in incoming_ours:
            print(message)

.. autofunction:: chiru.gateway.conn.run_gateway_loop

.. _gateway-events:

Gateway Events
--------------

Gateway events are divided into two different types; *incoming* and *outgoing*. As the names 
suggest, incoming events are only ever received and outgoing events are only ever sent. These
inherit from their appropriate base classes.


.. _voidable-events:

Voidable Events
~~~~~~~~~~~~~~~

Certain incoming gateway events are marked as *voidable* events. These are events that are primarily
used for statistics or logging, and otherwise are largely not useful for most bots. These events
will *not* block the event channel and will simply be discarded if nobody is listening to the
channel.

Outgoing Events
~~~~~~~~~~~~~~~

.. autoclass:: chiru.gateway.event.OutgoingGatewayEvent

.. autoclass:: chiru.gateway.event.GatewayMemberChunkRequest

Incoming Events
~~~~~~~~~~~~~~~

.. autoclass:: chiru.gateway.event.IncomingGatewayEvent
    :members:

.. autoclass:: chiru.gateway.event.GatewayHello
.. autoclass:: chiru.gateway.event.GatewayReconnectRequested
.. autoclass:: chiru.gateway.event.GatewayHeartbeatSent
.. autoclass:: chiru.gateway.event.GatewayHeartbeatAck
.. autoclass:: chiru.gateway.event.GatewayInvalidateSession
.. autoclass:: chiru.gateway.event.GatewayDispatch
