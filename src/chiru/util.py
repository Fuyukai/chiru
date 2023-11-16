from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import anyio
from anyio import CancelScope, CapacityLimiter
from anyio.abc import TaskGroup, TaskStatus

ItemT = TypeVar("ItemT")


class CapacityLimitedNursery:
    """
    A nursery that only allows a certain amount of tasks to be ran at any one time.
    """

    def __init__(self, real_nursery: TaskGroup, limiter: CapacityLimiter):
        self._nursery = real_nursery
        self._limiter = limiter

    async def start(self, fn: Callable[..., Any]) -> None:
        """
        Starts a new task. This will block until the capacity limiter has a token available.
        """

        async def _inner(task_status: TaskStatus[None]) -> None:
            async with self._limiter:
                task_status.started()
                await fn()

        await self._nursery.start(_inner)

    @property
    def available_tasks(self) -> float:
        return self._limiter.available_tokens

    @property
    def cancel_scope(self) -> CancelScope:
        return self._nursery.cancel_scope


@asynccontextmanager
async def open_limiting_nursery(
    max_tasks: int = 16
) -> AsyncGenerator[CapacityLimitedNursery, None]:
    """
    Opens a capacity limiting nursery.

    :param max_tasks: The maximum number of tasks that can run simultaneously.
    """

    async with anyio.create_task_group() as n:
        yield CapacityLimitedNursery(n, CapacityLimiter(max_tasks))


@asynccontextmanager
async def cancel_on_close(group: TaskGroup) -> AsyncGenerator[TaskGroup, None]:
    async with group:
        try:
            yield group
        finally:
            group.cancel_scope.cancel()
