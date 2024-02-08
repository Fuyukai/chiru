from typing import Any

from bitarray.util import int2ba
from cattrs import Converter
from cattrs.preconf.json import configure_converter as preconf_json
from whenever import UTCDateTime

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


def unstructure_utc_datetime(it: UTCDateTime) -> str:
    """
    An unstructuring hook for a :class:`.UTCDatetime`.

    This returns the value in RFC 3339 timestamp format.
    """

    return it.rfc3339()


def structure_utc_datetime(it: str, type: Any) -> UTCDateTime:
    """
    A structure hook for a :class:`.UTCDatetime`.

    This will attempt to parse from a Unix timestamp first, and then from an RFC 3339 timestamp
    if that fails.
    """

    try:
        ts = float(it)
    except ValueError:
        return UTCDateTime.from_rfc3339(it)

    return UTCDateTime.from_timestamp(ts)


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


def add_useful_conversions(converter: Converter) -> Converter:
    """
    Adds useful structure and unstructure hooks to a :class:`.Converter`.
    """

    converter.register_structure_hook(UTCDateTime, structure_utc_datetime)
    converter.register_unstructure_hook(UTCDateTime, unstructure_utc_datetime)

    return converter


def create_chiru_converter() -> Converter:
    """
    Creates a ``cattrs`` converter for deserialising Discord objects.
    """

    converter = Converter(
        omit_if_default=True,
        forbid_extra_keys=True,
        prefer_attrib_converters=True,
    )
    preconf_json(converter)
    add_useful_conversions(converter)

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
