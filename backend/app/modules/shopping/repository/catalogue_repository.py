"""SQLAlchemy catalogue repository.

Suggestions are a prefix match in SQL against ``lower(name)``, backed by the
same index that enforces uniqueness. At a few hundred rows this is not a
performance decision: a search extension would cost a dependency to explain
for a table small enough to scan, and fuzzy matching would make "mlik" match
"milk" — hiding exactly the duplicate that merge exists to surface.
"""

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.modules.shopping.domain.catalogue import CatalogueEntry
from app.modules.shopping.errors import EntryNotFoundError
from app.modules.shopping.repository.mapping import to_entry
from app.modules.shopping.repository.orm import (
    CatalogueEntryORM,
    CatalogueEntryStoreORM,
    ShoppingItemORM,
)


def _escape_like(value: str) -> str:
    """Escape LIKE metacharacters so a typed "%" matches a literal "%".

    Args:
        value: The raw prefix.

    Returns:
        The prefix safe to embed in a LIKE pattern.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlAlchemyCatalogueRepository:
    """The catalogue, backed by the ``catalogue_entries`` table."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to a session.

        Args:
            session: The session this repository reads and writes through.
        """
        self._session = session

    def _with_relations(
        self, statement: Select[tuple[CatalogueEntryORM]]
    ) -> Select[tuple[CatalogueEntryORM]]:
        """Eager-load the category and stores the domain entry needs.

        Args:
            statement: The select to extend.

        Returns:
            The select with relations eagerly loaded.
        """
        return statement.options(
            selectinload(CatalogueEntryORM.category),
            selectinload(CatalogueEntryORM.stores).selectinload(CatalogueEntryStoreORM.store),
        )

    def _require_row(self, entry_id: UUID) -> CatalogueEntryORM:
        """Return an entry row, refusing when it does not exist.

        Args:
            entry_id: The entry to load.

        Returns:
            The entry row.

        Raises:
            EntryNotFoundError: If no entry has that id.
        """
        row = self._session.get(CatalogueEntryORM, entry_id)
        if row is None:
            raise EntryNotFoundError(entry_id)
        return row

    def _reload(self, entry_id: UUID) -> CatalogueEntry:
        """Return an entry freshly loaded with its relations.

        Args:
            entry_id: The entry to load.

        Returns:
            The domain entry.

        Raises:
            EntryNotFoundError: If no entry has that id.
        """
        row = self._session.scalars(
            self._with_relations(select(CatalogueEntryORM).where(CatalogueEntryORM.id == entry_id))
        ).one_or_none()
        if row is None:
            raise EntryNotFoundError(entry_id)
        self._session.refresh(row)
        return to_entry(row)

    # ---- reads ----

    def get(self, entry_id: UUID) -> CatalogueEntry | None:
        """Return one entry with its category and remembered stores.

        Args:
            entry_id: The entry to look up.

        Returns:
            The entry, or None when no entry has that id.
        """
        row = self._session.scalars(
            self._with_relations(select(CatalogueEntryORM).where(CatalogueEntryORM.id == entry_id))
        ).one_or_none()
        return to_entry(row) if row else None

    def list_all(self) -> list[CatalogueEntry]:
        """Return every entry, ordered by name.

        Returns:
            The catalogue.
        """
        rows = self._session.scalars(
            self._with_relations(select(CatalogueEntryORM)).order_by(
                func.lower(CatalogueEntryORM.name)
            )
        ).all()
        return [to_entry(row) for row in rows]

    def find_by_name(self, name: str) -> CatalogueEntry | None:
        """Return the entry with this name, compared case-insensitively.

        Args:
            name: The name to look for.

        Returns:
            The matching entry, or None.
        """
        row = self._session.scalars(
            self._with_relations(
                select(CatalogueEntryORM).where(
                    func.lower(CatalogueEntryORM.name) == name.strip().lower()
                )
            )
        ).one_or_none()
        return to_entry(row) if row else None

    def suggest(self, prefix: str, *, limit: int) -> list[CatalogueEntry]:
        """Return entries whose name starts with the prefix, most recent first.

        Args:
            prefix: The start of a name, compared case-insensitively.
            limit: The most entries to return.

        Returns:
            Matching entries, most recently used first.
        """
        pattern = _escape_like(prefix.strip().lower()) + "%"
        rows = self._session.scalars(
            self._with_relations(
                select(CatalogueEntryORM)
                .where(func.lower(CatalogueEntryORM.name).like(pattern, escape="\\"))
                .order_by(CatalogueEntryORM.last_used_at.desc(), CatalogueEntryORM.name)
                .limit(limit)
            )
        ).all()
        return [to_entry(row) for row in rows]

    def item_names_referencing(self, entry_id: UUID) -> tuple[str, ...]:
        """Return the names of items referring to an entry.

        Args:
            entry_id: The entry.

        Returns:
            The referring items' names, ordered, empty when none.
        """
        names = self._session.scalars(
            select(ShoppingItemORM.name)
            .where(ShoppingItemORM.catalogue_entry_id == entry_id)
            .order_by(ShoppingItemORM.name)
        ).all()
        return tuple(names)

    # ---- writes ----

    def find_or_create(self, name: str, *, used_at: datetime) -> CatalogueEntry:
        """Return the entry for a name, creating it when none matches.

        Args:
            name: The item name, compared case-insensitively.
            used_at: When the name was used, for ordering suggestions.

        Returns:
            The matching or newly created entry.
        """
        cleaned = name.strip()
        row = self._session.scalars(
            select(CatalogueEntryORM).where(func.lower(CatalogueEntryORM.name) == cleaned.lower())
        ).one_or_none()
        if row is None:
            row = CatalogueEntryORM(name=cleaned, last_used_at=used_at)
            self._session.add(row)
        else:
            row.last_used_at = used_at
        self._session.flush()
        return self._reload(row.id)

    def update(
        self,
        entry_id: UUID,
        *,
        category_id: UUID | None = None,
        clear_category: bool = False,
        store_ids: Iterable[UUID] | None = None,
    ) -> CatalogueEntry:
        """Change an entry's category or remembered stores.

        Args:
            entry_id: The entry to change.
            category_id: A new category, or None to leave it.
            clear_category: Make the entry uncategorised. Takes precedence.
            store_ids: The complete new set of remembered stores, or None to
                leave them.

        Returns:
            The updated entry.
        """
        row = self._require_row(entry_id)
        if clear_category:
            row.category_id = None
        elif category_id is not None:
            row.category_id = category_id
        if store_ids is not None:
            wanted = list(dict.fromkeys(store_ids))
            row.stores = [
                CatalogueEntryStoreORM(entry_id=row.id, store_id=store_id) for store_id in wanted
            ]
        self._session.flush()
        return self._reload(row.id)

    def rename(self, entry_id: UUID, name: str) -> CatalogueEntry:
        """Change an entry's name.

        Args:
            entry_id: The entry to rename.
            name: The new name.

        Returns:
            The renamed entry.
        """
        row = self._require_row(entry_id)
        row.name = name.strip()
        self._session.flush()
        return self._reload(row.id)

    def merge(self, *, source_id: UUID, target_id: UUID) -> CatalogueEntry:
        """Move every item from the source entry to the target, then delete the source.

        Both steps run in the caller's transaction, so a failure part-way
        leaves neither entry changed: a half-merged catalogue is worse than a
        duplicated one.

        Args:
            source_id: The entry being merged away.
            target_id: The entry that survives.

        Returns:
            The surviving entry.
        """
        source = self._require_row(source_id)
        self._require_row(target_id)

        self._session.execute(
            update(ShoppingItemORM)
            .where(ShoppingItemORM.catalogue_entry_id == source_id)
            .values(catalogue_entry_id=target_id)
        )
        self._session.delete(source)
        self._session.flush()
        return self._reload(target_id)

    def delete(self, entry_id: UUID) -> None:
        """Remove an entry that nothing refers to.

        The foreign key from items is RESTRICT, so the database refuses this
        for an entry still in use even if the service check were bypassed.

        Args:
            entry_id: The entry to remove.
        """
        row = self._session.get(CatalogueEntryORM, entry_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
