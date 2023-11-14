A Basic Bot
===========

This will guide you through writing a basic Chiru-based bot that simply responds to messages that
say its name.

.. warning::

    Chiru is not a library for beginners to asynchronous Python programming. You should have
    experience with Python, asynchronous Python, asynchronous Python using Trio/AnyIO, and
    at least the basics of how to get your bot token.

Setup
-----

First, create your project. I recommend using either `Poetry`_ or `PDM`_ (Poetry is what I use)
for managing things. 

.. tab:: Poetry

    .. code-block:: fish

        $ poetry new --src .
        $ poetry add chiru
    
.. tab:: PDM

    .. code-block:: fish

        $ pdm init --lib
        $ pdm add chiru

.. warning::

    If using PDM, say "yes" when it asks if you're a library - even though you're not. PDM has
    really bad behaviour for applications by default.

We're going to use the `Trio`_ runner for this bot, so you need to install it in your virtual 
environment.

.. tab:: Poetry

    .. code-block:: fish

        $ poetry add "trio>=0.23.1"
        $ poetry install

.. tab:: PDM

    .. code-block:: fish

        $ pdm add "trio>=0.23.1"
        $ pdm install --dev

Trio is the primarily supported AnyIO backend for Chiru; the ``asyncio`` backend is not recommended
due to glaring deficiencies in the design of ``asyncio``.

Your First File
---------------

Your project will now have a ``src/my_bot_package`` package in it. Create a file called ``bot.py``
in it, with this as the contents:

.. code-block:: python

    import trio

    async def main():
        print("Hello, world!")

    if __name__ == "__main__":
        trio.run(main)

Then, you need to add this as an entrypoint in your ``pyproject.toml``:

.. tab:: Poetry

    .. code-block:: toml
        
        [tool.poetry.scripts]
        my-bot = "my_bot_package.bot"

.. tab:: PDM

    .. code-block:: toml

        [project.scripts]
        my-bot = "my_bot_package.bot"

In your terminal, you can then run your "bot" like so:

.. tab:: Poetry

    .. code-block:: fish

        $ poetry install  # Only needed once, when you update the ``pyproject.toml``.
        $ poetry run my-bot

.. tab:: PDM

    .. code-block:: fish

        $ pdm install --dev # Only needed once, when you update the ``pyproject.toml``.
        $ pdm run my-bot


Actually Getting Messages
-------------------------

.. 
    TODO: put a ref to message docs when its written

What we did above was *not* a bot, but it was a way of 
`making sure we can do nothing <https://devblogs.microsoft.com/oldnewthing/20230725-00/?p=108482>`__
first. Now, let's make the actual bot.

Most (practically, all the useful ones) bots are based around responding to :ref:`events`. To
respond to messages saying our name, we need an event handler for the ``MESSAGE_CREATE`` event.
Let's create a dummy handler that just prints every message we get:

.. code-block:: python

    from chiru.event import EventContext, MessageCreate

    async def handle_message_create(context: EventContext, evt: MessageCreate):
        print("Got a message:", evt.message.content)

Now, we need to wire it up to a bot. We can do this with the :class:`.StatefulEventDispatcher`:

.. code-block:: python

    from chiru.event import create_stateful_dispatcher
    from chiru.bot import open_bot

    # Get it from the Developer Portal.
    TOKEN = "..."

    async def main():
        async with (
            open_bot(TOKEN) as bot,
            create_stateful_dispatcher(bot) as dispatcher
        ):
            dispatcher.add_event_handler(MessageCreate, handle_message_create)

            await dispatcher.run_forever()

Once again, you can run your ``my-bot`` script in your command line, and then start sending some
messages in a channel you and your bot share. 

Responding To Messages
----------------------

Now, let's add responding to messages. First, we want to change our handler to filter out messages
that don't meet certain criteria:

.. code-block:: python

    async def handle_message_create(context: EventContext, evt: MessageCreate):
        # No bot messages! You don't want to get stuck in a loop.
        if evt.message.author.bot:
            return
        
        # Ignore all messages that aren't about me.
        if "bot name" not in evt.message.content:
            return

Now, we can respond to a message on the channel it came through, like so:

.. code-block:: python

    channel = evt.message.channel
    await channel.messages.send(content="You talking to me?")

.. _Poetry: https://python-poetry.org/docs/
.. _PDM: https://pdm-project.org/latest/
.. _Trio: https://trio.readthedocs.io/en/stable/
