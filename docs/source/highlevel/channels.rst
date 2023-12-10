.. _channels:

Channels
========

The channel is the most fundamental unit of the Discord API. Every message is contained within
a channel, and thus nearly all interactions with a bot will go through a channel. Channels are
modelled as an inheritance tree with each branch or leaf representing a specific type of channel.

Raw & Base Channels
-------------------

:class:`.RawChannel` is the stateless model class for all channels, and contains the common 
attributes for all channels. Every model class inherits from this.

:class:`.BaseChannel` is the *base type* for stateful channels. It is not created directly and 
exists an abstract type bound for the stateful channel objects.

:class:`.AnyGuildChannel` is similar to :class:`.BaseChannel`, but it is the type bound for all
channels that are within a single guild and exposes properties for the current guild and current
guild ID. If a channel is not a :class:`.AnyGuildChannel`, then it is a direct message channel.


.. autoclass:: chiru.models.channel.RawChannel

.. autoclass:: chiru.models.channel.BaseChannel
    :show-inheritance:

.. autoclass:: chiru.models.channel.AnyGuildChannel
    :show-inheritance:

.. autoclass:: chiru.models.channel.ChannelType

.. _text-channels:

Textual Channels & Messages
---------------------------

Textual channels are channels that can have *messages* sent to them. Messages are the primary 
mechanism for interaction with most Discord bots and most bot code relates to receiving messages
in some form. Textual channels all inherit from :class:`.TextualChannel`, which has methods for
both sending and retrieving messages. 

These channels produce and send instances of :class:`.Message`. See :ref:`messages` for more
information.

.. autoclass:: chiru.models.channel.TextualChannel
    :show-inheritance:

.. autoclass:: chiru.models.channel.TextualGuildChannel
    :show-inheritance:

Category Channels
-----------------

A :class:`.CategoryChannel` is a way of grouping channels in a single guild. Every 
:class:`.AnyGuildChannel` has a ``parent_id`` field that may reference their parent channel, 
and every :class:`.CategoryChannel` instance can iterate over their children.

.. autoclass:: chiru.models.channel.CategoryChannel
    :show-inheritance:

Unsupported Channels
--------------------

In the future, Discord may add new channel types that are not supported by Chiru. These are 
represented by the :class:`.UnsupportedChannel` (and :class:`.UnsupportedGuildType`) instances.

.. autoclass:: chiru.models.channel.UnsupportedChannel
    :show-inheritance:

.. autoclass:: chiru.models.channel.UnsupportedGuildChannel
