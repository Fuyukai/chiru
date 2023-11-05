import attr
import cattrs
from cattrs.gen import make_dict_unstructure_fn, make_dict_structure_fn

from chiru.models.base import DiscordObject, StatefulMixin


@attr.s(kw_only=True, hash=False, eq=False)
class RawUser(DiscordObject):
    """
    A single Discord user.
    """

    @classmethod
    def configure_converter(cls, converter: cattrs.Converter):
        converter.register_structure_hook(
            cls, make_dict_structure_fn(cls, converter, _cattrs_forbid_extra_keys=False)
        )
        converter.register_structure_hook(
            User,
            make_dict_structure_fn(User, converter, _cattrs_forbid_extra_keys=False),
        )

    #: The global username for this user. This may or may not be unique.
    username: str = attr.ib()

    #: The discriminator for this user. This is a deprecated field and is only kept for
    #: compatibility with legacy accounts.
    discriminator: str | None = attr.ib(default="0")

    #: The display name for this user. May be None if this user has no extra display name.
    global_name: str | None = attr.ib(default=None)

    #: The avatar hash for this user.
    avatar: str | None = attr.ib(default=None)

    #: If this user is a bot user or not.
    bot: bool = attr.ib(default=False)

    #: If this user is a system user or not.
    system: bool = attr.ib(default=False)

    @property
    def display_name(self) -> str:
        """
        Gets the display name for this user.
        """

        if self.global_name:
            return self.global_name

        return self.username

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, RawUser):
            return NotImplemented

        return other.id == self.id


@attr.s(kw_only=True, hash=False, eq=False)
class User(RawUser, StatefulMixin):
    """
    Stateful version of :class:`.RawUser`.
    """
