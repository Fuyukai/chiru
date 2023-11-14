from __future__ import annotations

import attr
from cattrs import Converter
from cattrs.gen import make_dict_structure_fn

from chiru.models.base import DiscordObject
from chiru.models.user import RawUser


@attr.s(slots=True, kw_only=True)
class OAuthApplication(DiscordObject):
    """
    A single OAuth2 application, with a bot user.
    """

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:
        converter.register_structure_hook(
            cls, make_dict_structure_fn(cls, converter, _cattrs_forbid_extra_keys=False)
        )

    #: The name of this application.
    name: str = attr.ib()

    #: The description of this application.
    description: str | None = attr.ib(default=None)

    #: If True, the bot for this application is public.
    bot_public: bool = attr.ib(default=False)

    #: The bot user for this application.
    bot: RawUser | None = attr.ib(default=None)

    #: The owner user for this application.
    owner: RawUser | None = attr.ib(default=None)
