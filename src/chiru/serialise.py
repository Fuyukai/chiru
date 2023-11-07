import arrow
from cattrs import Converter
from cattrs.preconf.json import configure_converter
from chiru.models.member import RawMember

from chiru.models.message import RawMessage
from chiru.models.oauth import OAuthApplication
from chiru.models.user import RawUser


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

    RawUser.configure_converter(converter)
    RawMessage.configure_converter(converter)
    RawMember.configure_converter(converter=converter)
    OAuthApplication.configure_converter(converter)

    return converter


CONVERTER = create_chiru_converter()
