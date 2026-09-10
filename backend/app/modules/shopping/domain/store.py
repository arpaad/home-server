"""A store the household shops at."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.shopping.errors import EmptyStoreNameError


@dataclass(frozen=True, slots=True)
class Store:
    """A store in the household's registry.

    Names are unique within the household, compared case-insensitively, so
    that a mistyped name cannot silently become a second store and hide items
    from the store they belong to.
    """

    id: UUID
    name: str

    def __post_init__(self) -> None:
        """Reject a store whose name carries no content.

        Raises:
            EmptyStoreNameError: If the name is empty or only whitespace.
        """
        if not self.name.strip():
            raise EmptyStoreNameError
