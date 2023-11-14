The Chiru Client
================

The "main" bot class for a Chiru bot is the imaginatively named :class:`.ChiruBot`. This is,
fundamentally, a collection of the following:

- An owned :class:`.ChiruHttpClient` with the appropriate lifetime
- A :class:`.ObjectCache` that can be used to store previously-created objects
- The ability to open and track multiple gateway connections across all shards simultaneously.

It can also edit the bot's profile and cache objects created from the HTTP client.

Creating a new client
---------------------

The :func:`.open_bot` *asynchronous context manager* can be used to create a new valid client.

.. code-block:: python

    async with open_bot(token=TOKEN) as client:
        print("I am", client.app.bot.global_name)

.. autofunction:: chiru.bot.open_bot

Connecting to the Gateway
-------------------------

Using :func:`.ChiruBot.start_receiving_events`, you can open a new connection on all shards to
the Discord Gateway and start receiving events. This will return a :class:`.GatewayCollection` that
can be used to both retrieve events or send events to a specific shard.

.. code-block:: python

    async with client.start_receiving_events() as stream:
        async for message in stream:
            print(stream)

Each event here is a :class:`.IncomingGatewayEvent`. See :ref:`Gateway Events <gateway-events>` 
for more information.

.. autoclass:: chiru.gateway.collection.GatewayCollection

To handle higher-level events, see the :ref:`event handling <events>` page.
