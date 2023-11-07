from contextlib import asynccontextmanager
from typing import AsyncContextManager

import anyio
import httpx

from chiru.cache import ObjectCache
from chiru.gateway.collection import GatewayCollection
from chiru.http.client import ChiruHttpClient
from chiru.http.response import GatewayResponse
from chiru.models.factory import StatefulObjectFactory
from chiru.models.oauth import OAuthApplication


class ChiruBot(object):
    """
    The primary bot class.
    """

    def __init__(
        self,
        *,
        http: ChiruHttpClient,
        app: OAuthApplication,
        gw: GatewayResponse,
        token: str,
    ):
        #: The HTTP client that is used for making HTTP requests. This is pre-configured with
        #: authentication and ratelimit support, and can be used directly to access endpoints that
        #: are not otherwise exposed.
        self.http = http

        #: The :class:`.OAuthApplication` that this bot is running under.
        self.app = app

        #: The :class:`.StatefulObjectFactory` that can be used to create :ref:`stateful objects`
        #: from raw response bodies.
        self.stateful_factory = StatefulObjectFactory(self)

        #: The cached gateway response created when the bot opened.
        self.cached_gateway_info: GatewayResponse = gw

        self.__token = token

    @property
    def object_cache(self) -> ObjectCache:
        """
        The :class:`.ObjectCache` that this bot owns.
        """

        return self.stateful_factory.object_cache

    def start_receiving_events(
        self,
    ) -> AsyncContextManager[GatewayCollection]:
        """
        Starts receiving inbound events from the gateway on all available shards.
        """

        @asynccontextmanager
        async def _do():
            async with anyio.create_task_group() as nursery:
                wrapper = GatewayCollection(
                    nursery,
                    self.__token,
                    self.cached_gateway_info.url,
                    self.cached_gateway_info.shards,
                )

                for shard in range(0, self.cached_gateway_info.shards):
                    wrapper._start_shard(shard)

                try:
                    yield wrapper
                finally:
                    nursery.cancel_scope.cancel()

        return _do()


def open_bot(
    token: str,
) -> AsyncContextManager[ChiruBot]:
    """
    Opens a new :class:`.ChiruBot` instance. This is an async context manager function.

    :param token: The token to connect to Discord with.
    """

    @asynccontextmanager
    async def _do():
        async with (
            httpx.AsyncClient() as httpx_client,
            anyio.create_task_group() as http_nursery,
        ):
            http = ChiruHttpClient(httpx_client=httpx_client, nursery=http_nursery, token=token)
            app = await http.get_current_application_info()
            gateway = await http.get_gateway_info()

            try:
                yield ChiruBot(http=http, app=app, token=token, gw=gateway)
            finally:
                http_nursery.cancel_scope.cancel()

    return _do()
