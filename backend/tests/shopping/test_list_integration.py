"""The shopping list and the catalogue, working together.

Every add remembers its name; the entry's category flows to the item; and
correcting the entry regroups items already on the list.
"""

from datetime import date
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

from app.modules.shopping.errors import (
    EmptyItemNameError,
    NonPositiveQuantityError,
    UnknownStoresError,
)
from app.modules.shopping.repository.catalogue_repository import SqlAlchemyCatalogueRepository
from app.modules.shopping.repository.category_repository import SqlAlchemyCategoryRepository
from app.modules.shopping.repository.item_repository import SqlAlchemyShoppingItemRepository
from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository
from app.modules.shopping.service.catalogue_service import CatalogueService
from app.modules.shopping.service.category_service import CategoryService
from app.modules.shopping.service.shopping_list_service import ShoppingListService
from app.modules.shopping.service.store_service import StoreService

BUDAPEST = ZoneInfo("Europe/Budapest")
TODAY = date(2026, 9, 11)


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


@pytest.fixture
def shopping(session: Session, catalogue: CatalogueService) -> ShoppingListService:
    """Provide the shopping list service on the test session.

    Args:
        session: The test session.
        catalogue: The catalogue service it remembers names through.

    Returns:
        A shopping list service.
    """
    return ShoppingListService(
        SqlAlchemyShoppingItemRepository(session),
        SqlAlchemyStoreRepository(session),
        catalogue,
        BUDAPEST,
    )


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
def stores(session: Session) -> StoreService:
    """Provide the store service on the test session.

    Args:
        session: The test session.

    Returns:
        A store service.
    """
    return StoreService(
        SqlAlchemyStoreRepository(session), SqlAlchemyShoppingItemRepository(session)
    )


class TestLinking:
    def test_adding_an_item_creates_and_links_its_entry(
        self, shopping: ShoppingListService, catalogue: CatalogueService
    ):
        item = shopping.add_item(name="sourdough")

        entries = catalogue.list_entries()
        assert [e.name for e in entries] == ["sourdough"]
        assert item.catalogue_entry_id == entries[0].id
        assert item.category is None

    def test_a_familiar_name_links_to_the_existing_entry(
        self, shopping: ShoppingListService, catalogue: CatalogueService
    ):
        first = shopping.add_item(name="milk")

        second = shopping.add_item(name="Milk")

        assert second.catalogue_entry_id == first.catalogue_entry_id
        assert len(catalogue.list_entries()) == 1

    def test_a_rejected_add_leaves_no_entry_behind(
        self, shopping: ShoppingListService, catalogue: CatalogueService
    ):
        with pytest.raises(EmptyItemNameError):
            shopping.add_item(name="   ")
        with pytest.raises(NonPositiveQuantityError):
            shopping.add_item(name="ghost", quantity=0)

        assert catalogue.list_entries() == []


class TestStorePrefill:
    def test_remembered_stores_are_copied_when_none_are_given(
        self, shopping: ShoppingListService, catalogue: CatalogueService, stores: StoreService
    ):
        lidl = stores.add_store("Lidl")
        spar = stores.add_store("Spar")
        entry = catalogue.remember("ketchup")
        catalogue.set_stores(entry.id, [lidl.id, spar.id])

        item = shopping.add_item(name="ketchup")

        assert [s.name for s in item.stores] == ["Lidl", "Spar"]

    def test_explicit_stores_override_the_prefill_and_leave_the_entry_alone(
        self, shopping: ShoppingListService, catalogue: CatalogueService, stores: StoreService
    ):
        lidl = stores.add_store("Lidl")
        spar = stores.add_store("Spar")
        entry = catalogue.remember("ketchup")
        catalogue.set_stores(entry.id, [lidl.id, spar.id])

        item = shopping.add_item(name="ketchup", store_ids=[])

        assert item.stores == ()
        assert [s.name for s in catalogue.get_entry(entry.id).stores] == ["Lidl", "Spar"]
        # And it shows up everywhere, as an unrestricted item should.
        assert [i.name for i in shopping.shopping_view(lidl.id)] == ["ketchup"]

    def test_an_unknown_store_in_the_override_is_refused(
        self, shopping: ShoppingListService, catalogue: CatalogueService
    ):
        catalogue.remember("ketchup")

        with pytest.raises(UnknownStoresError):
            shopping.add_item(name="ketchup", store_ids=[uuid4()])


class TestCategoryFlow:
    def test_an_item_derives_its_category_from_its_entry(
        self,
        shopping: ShoppingListService,
        catalogue: CatalogueService,
        categories: CategoryService,
    ):
        bakery = categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")
        entry = catalogue.remember("sourdough")
        catalogue.set_category(entry.id, bakery.id)

        item = shopping.add_item(name="sourdough")

        assert item.category is not None
        assert item.category.name == "Bakery"

    def test_correcting_an_entry_regroups_an_item_already_on_the_list(
        self,
        shopping: ShoppingListService,
        catalogue: CatalogueService,
        categories: CategoryService,
    ):
        # Task 5.5: the item is on the list first, uncategorised.
        item = shopping.add_item(name="sourdough")
        assert shopping.get_item(item.id).category is None
        bakery = categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")

        assert item.catalogue_entry_id is not None
        catalogue.set_category(item.catalogue_entry_id, bakery.id)

        regrouped = shopping.get_item(item.id)
        assert regrouped.category is not None
        assert regrouped.category.name == "Bakery"

    def test_the_list_comes_back_in_category_order_with_uncategorised_last(
        self,
        shopping: ShoppingListService,
        catalogue: CatalogueService,
        categories: CategoryService,
    ):
        produce = categories.add_category(name="Produce", icon="🥦", colour="#4c9a2a")
        dairy = categories.add_category(name="Dairy", icon="🧀", colour="#e0b53a")
        for name, category in (("milk", dairy), ("apples", produce), ("cheese", dairy)):
            catalogue.set_category(catalogue.remember(name).id, category.id)
        for name in ("cheese", "mystery thing", "milk", "apples", "another mystery"):
            shopping.add_item(name=name)

        names = [i.name for i in shopping.full_list()]

        assert names == ["apples", "cheese", "milk", "another mystery", "mystery thing"]

    def test_reordering_categories_reorders_the_list(
        self,
        shopping: ShoppingListService,
        catalogue: CatalogueService,
        categories: CategoryService,
    ):
        produce = categories.add_category(name="Produce", icon="🥦", colour="#4c9a2a")
        dairy = categories.add_category(name="Dairy", icon="🧀", colour="#e0b53a")
        catalogue.set_category(catalogue.remember("milk").id, dairy.id)
        catalogue.set_category(catalogue.remember("apples").id, produce.id)
        shopping.add_item(name="milk")
        shopping.add_item(name="apples")

        categories.reorder_categories([dairy.id, produce.id])

        assert [i.name for i in shopping.full_list()] == ["milk", "apples"]


class TestQueryCount:
    def test_listing_does_not_query_once_per_item(
        self,
        shopping: ShoppingListService,
        catalogue: CatalogueService,
        categories: CategoryService,
        engine: Engine,
    ):
        # Task 5.3: the category comes through a join, not a per-row lookup.
        dairy = categories.add_category(name="Dairy", icon="🧀", colour="#e0b53a")
        for i in range(12):
            catalogue.set_category(catalogue.remember(f"thing {i}").id, dairy.id)
            shopping.add_item(name=f"thing {i}")

        statements: list[str] = []

        def record(
            _conn: Any,
            _cursor: Any,
            statement: str,
            _parameters: Any,
            _context: Any,
            _executemany: bool,
        ) -> None:
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", record)
        try:
            items = shopping.full_list()
        finally:
            event.remove(engine, "before_cursor_execute", record)

        assert len(items) == 12
        # One select for items (with the entry+category joined), plus one
        # selectin load each for stores and purchases. Never twelve-plus.
        assert len(statements) <= 4, statements
