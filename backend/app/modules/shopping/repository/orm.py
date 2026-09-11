"""ORM mappings for the shopping capability.

The schema carries the capability's two structural rules:

- An item references stores through a join table with foreign keys, so a store
  that does not exist cannot be assigned and a store in use cannot vanish.
- A purchase is a row, not a flag, so an item is outstanding exactly when it
  has no purchase row.
- An item's category is reached through its catalogue entry and is never
  copied onto the item, so correcting a category is one update, not many.
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
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CategoryORM(Base):
    """A category the household sorts its shopping into.

    Categories exist so a member collects everything from one part of a shop
    at a time. ``position`` is the household-wide order groups appear in; it
    is one sequence for every store, because it matches how the household
    shops rather than the layout of any one shop.
    """

    __tablename__ = "categories"
    __table_args__ = (
        Index("ux_categories_name_lower", text("lower(name)"), unique=True),
        CheckConstraint("btrim(name) <> ''", name="ck_categories_name_not_blank"),
        CheckConstraint("btrim(icon) <> ''", name="ck_categories_icon_not_blank"),
        CheckConstraint("colour ~ '^#[0-9a-fA-F]{6}$'", name="ck_categories_colour_hex"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    # An emoji: zero dependencies, renders on both phones, and a custom
    # category can pick any icon without new assets being shipped.
    icon: Mapped[str] = mapped_column(String(16), nullable=False)
    colour: Mapped[str] = mapped_column(String(7), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    entries: Mapped[list[CatalogueEntryORM]] = relationship(back_populates="category")


class CatalogueEntryORM(Base):
    """What the household buys: one row per distinct item name.

    Entries are created as a by-product of adding items, never as a step a
    member has to do first. The category lives here and nowhere else, so
    fixing a miscategorised item is a single update that regroups every item
    referring to this entry — including ones already on the list.
    """

    __tablename__ = "catalogue_entries"
    __table_args__ = (
        # One index serves both the case-insensitive uniqueness rule and the
        # prefix search behind suggestions (lower(name) LIKE 'mil%').
        Index(
            "ux_catalogue_entries_name_lower",
            text("lower(name)"),
            unique=True,
            postgresql_ops={"lower(name)": "text_pattern_ops"},
        ),
        CheckConstraint("btrim(name) <> ''", name="ck_catalogue_entries_name_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # NULL means uncategorised. Removing a category sets this to NULL rather
    # than refusing: an absent category hides nothing, it only moves items
    # into the uncategorised group.
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    # Denormalised so ordering suggestions never needs an aggregate over items
    # on every keystroke.
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    category: Mapped[CategoryORM | None] = relationship(back_populates="entries")
    stores: Mapped[list[CatalogueEntryStoreORM]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    items: Mapped[list[ShoppingItemORM]] = relationship(back_populates="catalogue_entry")


class CatalogueEntryStoreORM(Base):
    """The stores an entry is usually bought at — a prefill, not a rule.

    Adding an item copies these onto the item's own store links, after which
    the two are independent. "We normally get ketchup at Lidl, but we are in
    Spar now" has to stay possible.
    """

    __tablename__ = "catalogue_entry_stores"
    __table_args__ = (Index("ix_catalogue_entry_stores_store_id", "store_id"),)

    entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalogue_entries.id", ondelete="CASCADE"), primary_key=True
    )
    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True
    )

    entry: Mapped[CatalogueEntryORM] = relationship(back_populates="stores")
    store: Mapped[StoreORM] = relationship()


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
        Index("ix_shopping_items_catalogue_entry_id", "catalogue_entry_id"),
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

    # Nullable so the migration cannot fail on data it does not understand;
    # the backfill fills it, and a null reads as uncategorised, not as an
    # error. RESTRICT: an entry items still refer to cannot vanish except
    # through a merge, which repoints them first.
    catalogue_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "catalogue_entries.id",
            ondelete="RESTRICT",
            name="fk_shopping_items_catalogue_entry_id",
        ),
        nullable=True,
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
    catalogue_entry: Mapped[CatalogueEntryORM | None] = relationship(back_populates="items")


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
