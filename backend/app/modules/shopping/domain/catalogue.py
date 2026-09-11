"""An entry in the household's catalogue of what it buys."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.shopping.domain.category import Category
from app.modules.shopping.domain.store import Store
from app.modules.shopping.errors import EmptyEntryNameError


def ensure_valid_entry_name(name: str) -> str:
    """Return the name stripped, refusing one that carries no content.

    Args:
        name: The proposed entry name.

    Returns:
        The name with surrounding whitespace removed.

    Raises:
        EmptyEntryNameError: If the name is empty or only whitespace.
    """
    stripped = name.strip()
    if not stripped:
        raise EmptyEntryNameError
    return stripped


@dataclass(frozen=True, slots=True)
class CatalogueEntry:
    """One thing the household buys, remembered across weeks.

    The entry owns the category: items derive theirs from it, so correcting
    a category here regroups every item referring to this entry, including
    ones already on the list. The stores are a prefill — adding an item
    copies them, after which the item's stores are its own.
    """

    id: UUID
    name: str
    category: Category | None = None
    stores: tuple[Store, ...] = ()
    last_used_at: datetime | None = None

    def __post_init__(self) -> None:
        """Enforce the entry invariants."""
        ensure_valid_entry_name(self.name)
