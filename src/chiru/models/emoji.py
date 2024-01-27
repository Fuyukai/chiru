from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NewType

import attr
import cattr
from cattr import Converter, override

from chiru.models.base import DiscordObject
from chiru.models.user import RawUser

#: An emoji that's simply a regular unicode one.
UnicodeEmoji = NewType("UnicodeEmoji", str)


@attr.s(kw_only=True)
class RawCustomEmoji(DiscordObject):
    """
    A custom emoji with an image.
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

        converter.register_structure_hook(
            RawCustomEmojiWithOwner,
            cattr.gen.make_dict_structure_fn(
                RawCustomEmojiWithOwner, converter, creator=override(rename="user")
            ),
        )

    #: The name for this emoji.
    name: str = attr.ib()

    #: The list of role IDs allowed to use this emoji. An empty list means anyone can.
    roles: list[int] = attr.ib(factory=list)

    # in practice, this is always true.
    #: If this emoji requires colons to be used.
    require_colons: bool = attr.ib(default=True)

    #: If this emoji is managed by an external integration.
    managed: bool = attr.ib(default=False)

    #: If this emoji is animated.
    animated: bool = attr.ib(default=False)

    #: If this emoji is available or not. Emojis may be unavailable in certain situations, such as
    #: if a server that previously had a higher cap no longer does.
    available: bool = attr.ib(default=False)

    @property
    def url(self) -> str:
        """
        Gets the CDN URL for this emoji.
        """

        cdn_url = f"https://cdn.discordapp.com/emojis/{self.id}"
        if not self.animated:
            return f"{cdn_url}.png"

        return f"{cdn_url}.gif"


@attr.s(kw_only=True)
class RawCustomEmojiWithOwner(RawCustomEmoji):
    """
    A :class:`.RawCustomEmoji` but also contains details about the user who created the emoji.

    Creator data for emojis is not always available:

    - Emoji objects provided by the gateway (i.e. in ``GUILD_CREATE`` or ``GUILD_EMOJIS_UPDATE``)
      *never* have creator information provided. This information can be manually reconstructed by
      listening to audit log entries.
    - Emoji objects provided by the HTTP API (i.e. the ``/emojis`` endpoint) may have creator
      information if the current user has the ``MANAGE_EMOJIS`` permissions.
    """

    #: The user who created this emoji.
    creator: RawUser = attr.ib()


#: The union type of possible emojis.
Emoji = UnicodeEmoji | RawCustomEmoji | RawCustomEmojiWithOwner


def structure_emoji_field(converter: Converter, data: Mapping[str, Any], _: Any) -> Emoji:
    """
    Structures an emoji field automatically.
    """

    id = data.get("id", None)
    if id is None:
        # definitely a unicode emoji
        return UnicodeEmoji(data["name"])

    if "user" in data:
        # has ownership info
        return converter.structure(data, RawCustomEmojiWithOwner)

    # just a plain RawCustomEmoji
    return converter.structure(data, RawCustomEmoji)
