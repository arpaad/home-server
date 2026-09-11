"""SQLAlchemy shopping item repository.

The store-and-availability filter is expressed here as one SQL predicate. It
is the correctness core of this capability: stating it once, in the database,
keeps it identical for every caller and correct under paging, rather than
leaving each client to reimplement "no store means every store".
"""

from collections.abc import Iterable
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, Select, and_, delete, exists, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.clock import now_utc
from app.modules.shopping.domain.item import ItemOrigin, ShoppingItem
from app.modules.shopping.domain.purchase import Purchase
from app.modules.shopping.domain.units import Unit
from app.modules.shopping.errors import ItemNotFoundError
from app.modules.shopping.repository.mapping import to_item, to_purchase
from app.modules.shopping.repository.orm import (
    CatalogueEntryORM,
    CategoryORM,
    ShoppingItemORM,
    ShoppingItemPurchaseORM,
    ShoppingItemStoreORM,
)


def _is_outstanding() -> ColumnElement[bool]:
    """Build the predicate matching items with no purchase recorded.

    Returns:
        A SQL predicate true for outstanding items.
    """
    return ~exists().where(ShoppingItemPurchaseORM.item_id == ShoppingItemORM.id)


def _is_available_on(today: date) -> ColumnElement[bool]:
    """Build the predicate matching items worth buying on a given date.

    Args:
        today: The household's current calendar date.

    Returns:
        A SQL predicate true for items with no date, or a date now reached.
    """
    return or_(
        ShoppingItemORM.available_from.is_(None),
        ShoppingItemORM.available_from <= today,
    )


def _belongs_to_store(store_id: UUID) -> ColumnElement[bool]:
    """Build the predicate matching items buyable at a given store.

    An item with no store link means "anywhere" and therefore matches every
    store. This is the rule that removes the need to write one item onto two
    stores' lists, and with it the double-buying it caused.

    Args:
        store_id: The store being shopped in.

    Returns:
        A SQL predicate true for unrestricted items and for items assigned to
        this store.
    """
    has_any_store = exists().where(ShoppingItemStoreORM.item_id == ShoppingItemORM.id)
    assigned_here = exists().where(
        and_(
            ShoppingItemStoreORM.item_id == ShoppingItemORM.id,
            ShoppingItemStoreORM.store_id == store_id,
        )
    )
    return or_(~has_any_store, assigned_here)


class SqlAlchemyShoppingItemRepository:
    """The shared shopping list, backed by the ``shopping_items`` table."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to a session.

        Args:
            session: The session this repository reads and writes through.
        """
        self._session = session

    # ---- reads ----

    def _with_relations(
        self, statement: Select[tuple[ShoppingItemORM]]
    ) -> Select[tuple[ShoppingItemORM]]:
        """Eager-load the relations the domain item needs.

        Args:
            statement: The select to extend.

        Returns:
            The select with stores and purchases eagerly loaded.
        """
        return statement.options(
            selectinload(ShoppingItemORM.stores).selectinload(ShoppingItemStoreORM.store),
            selectinload(ShoppingItemORM.purchases),
            # Joined, not selectin: the category decides row order, so it
            # has to be in the same query the ORDER BY runs in.
            joinedload(ShoppingItemORM.catalogue_entry).joinedload(CatalogueEntryORM.category),
        )

    def get(self, item_id: UUID) -> ShoppingItem | None:
        """Return one item with its stores and purchase.

        Args:
            item_id: The item to look up.

        Returns:
            The item, or None when no item has that id.
        """
        row = (
            self._session
            .scalars(
                self._with_relations(select(ShoppingItemORM).where(ShoppingItemORM.id == item_id))
            )
            .unique()
            .one_or_none()
        )
        return to_item(row) if row else None

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
        statement = select(ShoppingItemORM).where(_is_outstanding())

        if not include_upcoming:
            statement = statement.where(_is_available_on(today))

        if store_id is not None:
            statement = statement.where(_belongs_to_store(store_id))

        # Grouping is presentation and happens in the client; the query only
        # has to hand rows over in group order. Uncategorised items sort last
        # so a freshly typed item lands in the final group, never in the
        # middle of someone else's.
        statement = (
            self
            ._with_relations(statement)
            .outerjoin(ShoppingItemORM.catalogue_entry)
            .outerjoin(CatalogueEntryORM.category)
            .order_by(
                CategoryORM.position.nulls_last(),
                CategoryORM.name.nulls_last(),
                ShoppingItemORM.name,
            )
        )
        return [to_item(row) for row in self._session.scalars(statement).unique().all()]

    def list_bought_uncleared(self, *, store_id: UUID | None = None) -> list[ShoppingItem]:
        """Return bought items the household has not yet cleared away.

        A separate query, not a widening of the outstanding one: that
        predicate is the correctness core and its tests assert exactly which
        items appear. This one reuses the store rule and nothing else.

        Args:
            store_id: Restrict to items buyable at this store, or None for all.

        Returns:
            The bought, uncleared items, most recently bought first.
        """
        statement = (
            select(ShoppingItemORM)
            .join(ShoppingItemPurchaseORM, ShoppingItemPurchaseORM.item_id == ShoppingItemORM.id)
            .where(ShoppingItemORM.cleared_at.is_(None))
        )
        if store_id is not None:
            statement = statement.where(_belongs_to_store(store_id))
        statement = self._with_relations(statement).order_by(
            ShoppingItemPurchaseORM.bought_at.desc(), ShoppingItemORM.name
        )
        return [to_item(row) for row in self._session.scalars(statement).unique().all()]

    def clear_bought(self) -> int:
        """Mark every bought, uncleared item as cleared.

        Returns:
            How many items were cleared.
        """
        bought = select(ShoppingItemPurchaseORM.item_id)
        result = self._session.execute(
            update(ShoppingItemORM)
            .where(ShoppingItemORM.id.in_(bought))
            .where(ShoppingItemORM.cleared_at.is_(None))
            .values(cleared_at=now_utc())
        )
        self._session.flush()
        self._session.expire_all()
        return int(getattr(result, "rowcount", 0))

    def outstanding_names_referencing(self, store_id: UUID) -> tuple[str, ...]:
        """Return the names of outstanding items assigned to a store.

        Args:
            store_id: The store being deleted.

        Returns:
            The referencing items' names, ordered, empty when none.
        """
        names = self._session.scalars(
            select(ShoppingItemORM.name)
            .join(ShoppingItemStoreORM, ShoppingItemStoreORM.item_id == ShoppingItemORM.id)
            .where(ShoppingItemStoreORM.store_id == store_id)
            .where(_is_outstanding())
            .order_by(ShoppingItemORM.name)
        ).all()
        return tuple(names)

    def detach_store_from_bought_items(self, store_id: UUID) -> None:
        """Drop a store's links to items that have already been bought.

        Args:
            store_id: The store being deleted.
        """
        bought_item_ids = select(ShoppingItemPurchaseORM.item_id)
        self._session.execute(
            delete(ShoppingItemStoreORM)
            .where(ShoppingItemStoreORM.store_id == store_id)
            .where(ShoppingItemStoreORM.item_id.in_(bought_item_ids))
        )
        self._session.flush()

    # ---- writes ----

    def _require_row(self, item_id: UUID) -> ShoppingItemORM:
        """Return an item row, refusing when it does not exist.

        Args:
            item_id: The item to load.

        Returns:
            The item row.

        Raises:
            ItemNotFoundError: If no item has that id.
        """
        row = self._session.get(ShoppingItemORM, item_id)
        if row is None:
            raise ItemNotFoundError(item_id)
        return row

    def _reload(self, item_id: UUID) -> ShoppingItem:
        """Return an item freshly loaded with every relation the domain needs.

        Args:
            item_id: The item to load.

        Returns:
            The domain item.

        Raises:
            ItemNotFoundError: If no item has that id.
        """
        self._session.expire_all()
        item = self.get(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        return item

    def _set_stores(self, row: ShoppingItemORM, store_ids: Iterable[UUID]) -> None:
        """Replace an item's store links with exactly the given stores.

        Args:
            row: The item row to update.
            store_ids: The item's new complete set of stores.
        """
        wanted = list(dict.fromkeys(store_ids))
        row.stores = [
            ShoppingItemStoreORM(item_id=row.id, store_id=store_id) for store_id in wanted
        ]

    def add(
        self,
        *,
        name: str,
        quantity: float,
        unit: Unit,
        store_ids: Iterable[UUID],
        available_from: date | None,
        origin: ItemOrigin,
        catalogue_entry_id: UUID | None = None,
        item_id: UUID | None = None,
    ) -> ShoppingItem:
        """Add an item to the list.

        Args:
            name: The item's name.
            quantity: How much is needed; greater than zero.
            unit: The unit the quantity is expressed in.
            store_ids: Stores the item may be bought at; empty means anywhere.
            available_from: The date the item becomes worth buying, or None.
            origin: How the item came to be on the list.
            catalogue_entry_id: The catalogue entry this item is an instance
                of, from which it derives its category.
            item_id: An identifier chosen by the client, so an item added
                offline can be referred to before the server has seen it and
                replayed without landing twice. None lets the server mint one.

        Returns:
            The created item.
        """
        row = ShoppingItemORM(
            id=item_id if item_id is not None else uuid4(),
            name=name.strip(),
            quantity=quantity,
            unit=unit,
            available_from=available_from,
            origin=origin,
            catalogue_entry_id=catalogue_entry_id,
        )
        self._session.add(row)
        self._session.flush()
        self._set_stores(row, store_ids)
        self._session.flush()
        return self._reload(row.id)

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
        edited_at: datetime | None = None,
    ) -> ShoppingItem:
        """Change an item's fields, leaving unsupplied ones untouched.

        Args:
            item_id: The item to change.
            name: A new name, or None to leave it.
            quantity: A new quantity, or None to leave it.
            unit: A new unit, or None to leave it.
            store_ids: The item's new complete set of stores, or None to leave
                them. An empty iterable clears them.
            available_from: A new availability date, or None to leave it.
            clear_available_from: Remove the availability date. Takes
                precedence over available_from.
            edited_at: When the editing client made this edit. Recorded as
                the item's `updated_at`; None leaves it as it was.

        Returns:
            The updated item.
        """
        row = self._require_row(item_id)

        if edited_at is not None:
            row.updated_at = edited_at
        if name is not None:
            row.name = name.strip()
        if quantity is not None:
            row.quantity = quantity
        if unit is not None:
            row.unit = unit
        if clear_available_from:
            row.available_from = None
        elif available_from is not None:
            row.available_from = available_from
        if store_ids is not None:
            self._set_stores(row, store_ids)

        self._session.flush()
        return self._reload(row.id)

    def delete(self, item_id: UUID) -> None:
        """Take an item off the list without recording a purchase.

        Args:
            item_id: The item to remove.
        """
        row = self._session.get(ShoppingItemORM, item_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()

    def record_purchase(self, item_id: UUID, member_id: UUID) -> Purchase:
        """Record that a member bought an item.

        Marking an already-bought item returns the existing purchase rather
        than creating a second one, so both members marking the same item at
        once is harmless.

        Args:
            item_id: The item that was bought.
            member_id: The member who bought it.

        Returns:
            The purchase recorded against the item.
        """
        self._require_row(item_id)

        existing = self._session.scalars(
            select(ShoppingItemPurchaseORM).where(ShoppingItemPurchaseORM.item_id == item_id)
        ).one_or_none()
        if existing is not None:
            return to_purchase(existing)

        purchase = ShoppingItemPurchaseORM(
            item_id=item_id,
            member_id=member_id,
            bought_at=now_utc(),
        )
        self._session.add(purchase)
        self._session.flush()
        return to_purchase(purchase)

    def remove_purchase(self, item_id: UUID) -> None:
        """Undo a purchase, returning the item to the outstanding list.

        Args:
            item_id: The item whose purchase should be removed.
        """
        existing = self._session.scalars(
            select(ShoppingItemPurchaseORM).where(ShoppingItemPurchaseORM.item_id == item_id)
        ).one_or_none()
        if existing is not None:
            self._session.delete(existing)
        # Un-clear as well: an outstanding item is never a cleared one.
        row = self._session.get(ShoppingItemORM, item_id)
        if row is not None:
            row.cleared_at = None
        self._session.flush()
