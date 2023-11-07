from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chiru.models.user import User


class ObjectCache:
    """
    Caches certain Discord objects to avoid needing to constantly re-create them.
    """
