from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import anyio
from anyio import CancelScope
from anyio.abc import TaskGroup

logger = logging.getLogger(__name__)


class RatelimitManager:
    """
    Handles Ratelimit objects.
    """

    def __init__(self, nursery: TaskGroup):
        self._ratelimits: dict[tuple[str, str], Ratelimit] = {}
        self._nursery = nursery

    def _task_got_too_lonely(self, bucket: tuple[str, str]):
        logger.debug(f"Discarding ratelimit for bucket {bucket} due to timeout")

        rl = self._ratelimits.pop(bucket, None)

        # make sure no tasks
        if rl:
            for scope in rl._scopes:
                scope.cancel()

    def get_ratelimit_for_bucket(self, bucket: tuple[str, str]) -> Ratelimit:
        """
        Gets the :class:`.Ratelimit` instance for the specified bucket.
        """

        rl = self._ratelimits.get(bucket)
        if not rl:
            rl = Ratelimit(bucket, self, self._nursery)
            self._ratelimits[bucket] = rl

        return rl


class Ratelimit:
    """
    Handles ratelimiting for a single bucket.
    """

    def __init__(self, bucket: tuple[str, str], manager: RatelimitManager, nursery: TaskGroup):
        self._scopes: set[CancelScope] = set()
        self._manager = manager
        self._bucket = bucket

        # ratelimit state:
        # the time, in event loop seconds, for the looper task to wake up
        self._wakeup_time: float = 0
        # the total count to reset the semaphore to.
        self._max_count = 1

        # used to make sure we don't fill the semaphore up if a task is still running.
        self._requests_still_processing = 0

        # used to automatically discard the ratelimit after a while.
        self._loop_started = anyio.Event()

        self._semaphore = anyio.Semaphore(initial_value=1)
        nursery.start_soon(self._loop)

    def apply_ratelimit_statistics(self, expiration: float, limit: int):
        """
        Applies ratelimit statistics after a request completes successfully.
        """

        self._max_count = limit
        self._wakeup_time = anyio.current_time() + expiration

    async def _loop(self):
        """
        Loops forever, refilling the semaphore every time the wakeup time expires.
        """

        try:
            while True:
                with anyio.move_on_after(delay=10.0) as scope:
                    await self._loop_started.wait()

                if scope.cancelled_caught:
                    # no one care me :(
                    # die and tell the parent to evict us from the dict
                    return

                # run this repeatedly so that if discord changes their mind about the ratelimit, we
                # don't wake up early.
                while self._wakeup_time >= anyio.current_time():
                    logger.info(f"Ratelimit {self._bucket} will reset at {self._wakeup_time}")
                    await anyio.sleep_until(self._wakeup_time)

                # refill the semaphore to max.
                to_refill = (
                    self._max_count - self._semaphore.value - self._requests_still_processing
                )
                logger.info(f"Resetting {to_refill} tokens for {self._bucket}")
                for _ in range(0, to_refill):
                    self._semaphore.release()

                self._loop_started = anyio.Event()
        finally:
            # oops, we got cancelled or had an exception or whatever.
            # refill it in case anyone's waiting to avoid deadlocks, then tell the parent to
            # section 21 us
            for _ in range(0, self._max_count):
                self._semaphore.release()

            self._manager._task_got_too_lonely(self._bucket)

    @asynccontextmanager
    async def acquire_ratelimit_token(self):
        """
        Gets a new ratelimit token.
        """

        with CancelScope() as scope:
            self._scopes.add(scope)

            # deliberately leak the token, as it needs to be refilled externally by the looper task.
            self._loop_started.set()
            await self._semaphore.acquire()

            try:
                self._requests_still_processing += 1
                yield
            finally:
                self._scopes.remove(scope)
                self._requests_still_processing -= 1
