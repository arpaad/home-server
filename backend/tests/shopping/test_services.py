"""The service layer's rules: unknown stores, idempotent purchase, store use."""

from datetime import date
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.shopping.errors import (
    DuplicateStoreNameError,
    EmptyItemNameError,
    EmptyStoreNameError,
    ItemNotFoundError,
    NonPositiveQuantityError,
    StoreInUseError,
    StoreNotFoundError,
    UnknownStoresError,
)
from app.modules.shopping.repository.catalogue_repository import SqlAlchemyCatalogueRepository
from app.modules.shopping.repository.category_repository import SqlAlchemyCategoryRepository
from app.modules.shopping.repository.item_repository import SqlAlchemyShoppingItemRepository
from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository
from app.modules.shopping.service.catalogue_service import CatalogueService
from app.modules.shopping.service.shopping_list_service import ShoppingListService
from app.modules.shopping.service.store_service import StoreService

BUDAPEST = ZoneInfo("Europe/Budapest")


@pytest.fixture
def shopping(session: Session) -> ShoppingListService:
    """Provide the shopping list service on the test session.

    Args:
        session: The test session.

    Returns:
        A shopping list service.
    """
    return ShoppingListService(
        SqlAlchemyShoppingItemRepository(session),
        SqlAlchemyStoreRepository(session),
        CatalogueService(
            SqlAlchemyCatalogueRepository(session),
            SqlAlchemyCategoryRepository(session),
            SqlAlchemyStoreRepository(session),
        ),
        BUDAPEST,
    )


@pytest.fixture
def store_service(session: Session) -> StoreService:
    """Provide the store service on the test session.

    Args:
        session: The test session.

    Returns:
        A store service.
    """
    return StoreService(
        SqlAlchemyStoreRepository(session),
        SqlAlchemyShoppingItemRepository(session),
    )


class TestAddingItems:
    def test_an_item_with_only_a_name_gets_one_piece_and_no_store(
        self, shopping: ShoppingListService
    ):
        item = shopping.add_item(name="ketchup")

        assert item.quantity == pytest.approx(1.0)
        assert item.unit == "piece"
        assert item.stores == ()
        assert item.available_from is None
        assert item.origin == "manual"

    def test_an_empty_name_is_rejected_and_creates_nothing(self, shopping: ShoppingListService):
        with pytest.raises(EmptyItemNameError):
            shopping.add_item(name="   ")

        assert shopping.full_list() == []

    def test_a_non_positive_quantity_is_rejected_and_creates_nothing(
        self, shopping: ShoppingListService
    ):
        with pytest.raises(NonPositiveQuantityError):
            shopping.add_item(name="milk", quantity=0)

        assert shopping.full_list() == []

    def test_an_unknown_store_is_rejected_and_creates_nothing(self, shopping: ShoppingListService):
        missing = uuid4()

        with pytest.raises(UnknownStoresError) as caught:
            shopping.add_item(name="ketchup", store_ids=[missing])

        assert caught.value.store_ids == frozenset({missing})
        assert shopping.full_list() == []

    def test_the_name_is_stripped(self, shopping: ShoppingListService):
        assert shopping.add_item(name="  ketchup \n").name == "ketchup"


class TestEditingItems:
    def test_an_unknown_store_is_rejected_and_leaves_the_item_alone(
        self, shopping: ShoppingListService, store_service: StoreService
    ):
        lidl = store_service.add_store("Lidl")
        item = shopping.add_item(name="ketchup", store_ids=[lidl.id])

        with pytest.raises(UnknownStoresError):
            shopping.edit_item(item.id, store_ids=[uuid4()])

        assert [s.name for s in shopping.get_item(item.id).stores] == ["Lidl"]

    def test_editing_an_unknown_item_is_refused(self, shopping: ShoppingListService):
        with pytest.raises(ItemNotFoundError):
            shopping.edit_item(uuid4(), name="nope")

    def test_an_edit_is_visible_on_the_shared_item(self, shopping: ShoppingListService):
        item = shopping.add_item(name="milk", quantity=1)

        shopping.edit_item(item.id, quantity=3)

        assert shopping.get_item(item.id).quantity == pytest.approx(3.0)


class TestRemovingItems:
    def test_removing_records_no_purchase(self, shopping: ShoppingListService, session: Session):
        item = shopping.add_item(name="milk")

        shopping.remove_item(item.id)

        with pytest.raises(ItemNotFoundError):
            shopping.get_item(item.id)
        assert (
            session.execute(text("SELECT count(*) FROM shopping_item_purchases")).scalar_one() == 0
        )

    def test_removing_an_unknown_item_is_refused(self, shopping: ShoppingListService):
        with pytest.raises(ItemNotFoundError):
            shopping.remove_item(uuid4())


class TestBuying:
    def test_marking_twice_creates_one_purchase(
        self, shopping: ShoppingListService, member_id: UUID, session: Session
    ):
        item = shopping.add_item(name="milk")

        first = shopping.mark_bought(item.id, member_id)
        second = shopping.mark_bought(item.id, member_id)

        assert first.id == second.id
        assert (
            session.execute(text("SELECT count(*) FROM shopping_item_purchases")).scalar_one() == 1
        )

    def test_undo_leaves_no_purchase_recorded(
        self, shopping: ShoppingListService, member_id: UUID, session: Session
    ):
        item = shopping.add_item(name="milk")
        shopping.mark_bought(item.id, member_id)

        restored = shopping.undo_purchase(item.id)

        assert restored.is_outstanding
        assert (
            session.execute(text("SELECT count(*) FROM shopping_item_purchases")).scalar_one() == 0
        )

    def test_buying_removes_the_item_from_both_its_stores(
        self,
        shopping: ShoppingListService,
        store_service: StoreService,
        member_id: UUID,
    ):
        lidl = store_service.add_store("Lidl")
        spar = store_service.add_store("Spar")
        item = shopping.add_item(name="ketchup", store_ids=[lidl.id, spar.id])

        shopping.mark_bought(item.id, member_id)

        assert shopping.shopping_view(lidl.id) == []
        assert shopping.shopping_view(spar.id) == []


class TestStores:
    def test_a_duplicate_name_is_rejected_case_insensitively(self, store_service: StoreService):
        store_service.add_store("Lidl")

        with pytest.raises(DuplicateStoreNameError):
            store_service.add_store("lidl")

        assert [s.name for s in store_service.list_stores()] == ["Lidl"]

    def test_a_blank_name_is_rejected(self, store_service: StoreService):
        with pytest.raises(EmptyStoreNameError):
            store_service.add_store("  ")

    def test_deleting_a_store_in_use_is_refused_and_names_the_items(
        self, store_service: StoreService, shopping: ShoppingListService
    ):
        lidl = store_service.add_store("Lidl")
        shopping.add_item(name="ketchup", store_ids=[lidl.id])
        shopping.add_item(name="bread", store_ids=[lidl.id])

        with pytest.raises(StoreInUseError) as caught:
            store_service.delete_store(lidl.id)

        assert caught.value.item_names == ("bread", "ketchup")
        assert store_service.get_store(lidl.id).name == "Lidl"
        assert [i.name for i in shopping.shopping_view(lidl.id)] == ["bread", "ketchup"]

    def test_deleting_an_unused_store_succeeds(self, store_service: StoreService):
        aldi = store_service.add_store("Aldi")

        store_service.delete_store(aldi.id)

        with pytest.raises(StoreNotFoundError):
            store_service.get_store(aldi.id)

    def test_a_store_becomes_deletable_once_its_items_are_bought(
        self,
        store_service: StoreService,
        shopping: ShoppingListService,
        member_id: UUID,
    ):
        lidl = store_service.add_store("Lidl")
        item = shopping.add_item(name="ketchup", store_ids=[lidl.id])
        shopping.mark_bought(item.id, member_id)

        store_service.delete_store(lidl.id)

        assert store_service.list_stores() == []

    def test_deleting_an_unknown_store_is_refused(self, store_service: StoreService):
        with pytest.raises(StoreNotFoundError):
            store_service.delete_store(uuid4())


class TestTheFullList:
    def test_the_full_list_shows_upcoming_items_the_store_view_hides(
        self, shopping: ShoppingListService, store_service: StoreService
    ):
        lidl = store_service.add_store("Lidl")
        shopping.add_item(name="now", store_ids=[lidl.id])
        shopping.add_item(name="later", store_ids=[lidl.id], available_from=date(2099, 1, 1))

        assert [i.name for i in shopping.shopping_view(lidl.id)] == ["now"]
        assert [i.name for i in shopping.full_list()] == ["later", "now"]
