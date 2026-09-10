"""The store-and-availability filter, evaluated in SQL against PostgreSQL.

These are the tests that matter most in this capability: they pin down the
rule that one item, written once, appears in exactly the right stores' views.
"""

from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.shopping.domain.item import ShoppingItem
from app.modules.shopping.errors import ItemNotFoundError
from app.modules.shopping.repository.item_repository import SqlAlchemyShoppingItemRepository
from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository

TODAY = date(2026, 9, 10)
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)


@pytest.fixture
def items(session: Session) -> SqlAlchemyShoppingItemRepository:
    """Provide an item repository on the test session.

    Args:
        session: The test session.

    Returns:
        An item repository.
    """
    return SqlAlchemyShoppingItemRepository(session)


@pytest.fixture
def stores(session: Session) -> SqlAlchemyStoreRepository:
    """Provide a store repository on the test session.

    Args:
        session: The test session.

    Returns:
        A store repository.
    """
    return SqlAlchemyStoreRepository(session)


def add(
    items: SqlAlchemyShoppingItemRepository,
    name: str,
    *,
    store_ids: tuple[UUID, ...] = (),
    available_from: date | None = None,
) -> ShoppingItem:
    """Add an item with the defaults these tests do not care about.

    Args:
        items: The item repository.
        name: The item's name.
        store_ids: Stores the item may be bought at.
        available_from: The item's availability date.

    Returns:
        The created item.
    """
    return items.add(
        name=name,
        quantity=1.0,
        unit="piece",
        store_ids=store_ids,
        available_from=available_from,
        origin="manual",
    )


def names(result: list[ShoppingItem]) -> list[str]:
    """Reduce a list of items to their names.

    Args:
        result: Items returned by the repository.

    Returns:
        The items' names.
    """
    return [item.name for item in result]


class TestTheKetchupCase:
    """The scenario this whole capability exists to fix."""

    def test_a_store_view_holds_its_own_items_plus_the_unrestricted_ones(
        self, items: SqlAlchemyShoppingItemRepository, stores: SqlAlchemyStoreRepository
    ):
        lidl = stores.add("Lidl")
        spar = stores.add("Spar")
        aldi = stores.add("Aldi")

        add(items, "ketchup", store_ids=(lidl.id, spar.id))
        add(items, "milk")
        add(items, "cat litter", store_ids=(aldi.id,))

        in_lidl = names(items.list_outstanding(store_id=lidl.id, today=TODAY))

        assert in_lidl == ["ketchup", "milk"]
        assert "cat litter" not in in_lidl

    def test_an_item_with_no_store_appears_for_every_store(
        self, items: SqlAlchemyShoppingItemRepository, stores: SqlAlchemyStoreRepository
    ):
        lidl = stores.add("Lidl")
        spar = stores.add("Spar")
        aldi = stores.add("Aldi")
        add(items, "milk")

        for store in (lidl, spar, aldi):
            assert names(items.list_outstanding(store_id=store.id, today=TODAY)) == ["milk"]

    def test_an_item_restricted_to_two_stores_appears_for_neither_other_store(
        self, items: SqlAlchemyShoppingItemRepository, stores: SqlAlchemyStoreRepository
    ):
        lidl = stores.add("Lidl")
        spar = stores.add("Spar")
        aldi = stores.add("Aldi")
        auchan = stores.add("Auchan")
        add(items, "ketchup", store_ids=(lidl.id, spar.id))

        assert names(items.list_outstanding(store_id=lidl.id, today=TODAY)) == ["ketchup"]
        assert names(items.list_outstanding(store_id=spar.id, today=TODAY)) == ["ketchup"]
        assert names(items.list_outstanding(store_id=aldi.id, today=TODAY)) == []
        assert names(items.list_outstanding(store_id=auchan.id, today=TODAY)) == []


class TestAvailability:
    def test_an_item_with_a_future_date_is_excluded(
        self, items: SqlAlchemyShoppingItemRepository, stores: SqlAlchemyStoreRepository
    ):
        lidl = stores.add("Lidl")
        add(items, "sale coffee", store_ids=(lidl.id,), available_from=TOMORROW)

        assert names(items.list_outstanding(store_id=lidl.id, today=TODAY)) == []

    def test_an_item_becomes_available_on_its_date_with_no_edit(
        self, items: SqlAlchemyShoppingItemRepository, stores: SqlAlchemyStoreRepository
    ):
        lidl = stores.add("Lidl")
        add(items, "sale coffee", store_ids=(lidl.id,), available_from=TOMORROW)

        # The same row, one day later. Nothing was edited.
        assert names(items.list_outstanding(store_id=lidl.id, today=TOMORROW)) == ["sale coffee"]

    def test_the_boundary_is_inclusive_of_the_date_itself(
        self, items: SqlAlchemyShoppingItemRepository
    ):
        add(items, "on the day", available_from=TODAY)
        add(items, "the day before", available_from=YESTERDAY)

        assert names(items.list_outstanding(today=TODAY)) == ["on the day", "the day before"]

    def test_the_full_list_includes_upcoming_items(self, items: SqlAlchemyShoppingItemRepository):
        add(items, "now")
        add(items, "later", available_from=TOMORROW)

        assert names(items.list_outstanding(today=TODAY)) == ["now"]
        assert names(items.list_outstanding(today=TODAY, include_upcoming=True)) == [
            "later",
            "now",
        ]


class TestPurchases:
    def test_a_bought_item_leaves_every_store_view(
        self,
        items: SqlAlchemyShoppingItemRepository,
        stores: SqlAlchemyStoreRepository,
        member_id: UUID,
    ):
        lidl = stores.add("Lidl")
        spar = stores.add("Spar")
        ketchup = add(items, "ketchup", store_ids=(lidl.id, spar.id))

        items.record_purchase(ketchup.id, member_id)

        assert names(items.list_outstanding(store_id=lidl.id, today=TODAY)) == []
        assert names(items.list_outstanding(store_id=spar.id, today=TODAY)) == []
        assert names(items.list_outstanding(today=TODAY, include_upcoming=True)) == []

    def test_a_purchase_is_attributed(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID
    ):
        item = add(items, "milk")

        purchase = items.record_purchase(item.id, member_id)

        assert purchase.member_id == member_id
        assert purchase.item_id == item.id
        stored = items.get(item.id)
        assert stored is not None
        assert stored.purchase == purchase

    def test_marking_twice_does_not_create_a_second_purchase(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID, session: Session
    ):
        item = add(items, "milk")

        first = items.record_purchase(item.id, member_id)
        second = items.record_purchase(item.id, member_id)

        assert first.id == second.id
        count = session.execute(
            text("SELECT count(*) FROM shopping_item_purchases WHERE item_id = :i"),
            {"i": item.id},
        ).scalar_one()
        assert count == 1

    def test_undo_leaves_no_purchase_recorded(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID
    ):
        item = add(items, "milk")
        items.record_purchase(item.id, member_id)

        items.remove_purchase(item.id)

        stored = items.get(item.id)
        assert stored is not None
        assert stored.purchase is None
        assert names(items.list_outstanding(today=TODAY)) == ["milk"]

    def test_removing_an_item_records_no_purchase(
        self, items: SqlAlchemyShoppingItemRepository, session: Session
    ):
        item = add(items, "milk")

        items.delete(item.id)

        assert items.get(item.id) is None
        count = session.execute(text("SELECT count(*) FROM shopping_item_purchases")).scalar_one()
        assert count == 0

    def test_marking_an_unknown_item_is_refused(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID
    ):
        with pytest.raises(ItemNotFoundError):
            items.record_purchase(uuid4(), member_id)


class TestEditing:
    def test_stores_can_be_replaced(
        self, items: SqlAlchemyShoppingItemRepository, stores: SqlAlchemyStoreRepository
    ):
        lidl = stores.add("Lidl")
        spar = stores.add("Spar")
        item = add(items, "ketchup", store_ids=(lidl.id,))

        updated = items.update(item.id, store_ids=(lidl.id, spar.id))

        assert [s.name for s in updated.stores] == ["Lidl", "Spar"]
        assert names(items.list_outstanding(store_id=spar.id, today=TODAY)) == ["ketchup"]

    def test_clearing_stores_makes_an_item_buyable_anywhere(
        self, items: SqlAlchemyShoppingItemRepository, stores: SqlAlchemyStoreRepository
    ):
        lidl = stores.add("Lidl")
        aldi = stores.add("Aldi")
        item = add(items, "ketchup", store_ids=(lidl.id,))

        items.update(item.id, store_ids=())

        assert names(items.list_outstanding(store_id=aldi.id, today=TODAY)) == ["ketchup"]

    def test_unsupplied_fields_are_left_alone(self, items: SqlAlchemyShoppingItemRepository):
        item = add(items, "milk", available_from=TOMORROW)

        updated = items.update(item.id, quantity=3.0)

        assert updated.quantity == pytest.approx(3.0)
        assert updated.name == "milk"
        assert updated.available_from == TOMORROW

    def test_the_availability_date_can_be_cleared(self, items: SqlAlchemyShoppingItemRepository):
        item = add(items, "milk", available_from=TOMORROW)

        updated = items.update(item.id, clear_available_from=True)

        assert updated.available_from is None
        assert names(items.list_outstanding(today=TODAY)) == ["milk"]

    def test_updating_an_unknown_item_is_refused(self, items: SqlAlchemyShoppingItemRepository):
        with pytest.raises(ItemNotFoundError):
            items.update(uuid4(), name="nope")


class TestStoreReferences:
    def test_outstanding_items_referencing_a_store_are_reported(
        self, items: SqlAlchemyShoppingItemRepository, stores: SqlAlchemyStoreRepository
    ):
        lidl = stores.add("Lidl")
        aldi = stores.add("Aldi")
        add(items, "ketchup", store_ids=(lidl.id,))
        add(items, "bread", store_ids=(lidl.id,))
        add(items, "cat litter", store_ids=(aldi.id,))
        add(items, "milk")

        assert items.outstanding_names_referencing(lidl.id) == ("bread", "ketchup")
        assert items.outstanding_names_referencing(aldi.id) == ("cat litter",)

    def test_a_bought_item_no_longer_holds_a_store(
        self,
        items: SqlAlchemyShoppingItemRepository,
        stores: SqlAlchemyStoreRepository,
        member_id: UUID,
    ):
        lidl = stores.add("Lidl")
        ketchup = add(items, "ketchup", store_ids=(lidl.id,))

        items.record_purchase(ketchup.id, member_id)

        assert items.outstanding_names_referencing(lidl.id) == ()
