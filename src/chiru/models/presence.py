import enum
from typing import Literal

import attr
import cattr
from cattr import Converter

from chiru.models.emoji import Emoji

# a minimum possible effort object as the primary purpose is literally just tracking statuses
# and status names. i might come back to this in the future but not for now.

type PresenceStatus = Literal["online", "idle", "dnd"]


class ActivityType(enum.IntEnum):
    GAME = 0
    STREAMING = 1
    LISTENING = 2
    WATCHING = 3
    CUSTOM = 4
    COMPETING = 5


@attr.s(slots=True, kw_only=True)
class Activity:
    #: The name of this activity. This will be the string "Custom Activity" for custom statuses.
    name: str = attr.ib()

    #: The 'party state' for this activity, or custom text for the ``CUSTOM`` activity type.
    state: str | None = attr.ib(default=None)

    #: The type of this activity.
    type: ActivityType = attr.ib()

    #: The URL for this activity.
    url: str | None = attr.ib(default=None)

    #: The emoji for this activity, if any.
    emoji: Emoji | None = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class Presence:
    """
    A single set of presence data for a single member in a guild.
    """

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:
        for klass in (cls, Activity):
            converter.register_structure_hook(
                klass,
                cattr.gen.make_dict_structure_fn(
                    klass,
                    converter,
                    _cattrs_forbid_extra_keys=False,
                ),
            )

    #: The current computed status for this member.
    status: PresenceStatus = attr.ib()

    #: A list of activities for this member.
    activities: list[Activity] = attr.ib(factory=list)
