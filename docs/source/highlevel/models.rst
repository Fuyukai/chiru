.. _models:

Model Classes
=============

Chiru provides several attr-based dataclasses that provide object representations of certain Discord
objects, found in the ``chiru.models`` package. These are divided into *stateless* (or raw) models,
and *stateful* models.

.. _stateless-model:

Stateless Models
----------------

Stateless models are simply Python objects that provide statically typed attribute access to the
properties of a Discord object. The stateless models are pre-configured with a static instance of
a :class:`cattr.Converter` that knows how to convert the fields from their JSON representation to
our attribute names.

.. code-block:: python

    from chiru.models.user import RawUser
    from chiru.serialise import CONVERTER
    
    some_user = {
        "id": "1170161182989095013", 
        "username": "chiru chiru",
        "discriminator": "0",
        "bot": True,
    }

    some_user_object = CONVERTER.structure(some_user, RawUser)
    print(some_user_object.id)  # 1170161182989095013

.. note:: 

    Some attributes have been renamed on the models to avoid clashing with the stateful model
    properties. Usually, this comes in the form of ``raw_<property_name>``.

.. warning:: 
    
    Model classes are not currently configured for serialisation. Attempting to structure a model
    class may not produce a valid Discord object as an output.

Stateful Models
---------------

Stateful models are similar to stateless models (in fact, all stateful models inherit from their
stateless variant), but additionally hold a reference to the :class:`.ChiruBot` that created them.

Stateful models can be created manually with the :class:`.StatefulObjectFactory`:

.. code-block:: python

    some_user = {
        "id": "1170161182989095013", 
        "username": "chiru chiru",
        "discriminator": "0",
        "bot": True,
    }
    
    some_user_object = bot.stateful_factory.create_user(some_user)

.. warning::

    Stateful models should be considered immutable. (They are not frozen yet, but may be in the 
    future). Do not hold direct references to them, as some operations will simply swap them out
    from underneath you in the cache.


.. autoclass:: chiru.models.factory.StatefulObjectFactory
   :members:

Snowflakes
----------

Some models inherit from :class:`.DiscordObject`, which provides the ``id`` field for the 
snowflake of the object created, as well as the timestamp of the snowflake.

.. autoclass:: chiru.models.base.DiscordObject
   :members:
