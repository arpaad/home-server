"""Business rules for the household's category registry."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.modules.shopping.domain.category import (
    Category,
    ensure_valid_category_name,
    ensure_valid_colour,
    ensure_valid_icon,
)
from app.modules.shopping.errors import CategoryNotFoundError, DuplicateCategoryNameError
from app.modules.shopping.repository.interfaces import CategoryRepository


@dataclass(frozen=True, slots=True)
class CategoryRemoval:
    """What removing a category did."""

    entries_uncategorised: int


class CategoryService:
    """Adds, edits, orders and removes the categories items are grouped by."""

    def __init__(self, categories: CategoryRepository) -> None:
        """Bind the service to its repository.

        Args:
            categories: The category registry.
        """
        self._categories = categories

    def list_categories(self) -> list[Category]:
        """Return every category in the household's configured order.

        Returns:
            The categories.
        """
        return self._categories.list_all()

    def get_category(self, category_id: UUID) -> Category:
        """Return one category.

        Args:
            category_id: The category to look up.

        Returns:
            The category.

        Raises:
            CategoryNotFoundError: If no category has that id.
        """
        category = self._categories.get(category_id)
        if category is None:
            raise CategoryNotFoundError(category_id)
        return category

    def _require_unique_name(self, name: str, *, except_id: UUID | None = None) -> None:
        """Refuse a name another category already carries, ignoring case.

        Args:
            name: The proposed name.
            except_id: A category allowed to carry it (the one being renamed).

        Raises:
            DuplicateCategoryNameError: If another category has the name.
        """
        existing = self._categories.find_by_name(name)
        if existing is not None and existing.id != except_id:
            raise DuplicateCategoryNameError(name)

    def add_category(self, *, name: str, icon: str, colour: str) -> Category:
        """Add a category at the end of the order.

        Args:
            name: The category's name.
            icon: Its emoji icon.
            colour: Its colour as #rrggbb.

        Returns:
            The created category.
        """
        cleaned = ensure_valid_category_name(name)
        self._require_unique_name(cleaned)
        existing = self._categories.list_all()
        position = (existing[-1].position + 10) if existing else 10
        return self._categories.add(
            name=cleaned,
            icon=ensure_valid_icon(icon),
            colour=ensure_valid_colour(colour),
            position=position,
        )

    def edit_category(
        self,
        category_id: UUID,
        *,
        name: str | None = None,
        icon: str | None = None,
        colour: str | None = None,
    ) -> Category:
        """Change a category's name, icon or colour.

        Args:
            category_id: The category to change.
            name: A new name, or None to leave it.
            icon: A new icon, or None to leave it.
            colour: A new colour, or None to leave it.

        Returns:
            The updated category.
        """
        self.get_category(category_id)
        cleaned_name = ensure_valid_category_name(name) if name is not None else None
        if cleaned_name is not None:
            self._require_unique_name(cleaned_name, except_id=category_id)
        return self._categories.update(
            category_id,
            name=cleaned_name,
            icon=ensure_valid_icon(icon) if icon is not None else None,
            colour=ensure_valid_colour(colour) if colour is not None else None,
        )

    def reorder_categories(self, ordered_ids: Sequence[UUID]) -> list[Category]:
        """Set the household-wide order.

        Args:
            ordered_ids: Every category id, in the desired order.

        Returns:
            The categories in their new order.

        Raises:
            CategoryNotFoundError: If any id matches no category.
        """
        known = {category.id for category in self._categories.list_all()}
        for category_id in ordered_ids:
            if category_id not in known:
                raise CategoryNotFoundError(category_id)
        return self._categories.reorder(ordered_ids)

    def entries_that_would_be_uncategorised(self, category_id: UUID) -> int:
        """Say how many entries removing a category would leave uncategorised.

        The client shows this before asking for confirmation, so a member is
        told what will happen rather than finding out afterwards.

        Args:
            category_id: The category being considered for removal.

        Returns:
            The count of entries carrying that category.
        """
        self.get_category(category_id)
        return self._categories.count_entries_referencing(category_id)

    def remove_category(self, category_id: UUID) -> CategoryRemoval:
        """Remove a category, leaving its entries uncategorised.

        Unlike deleting a store, this is not refused while in use: an absent
        category hides nothing, it only moves items into the uncategorised
        group, where they stay visible.

        Args:
            category_id: The category to remove.

        Returns:
            How many entries became uncategorised.
        """
        self.get_category(category_id)
        affected = self._categories.count_entries_referencing(category_id)
        self._categories.delete(category_id)
        return CategoryRemoval(entries_uncategorised=affected)
