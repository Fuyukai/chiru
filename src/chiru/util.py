from __future__ import annotations

from typing import TypeVar, Type

import anyio
import trio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

ItemT = TypeVar("ItemT")


def open_stream_pair(
    buffer_size: float = 0, *, item_type: Type[ItemT]
) -> tuple[MemoryObjectReceiveStream[ItemT], MemoryObjectSendStream[ItemT]]:
    """
    Helper function because anyio's ``create_memory_object_stream`` is kinda hacky and PyCharm
    doesn't like it.
    """

    tup = anyio.create_memory_object_stream(buffer_size)
    return tup[1], tup[0]
