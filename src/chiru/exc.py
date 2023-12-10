
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import attr


class DiscordError(Exception):
    """
    Base type for all Discord-related errors.
    """


@attr.s(slots=True, str=True)
class HttpApiError(DiscordError):
    """
    Base class for all HTTP API related errors.
    """

    #: The HTTP status code for this response.
    status_code: int = attr.ib()


# TODO: Parse the sub-errors out into an ExceptionGroup?

@attr.s(slots=True, str=True)
class HttpApiRequestError(HttpApiError):
    """
    Base class for all errors caused by a bad request (i.e. )
    """

    @classmethod
    def from_response(
        cls, 
        status_code: int,
        body: Mapping[str, Any]
    ) -> HttpApiError:
        """
        Creates a new :class:`.HttpApiError` or appropriate subclass from the provided response.
        """

        code: int = body["code"]
        message: str = body["message"]
        errors: list[Any] = body.get("errors", [])

        # TODO: Actually make subclasses.
        return HttpApiRequestError(
            status_code=status_code, error_code=code, error_message=message, errors=errors
        )
    
    #: The actual error code for this HTTP response.
    error_code: int = attr.ib()

    #: The human-readable error code for this HTTP response.
    error_message: str = attr.ib()

    #: The list of specific body-related errors within this HTTP response.
    errors: list[Any] = attr.ib(factory=list, repr=False)
