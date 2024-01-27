from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import SupportsInt, TypeVar

from anyio.abc import TaskGroup

ItemT = TypeVar("ItemT")


@asynccontextmanager
async def cancel_on_close(group: TaskGroup) -> AsyncGenerator[TaskGroup, None]:
    """
    Context manager that cancels the provided class group on exit.
    """

    async with group:
        try:
            yield group
        finally:
            group.cancel_scope.cancel()


def maybe_int(what: SupportsInt | None) -> int | None:
    """
    Converts any ``int``-able type into an int, or short circuits into a None.
    """

    if what is None:
        return None

    return int(what)
