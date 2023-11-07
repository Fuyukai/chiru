import abc

import attr

from chiru.models.message import Message


class DispatchedEvent(abc.ABC):
    """
    Marker interface for dispatched events.
    """


class Connected(DispatchedEvent):
    """
    Published when a single shard has successfully connected to the gateway.
    """


@attr.s(frozen=True, slots=True, kw_only=True)
class MessageCreate(DispatchedEvent):
    """
    Published when a message is created a channel.
    """

    #: The message that was actually created.
    message: Message = attr.ib()
