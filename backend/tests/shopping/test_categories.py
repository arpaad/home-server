"""Categories: invariants, uniqueness, ordering, and removal that hides nothing."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.modules.shopping.domain.category import Category
from app.modules.shopping.errors import (
    CategoryNotFoundError,
    DuplicateCategoryNameError,
    EmptyCategoryIconError,
    EmptyCategoryNameError,
    InvalidCategoryColourError,
)
from app.modules.shopping.repository.catalogue_repository import SqlAlchemyCatalogueRepository
from app.modules.shopping.repository.category_repository import SqlAlchemyCategoryRepository
from app.modules.shopping.repository.item_repository import SqlAlchemyShoppingItemRepository
from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository
from app.modules.shopping.service.catalogue_service import CatalogueService
from app.modules.shopping.service.category_service import CategoryService

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)


@pytest.fixture
def categories(session: Session) -> CategoryService:
    """Provide the category service on the test session.

    Args:
        session: The test session.

    Returns:
        A category service.
    """
    return CategoryService(SqlAlchemyCategoryRepository(session))


@pytest.fixture
def catalogue(session: Session) -> CatalogueService:
    """Provide the catalogue service on the test session.

    Args:
        session: The test session.

    Returns:
        A catalogue service.
    """
    return CatalogueService(
        SqlAlchemyCatalogueRepository(session),
        SqlAlchemyCategoryRepository(session),
        SqlAlchemyStoreRepository(session),
    )


class TestInvariants:
    def test_a_category_constructs(self):
        category = Category(id=uuid4(), name="Bakery", icon="🥖", colour="#c48a3a", position=10)

        assert category.name == "Bakery"

    def test_an_empty_name_is_rejected(self):
        with pytest.raises(EmptyCategoryNameError):
            Category(id=uuid4(), name="  ", icon="🥖", colour="#c48a3a", position=10)

    def test_an_empty_icon_is_rejected(self):
        with pytest.raises(EmptyCategoryIconError):
            Category(id=uuid4(), name="Bakery", icon="", colour="#c48a3a", position=10)

    def test_a_non_hex_colour_is_rejected(self):
        with pytest.raises(InvalidCategoryColourError):
            Category(id=uuid4(), name="Bakery", icon="🥖", colour="brown", position=10)

    def test_a_short_hex_colour_is_rejected(self):
        with pytest.raises(InvalidCategoryColourError):
            Category(id=uuid4(), name="Bakery", icon="🥖", colour="#abc", position=10)


class TestRegistry:
    def test_a_category_can_be_added_and_listed(self, categories: CategoryService):
        added = categories.add_category(name="Bakery", icon="🥖", colour="#C48A3A")

        assert added.colour == "#c48a3a"
        assert [c.name for c in categories.list_categories()] == ["Bakery"]

    def test_a_differently_cased_duplicate_is_rejected_and_leaves_one(
        self, categories: CategoryService
    ):
        categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")

        with pytest.raises(DuplicateCategoryNameError):
            categories.add_category(name="bakery", icon="🍞", colour="#000000")

        assert [c.name for c in categories.list_categories()] == ["Bakery"]

    def test_a_category_can_be_renamed_and_recoloured(self, categories: CategoryService):
        bakery = categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")

        edited = categories.edit_category(bakery.id, name="Bread", colour="#111111")

        assert edited.name == "Bread"
        assert edited.colour == "#111111"
        assert edited.icon == "🥖"

    def test_renaming_onto_another_category_is_rejected(self, categories: CategoryService):
        categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")
        dairy = categories.add_category(name="Dairy", icon="🧀", colour="#e0b53a")

        with pytest.raises(DuplicateCategoryNameError):
            categories.edit_category(dairy.id, name="bakery")

    def test_renaming_to_its_own_name_in_another_case_is_fine(self, categories: CategoryService):
        bakery = categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")

        assert categories.edit_category(bakery.id, name="BAKERY").name == "BAKERY"


class TestOrdering:
    def test_new_categories_go_to_the_end(self, categories: CategoryService):
        categories.add_category(name="Produce", icon="🥦", colour="#4c9a2a")
        categories.add_category(name="Dairy", icon="🧀", colour="#e0b53a")
        categories.add_category(name="Household", icon="🧴", colour="#5a6b7a")

        assert [c.name for c in categories.list_categories()] == ["Produce", "Dairy", "Household"]

    def test_reordering_changes_the_sequence_and_persists(self, categories: CategoryService):
        produce = categories.add_category(name="Produce", icon="🥦", colour="#4c9a2a")
        dairy = categories.add_category(name="Dairy", icon="🧀", colour="#e0b53a")
        household = categories.add_category(name="Household", icon="🧴", colour="#5a6b7a")

        reordered = categories.reorder_categories([household.id, produce.id, dairy.id])

        assert [c.name for c in reordered] == ["Household", "Produce", "Dairy"]
        assert [c.name for c in categories.list_categories()] == ["Household", "Produce", "Dairy"]

    def test_reordering_with_an_unknown_id_is_refused(self, categories: CategoryService):
        produce = categories.add_category(name="Produce", icon="🥦", colour="#4c9a2a")

        with pytest.raises(CategoryNotFoundError):
            categories.reorder_categories([produce.id, uuid4()])


class TestRemoval:
    def test_removing_a_category_in_use_uncategorises_its_entries_and_hides_nothing(
        self,
        categories: CategoryService,
        catalogue: CatalogueService,
        session: Session,
    ):
        bakery = categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")
        bread = catalogue.remember("bread")
        rolls = catalogue.remember("rolls")
        catalogue.set_category(bread.id, bakery.id)
        catalogue.set_category(rolls.id, bakery.id)
        items = SqlAlchemyShoppingItemRepository(session)
        items.add(
            name="bread",
            quantity=1,
            unit="piece",
            store_ids=[],
            available_from=None,
            origin="manual",
        )

        assert categories.entries_that_would_be_uncategorised(bakery.id) == 2
        result = categories.remove_category(bakery.id)

        assert result.entries_uncategorised == 2
        assert catalogue.get_entry(bread.id).category is None
        assert catalogue.get_entry(rolls.id).category is None
        assert [i.name for i in items.list_outstanding(today=NOW.date())] == ["bread"]

    def test_removing_an_unused_category_reports_zero(self, categories: CategoryService):
        aldi = categories.add_category(name="Frozen", icon="🧊", colour="#3a8ac4")

        assert categories.remove_category(aldi.id).entries_uncategorised == 0
        assert categories.list_categories() == []

    def test_removing_an_unknown_category_is_refused(self, categories: CategoryService):
        with pytest.raises(CategoryNotFoundError):
            categories.remove_category(uuid4())
