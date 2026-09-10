"""Repository interfaces for the shopping capability.

These are `Protocol`s so the service layer depends on behaviour rather than on
SQLAlchemy, and so a fake can satisfy them without inheriting anything.
"""

from collections.abc import Iterable
from datetime import date
from typing import Protocol
from uuid import UUID

from app.modules.shopping.domain.item import ItemOrigin, ShoppingItem
from app.modules.shopping.domain.purchase import Purchase
from app.modules.shopping.domain.store import Store
from app.modules.shopping.domain.units import Unit


class StoreRepository(Protocol):
    """Persistence for the household's store registry."""

    def list_all(self) -> list[Store]:
        """Return every store, ordered by name.

        Returns:
            The stores in the registry.
        """
        ...

    def get(self, store_id: UUID) -> Store | None:
        """Return one store.

        Args:
            store_id: The store to look up.

        Returns:
            The store, or None when no store has that id.
        """
        ...

    def find_by_name(self, name: str) -> Store | None:
        """Return the store with this name, compared case-insensitively.

        Args:
            name: The name to look for.

        Returns:
            The matching store, or None.
        """
        ...

    def unknown_ids(self, store_ids: Iterable[UUID]) -> frozenset[UUID]:
        """Return which of the given ids are not in the registry.

        Args:
            store_ids: The ids to check.

        Returns:
            The subset that matches no store; empty when all exist.
        """
        ...

    def add(self, name: str) -> Store:
        """Add a store to the registry.

        Args:
            name: The store's name.

        Returns:
            The created store.
        """
        ...

    def delete(self, store_id: UUID) -> None:
        """Remove a store from the registry.

        Args:
            store_id: The store to remove.
        """
        ...


class ShoppingItemRepository(Protocol):
    """Persistence for the shared shopping list."""

    def get(self, item_id: UUID) -> ShoppingItem | None:
        """Return one item with its stores and purchase.

        Args:
            item_id: The item to look up.

        Returns:
            The item, or None when no item has that id.
        """
        ...

    def list_outstanding(
        self,
        *,
        store_id: UUID | None = None,
        today: date,
        include_upcoming: bool = False,
    ) -> list[ShoppingItem]:
        """Return the outstanding items, optionally filtered to one store.

        Args:
            store_id: Restrict to items buyable at this store. Items carrying
                no store match every store. None returns every store's items.
            today: The household's current calendar date.
            include_upcoming: Include items whose availability date has not
                yet arrived. False gives a store's shopping view; True gives
                the full list for planning at home.

        Returns:
            The matching items, ordered by name.
        """
        ...

    def add(
        self,
        *,
        name: str,
        quantity: float,
        unit: Unit,
        store_ids: Iterable[UUID],
        available_from: date | None,
        origin: ItemOrigin,
    ) -> ShoppingItem:
        """Add an item to the list.

        Args:
            name: The item's name.
            quantity: How much is needed; greater than zero.
            unit: The unit the quantity is expressed in.
            store_ids: Stores the item may be bought at; empty means anywhere.
            available_from: The date the item becomes worth buying, or None.
            origin: How the item came to be on the list.

        Returns:
            The created item.
        """
        ...

    def update(
        self,
        item_id: UUID,
        *,
        name: str | None = None,
        quantity: float | None = None,
        unit: Unit | None = None,
        store_ids: Iterable[UUID] | None = None,
        available_from: date | None = None,
        clear_available_from: bool = False,
    ) -> ShoppingItem:
        """Change an item's fields, leaving unsupplied ones untouched.

        Args:
            item_id: The item to change.
            name: A new name, or None to leave it.
            quantity: A new quantity, or None to leave it.
            unit: A new unit, or None to leave it.
            store_ids: The item's new complete set of stores, or None to leave
                them. An empty iterable clears them, making the item
                buyable anywhere.
            available_from: A new availability date, or None to leave it.
            clear_available_from: Remove the availability date, making the
                item always available. Takes precedence over available_from.

        Returns:
            The updated item.
        """
        ...

    def delete(self, item_id: UUID) -> None:
        """Take an item off the list without recording a purchase.

        Args:
            item_id: The item to remove.
        """
        ...

    def record_purchase(self, item_id: UUID, member_id: UUID) -> Purchase:
        """Record that a member bought an item.

        Marking an already-bought item returns the existing purchase rather
        than creating a second one, so that both members marking the same
        item at once is harmless.

        Args:
            item_id: The item that was bought.
            member_id: The member who bought it.

        Returns:
            The purchase recorded against the item.
        """
        ...

    def remove_purchase(self, item_id: UUID) -> None:
        """Undo a purchase, returning the item to the outstanding list.

        Args:
            item_id: The item whose purchase should be removed.
        """
        ...

    def detach_store_from_bought_items(self, store_id: UUID) -> None:
        """Drop a store's links to items that have already been bought.

        A store link records that an item *may* be bought at a store, not that
        it *was*, so removing it loses no purchase history. This is what lets
        a store the household no longer uses be deleted once its outstanding
        items are gone, while the foreign key still refuses to drop a store
        an outstanding item depends on.

        Args:
            store_id: The store being deleted.
        """
        ...

    def outstanding_names_referencing(self, store_id: UUID) -> tuple[str, ...]:
        """Return the names of outstanding items assigned to a store.

        Used to refuse deleting a store that is still in use, and to say which
        items stand in the way.

        Args:
            store_id: The store being deleted.

        Returns:
            The referencing items' names, ordered, empty when none.
        """
        ...
