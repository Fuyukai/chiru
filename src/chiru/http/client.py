from __future__ import annotations

import logging
from collections.abc import Mapping
from importlib.metadata import version
from math import ceil
from typing import Any, overload

import anyio
import httpx
from anyio.abc import TaskGroup
from httpx import AsyncClient, Response

from chiru.http.ratelimit import RatelimitManager
from chiru.http.response import GatewayResponse
from chiru.models.factory import StatefulObjectFactory
from chiru.models.message import Message, RawMessage
from chiru.models.oauth import OAuthApplication
from chiru.serialise import CONVERTER

# Small design notes.
#
# The "new" (I don't know how new it is) ratelimit bucket system is fucking stupid. I'm ignoring
# it, and using the old curious-style ratelimit system. (I don't think Joku ever had a 429 with
# curious...)


logger = logging.getLogger(__name__)


class Endpoints:
    """
    Contains all of the endpoints used by the HTTP client.
    """

    API_BASE = "/api/v10"

    GET_GATEWAY = API_BASE + "/gateway/bot"
    OAUTH2_ME = API_BASE + "/applications/@me"

    CHANNEL = API_BASE + "/channels/{channel_id}"
    CHANNEL_MESSAGES = CHANNEL + "/messages"

    def __init__(self, base_url: str = "https://discord.com"):
        self.base_url = base_url


class ChiruHttpClient:
    """
    Wrapper around the various Discord HTTP actions.
    """

    def __init__(
        self,
        *,
        nursery: TaskGroup,
        httpx_client: AsyncClient,
        token: str,
        endpoints: Endpoints | None = None,
    ):
        """
        :param nursery: The task group to spawn
        :param httpx_client: The ``httpx`` ``AsyncClient`` to send the actual network resources on.
                             This object's lifecycle should be managed separately from the
                             HttpClient.
        :param token: The Bot user token to use.
        :param endpoints: The namespace of API endpoints to use for routes.
        """

        self.endpoints = endpoints or Endpoints()
        self._http = httpx_client

        package_version = version("chiru")
        self._http.headers.update(
            {
                "Authorization": f"Bot {token}",
                "User-Agent": f"DiscordBot (https://github.com/TBD/TBD, {package_version})",
            }
        )
        self._http.base_url = self.endpoints.base_url
        # fuck you! we manage our own timeouts
        self._http.timeout = None

        # rate limit helper
        self._ratelimiter = RatelimitManager(nursery)
        # immediately acquired during request processing, and held post-request processing
        self._global_expiration: float = 0.0

    async def _wait_for_global_ratelimit(self):
        if self._global_expiration > anyio.current_time():
            await anyio.sleep_until(self._global_expiration)

    async def request(
        self,
        *,
        bucket: str,
        method: str,
        path: str,
        form_data: Mapping[str, str] | None = None,
        body_json: Mapping[str, Any] | None = None,
        reason: str | None = None,
    ) -> Response:
        """
        Performs a request to the specified endpoint path. This will automatically deal with
        rate limits.

        :param bucket: The rate-limiting bucket to use. Arbitrary hashable object.
        :param method: The HTTP method for the request.
        :param path: The path to use (not the URL!)

        Optional parameters:

        :param reason: The audit log reason for an action, if any.
        :param form_data: The body data that will be encoded as HTTP form data, if any.
        :param body_json: The body data that will be encoded as JSON, if any.
        """

        # this just checkpoints if the global ratelimit time is in the past.
        await self._wait_for_global_ratelimit()

        for tries in range(0, 5):
            rl = self._ratelimiter.get_ratelimit_for_bucket((method, bucket))
            async with rl.acquire_ratelimit_token():
                logger.debug(f"{method} {path} => (pending) (try {tries + 1})")

                try:
                    req = self._http.build_request(
                        method=method, url=path, data=form_data, json=body_json
                    )

                    if reason is not None:
                        req.headers["X-Audit-Log-Reason"] = reason

                    response = await self._http.send(req)
                except OSError as e:
                    logger.debug(f"{method} {path} => (failed) (try {tries + 1})", exc_info=e)
                    continue
                except httpx.RequestError as e:
                    logger.debug(f"{method} {path} => (failed) (try {tries + 1})", exc_info=e)
                    continue

                logger.debug(f"{method} {path} => {response.status_code} (try {tries + 1})")

                # Back in 2016, Discord would return 502s constantly on random requests.
                # I don't know if this is still the case in 2023, but I see no reason not to keep
                # it. Just backoff and retry.
                # Actually, I just got a 500 so I'm going to keep the handling in anyway.
                if 500 <= response.status_code <= 504:
                    sleep_time = 2 ** (tries + 1)
                    logger.warning(
                        f"Server-side error when requesting {path}, waiting for {sleep_time}s"
                    )
                    await anyio.sleep(sleep_time)
                    continue

                is_global = response.headers.get("X-RateLimit-Global", "").lower() == "true"

                if response.status_code == 429:
                    # Uh oh spaghetti-os!
                    # Is this no longer ms? Fuck you
                    sleep_time = ceil(int(response.headers["Retry-After"]))
                    if is_global:
                        self._global_expiration = anyio.current_time() + sleep_time

                    await anyio.sleep(sleep_time)
                    continue

                limit = int(response.headers.get("X-RateLimit-Limit", 1))
                # this is in seconds in 2023. it was in ms in 2016. lol!
                reset = float(response.headers.get("X-Ratelimit-Reset-After", 1))
                rl.apply_ratelimit_statistics(reset, limit)

                response.raise_for_status()
                return response

        else:
            raise RuntimeError("Failed to get a valid response after five tries.")

    async def get_gateway_info(self) -> GatewayResponse:
        """
        Gets the gateway info that the current bot should connect.
        """

        resp = await self.request(bucket="gateway", method="GET", path=Endpoints.GET_GATEWAY)

        return CONVERTER.structure(resp.json(), GatewayResponse)

    async def get_current_application_info(self) -> OAuthApplication:
        """
        Gets the application info about the current bot's application.
        """

        resp = await self.request(bucket="oauth2:me", method="GET", path=Endpoints.OAUTH2_ME)

        return CONVERTER.structure(resp.json(), OAuthApplication)

    # TODO: Figure out some good way of representing allowed_mentions.
    # TODO: Embeds.
    # TODO: Interactions.
    @overload
    async def send_message(self, *, channel_id: int, content: str | None) -> RawMessage: ...

    @overload
    async def send_message(
        self,
        *,
        channel_id: int,
        content: str | None,
        factory: StatefulObjectFactory | None = None,
    ) -> Message: ...

    async def send_message(
        self,
        *,
        channel_id: int,
        content: str | None = None,
        factory: StatefulObjectFactory | None = None,
    ) -> RawMessage:
        """
        Sends a single message to a channel.

        :param channel_id: The ID of the channel to send the message to.
        :param content: The textual content to send.
        """

        resp = await self.request(
            bucket=f"send-message:{channel_id}",
            method="POST",
            path=Endpoints.CHANNEL_MESSAGES.format(channel_id=channel_id),
            body_json={"content": content},
        )

        if factory:
            return factory.make_message(resp.json())

        return CONVERTER.structure(resp.json(), RawMessage)
