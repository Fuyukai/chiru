from __future__ import annotations

import enum
from functools import partial
from typing import Literal

import attr
import cattr
from cattr import Converter, override

from chiru.models.emoji import Emoji, structure_emoji_field

# a minimum possible effort object as the primary purpose is literally just tracking statuses
# and status names. i might come back to this in the future but not for now.

type PresenceStatus = Literal["online", "idle", "dnd"]
type SendablePresenceStatus = PresenceStatus | Literal["invisible", "offline"]


class ActivityType(enum.IntEnum):
    """
    Enumeration of the possible types of activities.
    """

    GAME = 0
    STREAMING = 1
    LISTENING = 2
    WATCHING = 3
    CUSTOM = 4
    COMPETING = 5


@attr.s(slots=True, kw_only=True)
class Activity:
    """
    A single activity in a presence.
    """

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

    @classmethod
    def custom(cls, text: str, *, url: str | None = None) -> Activity:
        """
        Shortcut method for creating a new custom activity.
        """

        return Activity(
            name="Custom Status",
            state=text,
            type=ActivityType.CUSTOM,
            url=url,
        )


@attr.s(slots=True, kw_only=True)
class Presence:
    """
    A single set of presence data for a single member in a guild.
    """

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:  # noqa: D102
        converter.register_structure_hook(
            cls,
            cattr.gen.make_dict_structure_fn(
                cls,
                converter,
                _cattrs_forbid_extra_keys=False,
            ),
        )

        emoji_field = partial(structure_emoji_field, converter)
        converter.register_structure_hook(
            Activity,
            cattr.gen.make_dict_structure_fn(
                Activity,
                converter,
                emoji=override(struct_hook=emoji_field),
                _cattrs_forbid_extra_keys=False,
            ),
        )

    #: The current computed status for this member.
    status: PresenceStatus = attr.ib()

    #: A list of activities for this member.
    activities: list[Activity] = attr.ib(factory=list)
