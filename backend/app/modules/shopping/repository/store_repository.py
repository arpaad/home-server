"""SQLAlchemy store repository."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.shopping.domain.store import Store
from app.modules.shopping.repository.mapping import to_store
from app.modules.shopping.repository.orm import StoreORM


class SqlAlchemyStoreRepository:
    """The store registry, backed by the ``stores`` table."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to a session.

        Args:
            session: The session this repository reads and writes through.
        """
        self._session = session

    def list_all(self) -> list[Store]:
        """Return every store, ordered by name.

        Returns:
            The stores in the registry.
        """
        rows = self._session.scalars(select(StoreORM).order_by(StoreORM.name)).all()
        return [to_store(row) for row in rows]

    def get(self, store_id: UUID) -> Store | None:
        """Return one store.

        Args:
            store_id: The store to look up.

        Returns:
            The store, or None when no store has that id.
        """
        row = self._session.get(StoreORM, store_id)
        return to_store(row) if row else None

    def find_by_name(self, name: str) -> Store | None:
        """Return the store with this name, compared case-insensitively.

        The comparison is done in SQL against the same expression the unique
        index is built on, so the check and the constraint cannot diverge.

        Args:
            name: The name to look for.

        Returns:
            The matching store, or None.
        """
        row = self._session.scalars(
            select(StoreORM).where(func.lower(StoreORM.name) == name.strip().lower())
        ).one_or_none()
        return to_store(row) if row else None

    def unknown_ids(self, store_ids: Iterable[UUID]) -> frozenset[UUID]:
        """Return which of the given ids are not in the registry.

        Args:
            store_ids: The ids to check.

        Returns:
            The subset that matches no store; empty when all exist.
        """
        wanted = frozenset(store_ids)
        if not wanted:
            return frozenset()
        found = set(self._session.scalars(select(StoreORM.id).where(StoreORM.id.in_(wanted))).all())
        return frozenset(wanted - found)

    def add(self, name: str) -> Store:
        """Add a store to the registry.

        Args:
            name: The store's name; surrounding whitespace is stripped.

        Returns:
            The created store.
        """
        row = StoreORM(name=name.strip())
        self._session.add(row)
        self._session.flush()
        return to_store(row)

    def delete(self, store_id: UUID) -> None:
        """Remove a store from the registry.

        Args:
            store_id: The store to remove.
        """
        row = self._session.get(StoreORM, store_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
