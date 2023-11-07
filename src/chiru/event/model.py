import abc

import attr

from chiru.models.guild import Guild
from chiru.models.message import Message


class DispatchedEvent(abc.ABC):
    """
    Marker interface for dispatched events.
    """


class Connected(DispatchedEvent):
    """
    Published when a single shard has successfully connected to the gateway.
    """


@attr.s(slots=True, frozen=True)
class GuildStreamed(DispatchedEvent):
    """
    Published when a guild has been streamed during gateway startup.
    """

    #: The guild that has just been streamed.
    guild: Guild = attr.ib()


@attr.s(slots=True, frozen=True)
class GuildJoined(DispatchedEvent):
    """
    Published when a bot joins a guild during non-startup operation.
    """

    #: The guild that has just been joined.
    guild: Guild = attr.ib()


@attr.s(slots=True, frozen=True)
class GuildAvailable(DispatchedEvent):
    """
    Published when a guild becomes available e.g. after an outage and not during startup.
    """

    #: The guild that has just become available.
    guild: Guild = attr.ib()


@attr.s(frozen=True, slots=True, kw_only=True)
class MessageCreate(DispatchedEvent):
    """
    Published when a message is created a channel.
    """

    #: The message that was actually created.
    message: Message = attr.ib()
