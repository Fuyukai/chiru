.. Chiru documentation master file, created by
   sphinx-quickstart on Sat Nov 11 06:36:52 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Chiru's documentation!
=================================

*Chiru* is a Python 3.12+ asynchronous wrapper for the Discord HTTP API and gateway, using the
`AnyIO`_ library. It is designed for writing traditional (think 2017 style) Discord bots.

Installation
------------

Chiru is available on PyPI under the ``chiru`` package name:

.. tab:: Poetry

    .. code-block:: fish

        $ poetry add chiru@latest

.. tab:: PDM

    .. code-block:: fish

        $ pdm add chiru


Alternatively, you can install the latest development version:

.. tab:: Poetry

    .. code-block:: fish

        $ poetry add git+https://github.com/Fuyukai/chiru.git

.. tab:: PDM

    .. code-block:: fish

        $ pdm add "chiru @ git+https://github.com/Fuyukai/chiru.git@mizuki"


Getting Started
---------------

.. toctree::
   :maxdepth: 1
   :caption: Tutorials

   tutorials/01_basic_bot.rst


Low-level API
-------------

Chiru provides low-level access to the Discord API, via raw access to the HTTP API as well as
raw access to the gateway system. These APIs are generally not needed for most bots; the
:ref:`highlevel` API exposes some of the lower-level mechanisms as an escape hatch instead.


.. toctree::
   :maxdepth: 2
   :caption: Low-level API

   lowlevel/http.rst
   lowlevel/gateway.rst

.. _highlevel:

High-level API
--------------

The high-level API is the preferred API for writing bots that act like traditional bots; i.e,
they respond interactively to user-initiated actions. 

.. toctree:: 
   :maxdepth: 2
   :caption: High-level API

   highlevel/models.rst
   highlevel/client.rst
   highlevel/events.rst
   highlevel/channels.rst
   highlevel/messages.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _AnyIO: https://anyio.readthedocs.io/en/stable/
