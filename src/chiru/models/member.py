
from arrow import Arrow
import attr
from cattr import Converter, override
import cattr
from chiru.models.base import DiscordObject, StatefulMixin
from chiru.models.user import RawUser, User


@attr.s(kw_only=True)
class RawMember:
    """
    A single member in a guild.
    """

    @classmethod
    def configure_converter(cls, converter: Converter):
        for klass in (cls, Member):
            converter.register_structure_hook(
                klass, 
                func=cattr.gen.make_dict_structure_fn(
                    klass, converter, 
                    role_ids=override(rename="roles"),
                    _cattrs_forbid_extra_keys=False,
                )
            )

    # may be None e.g. on message objects
    #: The raw user object for this member.
    user: RawUser | None = attr.ib(default=None)

    #: The nickname for this member.
    nick: str | None = attr.ib(default=None)

    #: The avatar hash for this member, if unspecified in the RawUser field.
    avatar: str | None = attr.ib(default=None)

    #: The list of role IDs that this member has.
    role_ids: list[int] = attr.ib(factory=list)

    #: When this member joined the guild.
    joined_at: Arrow = attr.ib()


@attr.s(slots=True, kw_only=True)
class Member(RawMember, StatefulMixin):
    """
    Stateful version of :class:`.RawMember`.
    """

    user: User | None = attr.ib(default=None)
