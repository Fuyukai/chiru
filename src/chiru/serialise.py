from cattrs import Converter
from cattrs.preconf.json import configure_converter

from chiru.models.oauth import OAuthApplication
from chiru.models.user import RawUser


def create_cattrs_converter() -> Converter:
    """
    Creates a ``cattrs`` converter for deserialising Discord objects.
    """

    converter = Converter(
        omit_if_default=True,
        forbid_extra_keys=True,
        prefer_attrib_converters=True,
    )
    configure_converter(converter)

    RawUser.configure_converter(converter)
    OAuthApplication.configure_converter(converter)

    return converter


CONVERTER = Converter()
