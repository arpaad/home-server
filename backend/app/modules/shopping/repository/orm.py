"""ORM mappings for the shopping capability.

The schema carries the capability's two structural rules:

- An item references stores through a join table with foreign keys, so a store
  that does not exist cannot be assigned and a store in use cannot vanish.
- A purchase is a row, not a flag, so an item is outstanding exactly when it
  has no purchase row.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StoreORM(Base):
    """A store the household shops at.

    The unique index is on ``lower(name)``: comparing case-insensitively in
    the database is what stops "lidl" becoming a second "Lidl" and quietly
    hiding items from the store they belong to.
    """

    __tablename__ = "stores"
    __table_args__ = (
        Index("ux_stores_name_lower", text("lower(name)"), unique=True),
        CheckConstraint("btrim(name) <> ''", name="ck_stores_name_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    items: Mapped[list[ShoppingItemStoreORM]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ShoppingItemORM(Base):
    """One item on the single shared household list."""

    __tablename__ = "shopping_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_shopping_items_quantity_positive"),
        CheckConstraint("btrim(name) <> ''", name="ck_shopping_items_name_not_blank"),
        CheckConstraint(
            "unit IN ('piece', 'box', 'kg', 'g', 'l', 'dl', 'm', 'cm')",
            name="ck_shopping_items_unit_known",
        ),
        CheckConstraint(
            "origin IN ('manual', 'recipe')",
            name="ck_shopping_items_origin_known",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("1"))
    unit: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'piece'"))

    # NULL means "always available". A date means the item stays out of
    # shopping views until the household's local date reaches it.
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)

    origin: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'manual'"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    stores: Mapped[list[ShoppingItemStoreORM]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    purchases: Mapped[list[ShoppingItemPurchaseORM]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ShoppingItemStoreORM(Base):
    """Links an item to a store it may be bought at.

    No row for an item means "anywhere", which is why the absence of rows is
    meaningful and the join table is not merely an optimisation.
    """

    __tablename__ = "shopping_item_stores"
    __table_args__ = (Index("ix_shopping_item_stores_store_id", "store_id"),)

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("shopping_items.id", ondelete="CASCADE"), primary_key=True
    )
    # RESTRICT, not CASCADE: dropping the link would turn a restricted item
    # into one that appears in every store's view.
    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), primary_key=True
    )

    item: Mapped[ShoppingItemORM] = relationship(back_populates="stores")
    store: Mapped[StoreORM] = relationship(back_populates="items")


class ShoppingItemPurchaseORM(Base):
    """Records that an item was bought, by which member and when.

    One row per item: marking an already-bought item is idempotent, which
    matters when both members act at once in a shop. Undo deletes the row.
    """

    __tablename__ = "shopping_item_purchases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("shopping_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("household_members.id", ondelete="RESTRICT"), nullable=False
    )
    bought_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item: Mapped[ShoppingItemORM] = relationship(back_populates="purchases")
