from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

import attr
from typing_extensions import override

if TYPE_CHECKING:  # Make sphinx happy!
    from chiru.models.base import DiscordObject


# hack for lack of easy "singleton" sentinel typing.
class Parse:
    """
    Marker type for telling Discord to parse out mentions from the message body.
    """


_PARSE = Parse()


class AllowedMentions(Protocol):
    """
    An empty protocol returned from :func:`.make_allowed_mentions` to hide the implementation
    details.
    """

    def to_dict(self) -> dict[str, Any]:
        """
        Turns this set of allowed mentions into the dict format that Discord expects in the
        HTTP API.
        """

        ...


@attr.s(slots=True)
class _AllowedMentions(AllowedMentions):
    parse: list[str] = attr.ib(factory=list)
    users: list[int] = attr.ib(factory=list)
    roles: list[int] = attr.ib(factory=list)

    @override
    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {}

        # extra condition so that this correctly suppresses *all* mentions
        if self.parse or not (self.users and self.roles):
            body["parse"] = self.parse

        if self.users:
            body["users"] = self.users

        if self.roles:
            body["roles"] = self.roles

        return body


def make_allowed_mentions(
    *,
    parse_everyone: bool = False,
    users: type[Parse] | Parse | list[int | DiscordObject] = _PARSE,
    roles: type[Parse] | Parse | list[int | DiscordObject] = _PARSE,
) -> AllowedMentions:
    """
    Creates a new allowed mentions definition from the provided values.

    :param parse_everyone: If True, then ``@everyone`` and ``@here`` will ping all (online) users
        if they are present in the text. Otherwise, they will be silently ignored even if the bot
        has permission to ping everyone.

    :param users: Either the literal type :class:`.Parse` to have Discord parse all user mentions
        from the message body, or a list of either snowflakes or :class:`.DiscordObject`
        that are allowed to be mentioned.

    :param roles: Either the literal type :class:`.Parse` to have Discord parse all user mentions
        from the message body, or a list of either snowflakes or :class:`.DiscordObject`
        that are allowed to be mentioned.

    :return: A :class:`.AllowedMentions` instance. The actual implementation of this object is
        hidden.
    """

    def _unparse(into: list[int], fromto: list[int | DiscordObject]) -> None:
        for what in fromto:
            if isinstance(what, DiscordObject):
                into.append(what.id)
            else:
                into.append(what)

    obb = _AllowedMentions()

    if parse_everyone:
        obb.parse.append("everyone")

    if isinstance(users, Parse) or users == Parse:
        obb.parse.append("users")
    else:
        _unparse(obb.users, users)  # type: ignore

    if isinstance(roles, Parse) or roles == Parse:
        obb.parse.append("roles")
    else:
        _unparse(obb.roles, roles)  # type: ignore

    return obb


#: A singleton instance of :class:`.AllowedMentions` that suppresses all mentions.
SUPPRESS_ALL = make_allowed_mentions(users=[], roles=[])
