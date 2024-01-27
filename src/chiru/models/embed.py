from __future__ import annotations

import attr
import cattr
from arrow import Arrow
from cattr import Converter, override

# a fundamentally ugly API.


@attr.s(slots=True, kw_only=True)
class EmbedFooter:
    """
    The footer for an embed. This displays directly at the bottom.
    """

    #: The text within this footer.
    text: str = attr.ib()

    #: The icon URL for this footer.
    icon_url: str | None = attr.ib(default=None)

    #: The proxied icon URL through Discord's CDN. Read-only.
    proxy_icon_url: str | None = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class EmbedImageOrVideo:
    """
    Common class for both image and video content.
    """

    #: The proxy URL for this image or video, if any. Read-only.
    proxy_url: str | None = attr.ib(default=None)

    #: The height for this image or video, if any.
    height: int | None = attr.ib(default=None)

    #: The width for this image or video, if any.
    width: int | None = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class EmbedImage(EmbedImageOrVideo):
    """
    A single image in an embed. This is shared between both the image and the thumbnail.
    """

    #: The image URL for this image.
    url: str = attr.ib()


@attr.s(slots=True, kw_only=True)
class EmbedVideo(EmbedImageOrVideo):
    """
    A single clickthrough video for this embed.
    """

    #: The video URL for this video, if any.
    url: str | None = attr.ib()


@attr.s(slots=True, kw_only=True)
class EmbedProvider:
    """
    It's a mystery.
    """

    #: The name for this provider, if any.
    name: str | None = attr.ib()

    #: The URL for this provider, if any.
    url: str | None = attr.ib()


@attr.s(slots=True, kw_only=True)
class EmbedAuthor:
    """
    The author for this embed, shown at the top of the embed.
    """

    #: The name of the author.
    name: str = attr.ib()

    #: The URL of the author.
    url: str | None = attr.ib(default=None)

    #: The icon URL for the author, if any.
    icon_url: str | None = attr.ib(default=None)

    #: The proxied icon URL. Read-only.
    proxy_icon_url: str | None = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class EmbedField:
    """
    A single key-value field for this embed, shown as a list below the image.
    """

    #: The name of this field.
    name: str = attr.ib()

    #: The value for this field.
    value: str = attr.ib()

    #: If this field displays inline or not.
    inline: bool = attr.ib(default=True)


@attr.s(slots=True, kw_only=True)
class Embed:
    """
    A rich content embed in a message.
    """

    @classmethod
    def configure_converter(cls, converter: Converter) -> None:  # noqa: D102
        converter.register_structure_hook(
            cls,
            cattr.gen.make_dict_structure_fn(
                cls, converter, colour=override(rename="color"), _cattrs_forbid_extra_keys=False
            ),
        )

        converter.register_unstructure_hook(
            cls,
            cattr.gen.make_dict_unstructure_fn(
                cls, converter, _cattrs_omit_if_default=True, colour=override(rename="color")
            ),
        )

        for klass in (
            EmbedAuthor,
            EmbedFooter,
            EmbedImage,
            EmbedProvider,
            EmbedVideo,
        ):
            converter.register_unstructure_hook(
                klass,
                cattr.gen.make_dict_unstructure_fn(
                    klass,
                    converter,
                    _cattrs_omit_if_default=True,
                ),
            )

    #: The title for this embed, if any.
    title: str | None = attr.ib(default=None)

    #: The description for this embed, if any.
    description: str | None = attr.ib(default=None)

    #: The unparsed, textual url for this embed, if any.
    url: str = attr.ib(default=None)

    #: The timestamp for this embed, if any.
    timestamp: Arrow | None = attr.ib(default=None)

    #: The colour for this embed, if any.
    colour: int | None = attr.ib(default=None)

    #: The footer for this embed, if any.
    footer: EmbedFooter | None = attr.ib(default=None)

    #: The image for this embed, if any.
    image: EmbedImage | None = attr.ib(default=None)

    #: The thumbnail for this embed, if any.
    thumbnail: EmbedImage | None = attr.ib(default=None)

    #: The video for this embed, if any.
    video: EmbedVideo | None = attr.ib(default=None)

    #: The provider for this embed, if any.
    provider: EmbedProvider | None = attr.ib(default=None)

    #: The author for this embed, if any.
    author: EmbedAuthor | None = attr.ib(default=None)

    #: The fields for this embed.
    fields: list[EmbedField] = attr.ib(factory=list)
