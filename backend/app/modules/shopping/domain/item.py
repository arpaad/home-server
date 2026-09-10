"""An item on the household's shared shopping list."""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal
from uuid import UUID

from app.modules.shopping.domain.purchase import Purchase
from app.modules.shopping.domain.store import Store
from app.modules.shopping.domain.units import DEFAULT_QUANTITY, DEFAULT_UNIT, Unit
from app.modules.shopping.errors import EmptyItemNameError, NonPositiveQuantityError

ItemOrigin = Literal["manual", "recipe"]
"""How an item came to be on the list. Only "manual" occurs in this release."""


@dataclass(frozen=True, slots=True)
class ShoppingItem:
    """One item on the single shared list.

    The three rules that decide whether an item belongs in a store's shopping
    view live here as well as in SQL: the repository evaluates them in the
    database for correctness under paging, and these methods state the same
    rules in a form that can be unit tested without one.
    """

    id: UUID
    name: str
    quantity: float = DEFAULT_QUANTITY
    unit: Unit = DEFAULT_UNIT
    stores: tuple[Store, ...] = ()
    available_from: date | None = None
    origin: ItemOrigin = "manual"
    purchase: Purchase | None = field(default=None)

    def __post_init__(self) -> None:
        """Enforce the item invariants.

        Raises:
            EmptyItemNameError: If the name is empty or only whitespace.
            NonPositiveQuantityError: If the quantity is not greater than zero.
        """
        if not self.name.strip():
            raise EmptyItemNameError
        if self.quantity <= 0:
            raise NonPositiveQuantityError(self.quantity)

    @property
    def is_outstanding(self) -> bool:
        """Whether the item is still to be bought.

        Returns:
            True when no purchase has been recorded against the item.
        """
        return self.purchase is None

    def is_available_on(self, today: date) -> bool:
        """Whether the item is worth buying on the given household date.

        Args:
            today: The household's current calendar date.

        Returns:
            True when the item has no availability date, or that date has
            arrived.
        """
        return self.available_from is None or self.available_from <= today

    def belongs_to_store(self, store_id: UUID) -> bool:
        """Whether the item may be bought at the given store.

        An item carrying no store means "anywhere" and therefore belongs to
        every store. This is the rule that removes the need to write the same
        item on two stores' lists.

        Args:
            store_id: The store being shopped in.

        Returns:
            True when the item is unrestricted, or is assigned to this store.
        """
        if not self.stores:
            return True
        return any(store.id == store_id for store in self.stores)

    def is_in_shopping_view_of(self, store_id: UUID, today: date) -> bool:
        """Whether the item appears in a store's shopping view.

        Args:
            store_id: The store being shopped in.
            today: The household's current calendar date.

        Returns:
            True when the item is outstanding, available, and belongs to the
            store.
        """
        return (
            self.is_outstanding and self.is_available_on(today) and self.belongs_to_store(store_id)
        )
