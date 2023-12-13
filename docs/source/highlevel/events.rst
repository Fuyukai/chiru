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

Channel Event Dispatcher
------------------------

The channel event dispatcher is a higher-level mechanism for handling events based around routing
events to handlers via channels using the :class:`.ChannelDispatcher`.

A single event handler is a function that takes a :class:`.ObjectReadStream` passed in, and
infinitely loops over the content to stream all incoming events of that type:

.. code-block:: python

    # DispatchChannel is a type alias for ObjectReadStream[tuple[EventContext, T]].
    # It can be used in place of typing out the actual stream type.
    async def print_message_content(self, channel: DispatchChannel[MessageCreate]) -> NoReturn:
        async for (context, event) in channel:
            print(event.message.content)

Each channel produces a tuple of a :class:`.EventContext`, which provides additional data about the
dispatched event such as the shard ID and a reference to the client, and an instance of the actual
event requested.

Then, it can be registered with the :class:`.ChannelDispatcher` like so:

.. code-block:: python

    async def main():
        dispatcher = ChannelDispatcher()
        dispatcher.register_event_handling_function(MessageCreate, print_message_content)

Multiple functions can be registered for the same event, and multiple events for the same function.

Finally, the client can be connected and the dispatcher can be started in order to route events:

.. code-block:: python

    async with (
        open_bot(token) as bot,
        bot.start_receiving_events() as collection,
    ):
        await dispatcher.run_forever(bot, collection)

.. warning::

    The channel dispatcher heavily applies the concept of *backpressure*. If an event handler is not
    available to receive an event from the channel then *no events* will be processed until that
    event handler is ready. This avoids your bot having a catastrophic resource overload trying to
    process too many events.

    To avoid this, you can either set a buffer size on the created channels so that the dispatcher
    can continue processing events in the background, or you should do complex work that might
    suspend the bot in its own background task via your own :class:`.TaskGroup`.


.. autoclass:: chiru.event.dispatcher.ChannelDispatcher
.. autoclass:: chiru.event.dispatcher.EventContext
