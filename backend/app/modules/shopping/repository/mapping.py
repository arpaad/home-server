"""Translation between ORM rows and the ORM-free domain types."""

from typing import cast

from app.modules.shopping.domain.catalogue import CatalogueEntry
from app.modules.shopping.domain.category import Category
from app.modules.shopping.domain.item import ItemOrigin, ShoppingItem
from app.modules.shopping.domain.purchase import Purchase
from app.modules.shopping.domain.store import Store
from app.modules.shopping.domain.units import Unit
from app.modules.shopping.repository.orm import (
    CatalogueEntryORM,
    CategoryORM,
    ShoppingItemORM,
    ShoppingItemPurchaseORM,
    StoreORM,
)


def to_store(row: StoreORM) -> Store:
    """Build a domain store from its row.

    Args:
        row: The store row.

    Returns:
        The domain store.
    """
    return Store(id=row.id, name=row.name)


def to_purchase(row: ShoppingItemPurchaseORM) -> Purchase:
    """Build a domain purchase from its row.

    Args:
        row: The purchase row.

    Returns:
        The domain purchase.
    """
    return Purchase(
        id=row.id,
        item_id=row.item_id,
        member_id=row.member_id,
        bought_at=row.bought_at,
    )


def to_item(row: ShoppingItemORM) -> ShoppingItem:
    """Build a domain item from its row, including stores and purchase.

    The ``unit`` and ``origin`` columns are cast rather than parsed: the
    database constrains both to the same sets the domain declares, so a value
    outside them cannot be stored in the first place.

    Args:
        row: The item row, with its stores, purchases and catalogue entry
            (and the entry's category) loaded.

    Returns:
        The domain item.
    """
    stores = tuple(sorted((to_store(link.store) for link in row.stores), key=lambda s: s.name))
    purchase = to_purchase(row.purchases[0]) if row.purchases else None
    entry = row.catalogue_entry
    category = to_category(entry.category) if entry is not None and entry.category else None
    return ShoppingItem(
        id=row.id,
        name=row.name,
        quantity=row.quantity,
        unit=cast(Unit, row.unit),
        stores=stores,
        available_from=row.available_from,
        origin=cast(ItemOrigin, row.origin),
        purchase=purchase,
        catalogue_entry_id=row.catalogue_entry_id,
        category=category,
        cleared_at=row.cleared_at,
    )


def to_category(row: CategoryORM) -> Category:
    """Build a domain category from its row.

    Args:
        row: The category row.

    Returns:
        The domain category.
    """
    return Category(
        id=row.id, name=row.name, icon=row.icon, colour=row.colour, position=row.position
    )


def to_entry(row: CatalogueEntryORM) -> CatalogueEntry:
    """Build a domain catalogue entry from its row, with category and stores.

    Args:
        row: The entry row, with its category and stores loaded.

    Returns:
        The domain entry.
    """
    stores = tuple(sorted((to_store(link.store) for link in row.stores), key=lambda s: s.name))
    return CatalogueEntry(
        id=row.id,
        name=row.name,
        category=to_category(row.category) if row.category is not None else None,
        stores=stores,
        last_used_at=row.last_used_at,
    )
