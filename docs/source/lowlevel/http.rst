HTTP API
=========

The :class:`.ChiruHttpClient` can be used for direct access to Discord's HTTP API. This
object has both wrappers for known API methods that return 
:ref:`stateless models <stateless-model>`, as well as the ability to call arbitrary remote routes
whilst respecting Discord rate limits.

The HTTP client is bound to a lifetime of an externally created :class:`~anyio.abc.TaskGroup` and an
externally created ``AsyncClient`` from the ``httpx`` library. To create a new ``ChiruHttpClient``,
you need to provide both of these to the constructor, like so:

.. code-block:: python

    async def main():
        async with (
            httpx.AsyncClient() as httpx_client,
            anyio.create_task_group() as group,
        ):
            http_client = ChiruHttpClient(httpx_client, group, BOT_TOKEN)
            resp = await http_client.request(...)

The :class:`.ChiruHttpClient` will perform adjustments to the passed-in ``AsyncClient``
instance, including setting an authorisation and user agent header, and disabling timeouts. If you
need to make requests with a timeout, you must use the
`timeout helpers <https://anyio.readthedocs.io/en/stable/cancellation.html#timeouts>`__ provided
by the AnyIO library instead.

.. autoclass:: chiru.http.ChiruHttpClient
    :members:

Responses
---------

Some objects are only used for HTTP responses.

.. autoclass:: chiru.http.response.GatewaySessionLimits
.. autoclass:: chiru.http.response.GatewayResponse
