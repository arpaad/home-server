"""Aggregates every ORM model so that ``Base.metadata`` is complete.

Alembic imports this module to see the full schema. A model that is not
reachable from here is invisible to autogenerate and would be dropped by the
next revision, so every ORM module belongs in this list.
"""

from app.db.base import Base
from app.modules.household.repository.member_orm import HouseholdMemberORM
from app.modules.shopping.repository.orm import (
    CatalogueEntryORM,
    CatalogueEntryStoreORM,
    CategoryORM,
    ShoppingItemORM,
    ShoppingItemPurchaseORM,
    ShoppingItemStoreORM,
    StoreORM,
)

__all__ = [
    "Base",
    "CatalogueEntryORM",
    "CatalogueEntryStoreORM",
    "CategoryORM",
    "HouseholdMemberORM",
    "ShoppingItemORM",
    "ShoppingItemPurchaseORM",
    "ShoppingItemStoreORM",
    "StoreORM",
]
