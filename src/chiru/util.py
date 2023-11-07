from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncContextManager, Type, TypeVar

import anyio
from anyio import CancelScope, CapacityLimiter
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

ItemT = TypeVar("ItemT")


def open_channel_pair(
    buffer_size: float = 0, *, item_type: Type[ItemT]
) -> tuple[MemoryObjectReceiveStream[ItemT], MemoryObjectSendStream[ItemT]]:
    """
    Helper function because anyio's ``create_memory_object_stream`` is kinda hacky and PyCharm
    doesn't like it.
    """

    tup = anyio.create_memory_object_stream(buffer_size)
    return tup[1], tup[0]


class CapacityLimitedNursery:
    """
    A nursery that only allows a certain amount of tasks to be ran at any one time.
    """

    def __init__(self, real_nursery: TaskGroup, limiter: CapacityLimiter):
        self._nursery = real_nursery
        self._limiter = limiter

    async def start(self, fn):
        """
        Starts a new task. This will block until the capacity limiter has a token available.
        """

        async def inner(task_status):
            async with self._limiter:
                task_status.started()
                await fn()

        await self._nursery.start(inner)

    @property
    def available_tasks(self):
        return self._limiter.available_tokens

    @property
    def cancel_scope(self) -> CancelScope:
        return self._nursery.cancel_scope


def open_limiting_nursery(max_tasks: int = 16) -> AsyncContextManager[CapacityLimitedNursery]:
    """
    Opens a capacity limiting nursery.

    :param max_tasks: The maximum number of tasks that can run simultaneously.
    """

    @asynccontextmanager
    async def _do():
        async with anyio.create_task_group() as n:
            yield CapacityLimitedNursery(n, CapacityLimiter(max_tasks))

    return _do()
