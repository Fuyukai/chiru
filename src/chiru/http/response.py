import attr


@attr.s(frozen=True, kw_only=True, slots=True)
class GatewaySessionLimits:
    #: The number of session starts that the current bot is allowed within the limit.
    total: int = attr.ib()

    #: The remaining number of session starts that the current bot is allowed within the limit.
    remaining: int = attr.ib()

    #: The number of milliseconds until the identification limit resets.
    reset_after: int = attr.ib()

    #: The maximum number of IDENTIFY requests within 5 seconds.
    max_concurrency: int = attr.ib()


@attr.s(frozen=True, kw_only=True, slots=True)
class GatewayResponse:
    """
    The response for a gateway HTTP request.
    """

    #: The WebSocket URL of the gateway.
    url: str = attr.ib()

    #: The number of shards to connect with.
    shards: int = attr.ib(default=1)

    #: The session start limit information for the current user.
    session_start_limit: GatewaySessionLimits = attr.ib()
