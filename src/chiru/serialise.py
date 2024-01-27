from typing import Any

import arrow
from bitarray.util import int2ba
from cattrs import Converter
from cattrs.preconf.json import configure_converter

from chiru.models.channel import RawChannel
from chiru.models.embed import Embed
from chiru.models.emoji import RawCustomEmoji
from chiru.models.guild import RawGuild
from chiru.models.member import RawMember
from chiru.models.message import RawMessage
from chiru.models.oauth import OAuthApplication
from chiru.models.permissions import ReadOnlyPermissions, WriteablePermissions
from chiru.models.presence import Presence
from chiru.models.role import Role
from chiru.models.user import RawUser


def _unstructure_arrow(it: arrow.Arrow) -> str:
    return str(it.isoformat())


def _unstructure_perms(it: ReadOnlyPermissions) -> str:
    return str(it)


def _structure_perms(it: str, type: Any) -> ReadOnlyPermissions | WriteablePermissions:
    perms = int(it)
    ba = int2ba(perms)

    if type == ReadOnlyPermissions:
        return ReadOnlyPermissions(bitfield=ba)
    if type == WriteablePermissions:
        return WriteablePermissions(bitfield=ba)

    raise ValueError(f"unknown type {type}")


def create_chiru_converter() -> Converter:
    """
    Creates a ``cattrs`` converter for deserialising Discord objects.
    """

    converter = Converter(
        omit_if_default=True,
        forbid_extra_keys=True,
        prefer_attrib_converters=True,
    )
    configure_converter(converter)
    converter.register_structure_hook(arrow.Arrow, lambda it, typ: arrow.get(it))
    converter.register_unstructure_hook(arrow.Arrow, _unstructure_arrow)

    for klass in (ReadOnlyPermissions, WriteablePermissions):
        converter.register_structure_hook(klass, _structure_perms)
        converter.register_unstructure_hook(klass, _unstructure_perms)

    Embed.configure_converter(converter)
    RawUser.configure_converter(converter)
    RawMessage.configure_converter(converter)
    RawMember.configure_converter(converter)
    RawChannel.configure_converter(converter)
    RawGuild.configure_converter(converter)
    RawCustomEmoji.configure_converter(converter)
    OAuthApplication.configure_converter(converter)
    Presence.configure_converter(converter)
    Role.configure_converter(converter)

    return converter


CONVERTER = create_chiru_converter()
