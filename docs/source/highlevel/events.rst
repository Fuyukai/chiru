.. _events:

Event Handling
==============

Nearly every possible action in Discord is accompanied by an associated *dispatched event*. Chiru
wraps these up into helper classes that contain the relevant attributes associated with the 
object(s) inside the event.

There are two ways of handling dispatched events in Chiru:

- The linear way, where you subscribe directly to the stream of events.
- The dispatcher way, using a :class:`.StatefulEventDispatcher`.

Linear Events
-------------

Linear event handling is the simplest mechanism for event handling, consisting of reading events
from the gateway channel and passing them to a :class:`.CachedEventParser` to produce dispatched
events.

.. code-block:: python

    # This uses 3.10+ syntax for parenthesized context managers. 
    # See: https://docs.python.org/3.10/whatsnew/3.10.html#parenthesized-context-managers
    async with (
        open_bot(TOKEN) as bot,
        bot.start_receiving_events() as stream,
    ):
        parser = CachedEventParser(bot.object_cache, bot.cached_gateway_info.shards)
        
        async for event in stream:
            if not isinstance(event, GatewayDispatch):
                continue

            dispatched_events = parser.get_parsed_events(bot.stateful_factory, event)
            for evt in dispatched_events:
                print(f"event on shard {event.shard_id}: {evt}")


.. autoclass:: chiru.event.parser.CachedEventParser
   :special-members: __init__

Stateful Event Dispatcher
-------------------------

A more traditional form of event handling is in the form of the event dispatcher. The 
:class:`.StatefulEventDispatcher` will handle receiving incoming events automatically and 
dispatching them to a number of background tasks.

.. warning:: 

    Event dispatching in this form breaks structured concurrency and backpressure by reading tasks
    from the channel and fobbing them off to spawned tasks, meaning that the channel producer will
    continue to buffer events infinitely.

    To avoid this, the stateful event dispatcher caps the number of concurrent event handling
    children tasks with a capacity limiter. Going over this limit will cause the gateway producers
    to stop producing events, avoiding infinite in-memory buffering.

The ``StatefulEventDispatcher`` supports both gateway events and dispatched events in the same
object. To create one, you can use the :func:`.create_stateful_dispatcher` asynchronous context 
manager.

.. autofunction:: chiru.event.dispatcher.create_stateful_dispatcher

With the dispatcher open, you can then register events with 
:meth:`.StatefulEventDispatcher.add_event_handler`. This is used for both gateway events and for
dispatched events. For more information on gateway events, see :ref:`gateway-events`. Finally,
use :meth:`.StatefulEventDispatcher.run_forever` to open the gateway connection and start 
listening to inbound events.

.. code-block:: python


    async def print_message_content(ctx: EventContext, evt: MessageCreate):
        print(evt.message.content)

    async def print_dispatch(evt: GatewayDispatch):
        print("dispatched:", evt.event_name)

    async with (
        open_bot(TOKEN) as bot,
        create_stateful_dispatcher(bot) as dispatcher
    ):
        dispatcher.add_event_handler(GatewayDispatch, print_dispatch)
        dispatcher.add_event_handler(MessageCreate, print_message_content)

        await dispatcher.run_forever()


.. autoclass:: chiru.event.dispatcher.StatefulEventDispatcher
.. autoclass:: chiru.event.dispatcher.EventContext
