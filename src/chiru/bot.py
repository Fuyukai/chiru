from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import final

import anyio
import httpx

from chiru.cache import ObjectCache
from chiru.gateway.collection import GatewayCollection
from chiru.http.client import ChiruHttpClient
from chiru.http.response import GatewayResponse
from chiru.models.factory import ModelObjectFactory
from chiru.models.oauth import OAuthApplication


@final
class ChiruBot:
    """
    Primary bot class. This is a wrapper class that owns the various machinery required to connect
    to Discord.
    """

    def __init__(
        self,
        *,
        http: ChiruHttpClient,
        app: OAuthApplication,
        gw: GatewayResponse,
        token: str,
    ) -> None:
        #: The HTTP client that is used for making HTTP requests. This is pre-configured with
        #: authentication and ratelimit support, and can be used directly to access endpoints that
        #: are not otherwise exposed.
        self.http: ChiruHttpClient = http

        #: The :class:`.OAuthApplication` that this bot is running under.
        self.app: OAuthApplication = app

        #: The :class:`.ModelObjectFactory` that can be used to create :ref:`stateful objects`
        #: from raw response bodies.
        self.stateful_factory: ModelObjectFactory = ModelObjectFactory(self)

        #: The cached gateway response created when the bot opened.
        self.cached_gateway_info: GatewayResponse = gw

        self.__token = token

    @property
    def object_cache(self) -> ObjectCache:
        """
        The :class:`.ObjectCache` that this bot owns.
        """

        return self.stateful_factory.object_cache

    @asynccontextmanager
    async def start_receiving_events(
        self,
    ) -> AsyncGenerator[GatewayCollection, None]:
        """
        Starts receiving inbound events from the gateway on all available shards.
        """

        async with anyio.create_task_group() as nursery:
            wrapper = GatewayCollection(
                nursery,
                self.__token,
                self.cached_gateway_info.url,
                self.cached_gateway_info.shards,
            )

            for shard in range(0, self.cached_gateway_info.shards):
                wrapper._start_shard(shard)

            yield wrapper


@asynccontextmanager
async def open_bot(
    token: str,
) -> AsyncGenerator[ChiruBot, None]:
    """
    Opens a new :class:`.ChiruBot` instance. This is an async context manager function.

    :param token: The token to connect to Discord with.
    """

    async with (
        httpx.AsyncClient() as httpx_client,
        anyio.create_task_group() as http_nursery,
    ):
        http = ChiruHttpClient(httpx_client=httpx_client, nursery=http_nursery, token=token)
        app = await http.get_current_application_info()
        gateway = await http.get_gateway_info()

        yield ChiruBot(http=http, app=app, token=token, gw=gateway)
