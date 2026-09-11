"""SQLAlchemy category repository."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.shopping.domain.category import Category
from app.modules.shopping.errors import CategoryNotFoundError
from app.modules.shopping.repository.mapping import to_category
from app.modules.shopping.repository.orm import CatalogueEntryORM, CategoryORM


class SqlAlchemyCategoryRepository:
    """The category registry, backed by the ``categories`` table."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to a session.

        Args:
            session: The session this repository reads and writes through.
        """
        self._session = session

    def _require_row(self, category_id: UUID) -> CategoryORM:
        """Return a category row, refusing when it does not exist.

        Args:
            category_id: The category to load.

        Returns:
            The category row.

        Raises:
            CategoryNotFoundError: If no category has that id.
        """
        row = self._session.get(CategoryORM, category_id)
        if row is None:
            raise CategoryNotFoundError(category_id)
        return row

    def list_all(self) -> list[Category]:
        """Return every category in configured order.

        Returns:
            The categories, ordered by position then name.
        """
        rows = self._session.scalars(
            select(CategoryORM).order_by(CategoryORM.position, CategoryORM.name)
        ).all()
        return [to_category(row) for row in rows]

    def get(self, category_id: UUID) -> Category | None:
        """Return one category.

        Args:
            category_id: The category to look up.

        Returns:
            The category, or None when no category has that id.
        """
        row = self._session.get(CategoryORM, category_id)
        return to_category(row) if row else None

    def find_by_name(self, name: str) -> Category | None:
        """Return the category with this name, compared case-insensitively.

        Args:
            name: The name to look for.

        Returns:
            The matching category, or None.
        """
        row = self._session.scalars(
            select(CategoryORM).where(func.lower(CategoryORM.name) == name.strip().lower())
        ).one_or_none()
        return to_category(row) if row else None

    def add(self, *, name: str, icon: str, colour: str, position: int) -> Category:
        """Add a category.

        Args:
            name: The category's name.
            icon: Its emoji icon.
            colour: Its colour as #rrggbb.
            position: Its place in the household-wide order.

        Returns:
            The created category.
        """
        row = CategoryORM(name=name, icon=icon, colour=colour, position=position)
        self._session.add(row)
        self._session.flush()
        return to_category(row)

    def update(
        self,
        category_id: UUID,
        *,
        name: str | None = None,
        icon: str | None = None,
        colour: str | None = None,
    ) -> Category:
        """Change a category's appearance, leaving unsupplied fields untouched.

        Args:
            category_id: The category to change.
            name: A new name, or None to leave it.
            icon: A new icon, or None to leave it.
            colour: A new colour, or None to leave it.

        Returns:
            The updated category.
        """
        row = self._require_row(category_id)
        if name is not None:
            row.name = name
        if icon is not None:
            row.icon = icon
        if colour is not None:
            row.colour = colour
        self._session.flush()
        return to_category(row)

    def reorder(self, ordered_ids: Sequence[UUID]) -> list[Category]:
        """Set the household-wide order to the given sequence.

        Positions are spaced by ten so a later insert can slot between two
        without a full renumber.

        Args:
            ordered_ids: Every category id, in the desired order.

        Returns:
            The categories in their new order.
        """
        for position, category_id in enumerate(ordered_ids, start=1):
            self._session.execute(
                update(CategoryORM)
                .where(CategoryORM.id == category_id)
                .values(position=position * 10)
            )
        self._session.flush()
        return self.list_all()

    def count_entries_referencing(self, category_id: UUID) -> int:
        """Return how many catalogue entries carry this category.

        Args:
            category_id: The category being removed.

        Returns:
            The number of entries that would become uncategorised.
        """
        return (
            self._session.scalar(
                select(func.count())
                .select_from(CatalogueEntryORM)
                .where(CatalogueEntryORM.category_id == category_id)
            )
            or 0
        )

    def delete(self, category_id: UUID) -> None:
        """Remove a category; referring entries become uncategorised.

        The foreign key is ON DELETE SET NULL, so the database does the
        uncategorising and no entry can be left pointing at nothing.

        Args:
            category_id: The category to remove.
        """
        row = self._session.get(CategoryORM, category_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
