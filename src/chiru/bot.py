from contextlib import asynccontextmanager
from typing import AsyncContextManager

import anyio
import httpx

from chiru.gateway.collection import GatewayCollection
from chiru.http.client import ChiruHttpClient
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
        token: str,
    ):
        self.http = http
        self.app = app

        self.__token = token

    def start_receiving_events(
        self,
    ) -> AsyncContextManager[GatewayCollection]:
        """
        Starts receiving inbound events from the gateway on all available shards.
        """

        @asynccontextmanager
        async def _do():
            gateway_info = await self.http.get_gateway_info()

            async with anyio.create_task_group() as nursery:
                wrapper = GatewayCollection(
                    nursery, self.__token, gateway_info.url, gateway_info.shards
                )

                for shard in range(0, gateway_info.shards):
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
            http = ChiruHttpClient(
                httpx_client=httpx_client, nursery=http_nursery, token=token
            )
            app = await http.get_current_application_info()

            try:
                yield ChiruBot(http=http, app=app, token=token)
            finally:
                http_nursery.cancel_scope.cancel()

    return _do()
