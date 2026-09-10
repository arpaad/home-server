"""Business rules for the shared household shopping list.

Every rule that is not a database constraint lives here, so that the API layer
translates HTTP and nothing more, and so a second client cannot reach the data
by a path that skips a rule.
"""

from collections.abc import Iterable
from datetime import date
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.clock import household_today
from app.modules.shopping.domain.item import (
    ItemOrigin,
    ShoppingItem,
    ensure_positive_quantity,
    ensure_valid_name,
)
from app.modules.shopping.domain.purchase import Purchase
from app.modules.shopping.domain.units import DEFAULT_QUANTITY, DEFAULT_UNIT, Unit
from app.modules.shopping.errors import ItemNotFoundError, UnknownStoresError
from app.modules.shopping.repository.interfaces import (
    ShoppingItemRepository,
    StoreRepository,
)


class ShoppingListService:
    """The single shared list: what is on it, and what happens to it."""

    def __init__(
        self,
        items: ShoppingItemRepository,
        stores: StoreRepository,
        timezone: ZoneInfo,
    ) -> None:
        """Bind the service to its repositories and the household's zone.

        Args:
            items: The shopping list.
            stores: The store registry, used to validate assignments.
            timezone: The household's time zone, deciding what "today" means.
        """
        self._items = items
        self._stores = stores
        self._timezone = timezone

    def _today(self) -> date:
        """Return the household's current calendar date.

        Returns:
            Today, as the household reckons it.
        """
        return household_today(self._timezone)

    def _require_known_stores(self, store_ids: Iterable[UUID]) -> list[UUID]:
        """Refuse store ids that are not in the registry.

        Ignoring an unknown store would hide the item from that store's view
        with no error, which is the failure mode this capability removes.

        Args:
            store_ids: The stores being assigned.

        Returns:
            The store ids, de-duplicated, in the order given.

        Raises:
            UnknownStoresError: If any id matches no store.
        """
        wanted = list(dict.fromkeys(store_ids))
        unknown = self._stores.unknown_ids(wanted)
        if unknown:
            raise UnknownStoresError(unknown)
        return wanted

    def _require_item(self, item_id: UUID) -> ShoppingItem:
        """Return an item, refusing when it is not on the list.

        Args:
            item_id: The item to look up.

        Returns:
            The item.

        Raises:
            ItemNotFoundError: If no item has that id.
        """
        item = self._items.get(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        return item

    # ---- reads ----

    def get_item(self, item_id: UUID) -> ShoppingItem:
        """Return one item.

        Args:
            item_id: The item to look up.

        Returns:
            The item.
        """
        return self._require_item(item_id)

    def shopping_view(self, store_id: UUID) -> list[ShoppingItem]:
        """Return what to put in the basket in a given store.

        Args:
            store_id: The store being shopped in.

        Returns:
            The outstanding, currently available items buyable at that store,
            including those assigned to no store at all.
        """
        return self._items.list_outstanding(store_id=store_id, today=self._today())

    def full_list(self, *, include_upcoming: bool = True) -> list[ShoppingItem]:
        """Return every outstanding item, for reviewing the list at home.

        Args:
            include_upcoming: Include items whose availability date has not
                yet arrived.

        Returns:
            The outstanding items across every store.
        """
        return self._items.list_outstanding(today=self._today(), include_upcoming=include_upcoming)

    def list_items(
        self,
        *,
        store_id: UUID | None = None,
        include_upcoming: bool = False,
    ) -> list[ShoppingItem]:
        """Return outstanding items, optionally filtered to one store.

        Args:
            store_id: Restrict to items buyable at this store, or None for
                every store.
            include_upcoming: Include items not yet available.

        Returns:
            The matching items.
        """
        return self._items.list_outstanding(
            store_id=store_id,
            today=self._today(),
            include_upcoming=include_upcoming,
        )

    # ---- writes ----

    def add_item(
        self,
        *,
        name: str,
        quantity: float = DEFAULT_QUANTITY,
        unit: Unit = DEFAULT_UNIT,
        store_ids: Iterable[UUID] = (),
        available_from: date | None = None,
        origin: ItemOrigin = "manual",
    ) -> ShoppingItem:
        """Put an item on the shared list.

        Args:
            name: The item's name.
            quantity: How much is needed; defaults to one.
            unit: The unit of measure; defaults to pieces.
            store_ids: Stores it may be bought at; empty means anywhere.
            available_from: When it becomes worth buying, or None for now.
            origin: How it came to be on the list.

        Returns:
            The created item.
        """
        return self._items.add(
            name=ensure_valid_name(name),
            quantity=ensure_positive_quantity(quantity),
            unit=unit,
            store_ids=self._require_known_stores(store_ids),
            available_from=available_from,
            origin=origin,
        )

    def edit_item(
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
        """Change an item, leaving unsupplied fields untouched.

        Args:
            item_id: The item to change.
            name: A new name, or None to leave it.
            quantity: A new quantity, or None to leave it.
            unit: A new unit, or None to leave it.
            store_ids: The complete new set of stores, or None to leave them.
            available_from: A new availability date, or None to leave it.
            clear_available_from: Remove the availability date entirely.

        Returns:
            The updated item.
        """
        self._require_item(item_id)

        return self._items.update(
            item_id,
            name=ensure_valid_name(name) if name is not None else None,
            quantity=ensure_positive_quantity(quantity) if quantity is not None else None,
            unit=unit,
            store_ids=(self._require_known_stores(store_ids) if store_ids is not None else None),
            available_from=available_from,
            clear_available_from=clear_available_from,
        )

    def remove_item(self, item_id: UUID) -> None:
        """Take an item off the list because nobody wants it any more.

        This is not a purchase: nothing is recorded against the item, so later
        reporting cannot mistake a discarded item for something bought.

        Args:
            item_id: The item to remove.
        """
        self._require_item(item_id)
        self._items.delete(item_id)

    def mark_bought(self, item_id: UUID, member_id: UUID) -> Purchase:
        """Record that a member bought an item.

        Idempotent: marking an already-bought item returns the existing
        purchase, so both members marking the same item at once is harmless.

        Args:
            item_id: The item that was bought.
            member_id: The member who bought it.

        Returns:
            The purchase recorded against the item.
        """
        self._require_item(item_id)
        return self._items.record_purchase(item_id, member_id)

    def undo_purchase(self, item_id: UUID) -> ShoppingItem:
        """Undo a purchase made in error.

        Args:
            item_id: The item to return to the outstanding list.

        Returns:
            The item, outstanding again.
        """
        self._require_item(item_id)
        self._items.remove_purchase(item_id)
        return self._require_item(item_id)
