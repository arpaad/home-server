"""Bought items stay visible until cleared; clearing never deletes a purchase."""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.shopping.domain.item import ShoppingItem
from app.modules.shopping.domain.purchase import Purchase
from app.modules.shopping.repository.item_repository import SqlAlchemyShoppingItemRepository
from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository

TODAY = date(2026, 9, 11)


@pytest.fixture
def items(session: Session) -> SqlAlchemyShoppingItemRepository:
    """Provide the item repository on the test session.

    Args:
        session: The test session.

    Returns:
        An item repository.
    """
    return SqlAlchemyShoppingItemRepository(session)


@pytest.fixture
def stores(session: Session) -> SqlAlchemyStoreRepository:
    """Provide the store repository on the test session.

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
    """Reduce items to their names.

    Args:
        result: Items returned by the repository.

    Returns:
        The items' names.
    """
    return [item.name for item in result]


def purchase_count(session: Session) -> int:
    """Count purchase rows.

    Args:
        session: The test session.

    Returns:
        The number of purchase rows.
    """
    return session.execute(text("SELECT count(*) FROM shopping_item_purchases")).scalar_one()


class TestDomain:
    def test_a_bought_and_cleared_item_is_neither_outstanding_nor_uncleared(self):
        item_id = uuid4()
        item = ShoppingItem(
            id=item_id,
            name="milk",
            purchase=Purchase(
                id=uuid4(), item_id=item_id, member_id=uuid4(), bought_at=datetime.now(UTC)
            ),
            cleared_at=datetime.now(UTC),
        )

        assert not item.is_outstanding
        assert item.is_cleared

    def test_an_outstanding_item_is_not_cleared(self):
        assert not ShoppingItem(id=uuid4(), name="milk").is_cleared


class TestBoughtUncleared:
    def test_only_bought_and_uncleared_items_are_listed(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID
    ):
        add(items, "outstanding")
        bought = add(items, "bought")
        cleared = add(items, "cleared")
        items.record_purchase(bought.id, member_id)
        items.record_purchase(cleared.id, member_id)
        items.clear_bought()
        # Buy one more after clearing so there is an uncleared one to see.
        later = add(items, "later")
        items.record_purchase(later.id, member_id)

        assert names(items.list_bought_uncleared()) == ["later"]

    def test_the_store_rule_applies_to_bought_items_too(
        self,
        items: SqlAlchemyShoppingItemRepository,
        stores: SqlAlchemyStoreRepository,
        member_id: UUID,
    ):
        lidl = stores.add("Lidl")
        aldi = stores.add("Aldi")
        anywhere = add(items, "milk")
        lidl_only = add(items, "bread", store_ids=(lidl.id,))
        aldi_only = add(items, "cat litter", store_ids=(aldi.id,))
        for item in (anywhere, lidl_only, aldi_only):
            items.record_purchase(item.id, member_id)

        in_lidl = names(items.list_bought_uncleared(store_id=lidl.id))

        assert set(in_lidl) == {"milk", "bread"}
        assert "cat litter" not in in_lidl

    def test_availability_is_ignored_for_bought_items(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID
    ):
        future = add(items, "sale coffee", available_from=date(2099, 1, 1))
        items.record_purchase(future.id, member_id)

        assert names(items.list_bought_uncleared()) == ["sale coffee"]
        # And it is still not "outstanding": the outstanding query is untouched.
        assert items.list_outstanding(today=TODAY, include_upcoming=True) == []

    def test_most_recently_bought_comes_first(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID, session: Session
    ):
        first = add(items, "first")
        second = add(items, "second")
        items.record_purchase(first.id, member_id)
        items.record_purchase(second.id, member_id)
        # Make the ordering unambiguous regardless of clock resolution.
        session.execute(
            text(
                "UPDATE shopping_item_purchases SET bought_at = now() - interval '1 hour' WHERE item_id = :i"
            ),
            {"i": first.id},
        )

        assert names(items.list_bought_uncleared()) == ["second", "first"]

    def test_bought_items_are_absent_from_the_outstanding_list(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID
    ):
        item = add(items, "milk")
        items.record_purchase(item.id, member_id)

        assert items.list_outstanding(today=TODAY) == []


class TestClearing:
    def test_clear_marks_only_bought_uncleared_items_and_keeps_purchases(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID, session: Session
    ):
        outstanding = add(items, "outstanding")
        bought_a = add(items, "a")
        bought_b = add(items, "b")
        items.record_purchase(bought_a.id, member_id)
        items.record_purchase(bought_b.id, member_id)

        cleared = items.clear_bought()

        assert cleared == 2
        assert items.list_bought_uncleared() == []
        assert names(items.list_outstanding(today=TODAY)) == ["outstanding"]
        assert purchase_count(session) == 2
        stored = items.get(bought_a.id)
        assert stored is not None and stored.is_cleared and stored.purchase is not None
        untouched = items.get(outstanding.id)
        assert untouched is not None and not untouched.is_cleared

    def test_clear_is_idempotent(self, items: SqlAlchemyShoppingItemRepository, member_id: UUID):
        item = add(items, "milk")
        items.record_purchase(item.id, member_id)

        assert items.clear_bought() == 1
        assert items.clear_bought() == 0

    def test_clear_with_nothing_bought_clears_nothing(
        self, items: SqlAlchemyShoppingItemRepository
    ):
        add(items, "milk")

        assert items.clear_bought() == 0


class TestUndo:
    def test_undoing_a_cleared_item_leaves_it_outstanding_and_uncleared(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID
    ):
        item = add(items, "milk")
        items.record_purchase(item.id, member_id)
        items.clear_bought()

        items.remove_purchase(item.id)

        stored = items.get(item.id)
        assert stored is not None
        assert stored.is_outstanding
        assert not stored.is_cleared
        assert names(items.list_outstanding(today=TODAY)) == ["milk"]

    def test_undoing_a_bought_item_returns_it_to_outstanding(
        self, items: SqlAlchemyShoppingItemRepository, member_id: UUID
    ):
        item = add(items, "milk")
        items.record_purchase(item.id, member_id)

        items.remove_purchase(item.id)

        assert items.list_bought_uncleared() == []
        assert names(items.list_outstanding(today=TODAY)) == ["milk"]


# ---- service and API ----


def listed(client: TestClient, **params: Any) -> list[dict[str, Any]]:
    """List items over HTTP.

    Args:
        client: The test client.
        **params: Query parameters.

    Returns:
        The items.
    """
    r = client.get("/api/shopping/items", params=params)
    assert r.status_code == 200, r.text
    result: list[dict[str, Any]] = r.json()
    return result


def buy(client: TestClient, item_id: str, member_id: UUID) -> None:
    """Mark an item bought over HTTP.

    Args:
        client: The test client.
        item_id: The item.
        member_id: The buying member.
    """
    r = client.post(
        f"/api/shopping/items/{item_id}/purchase", headers={"X-Household-Member": str(member_id)}
    )
    assert r.status_code == 200, r.text


def create(client: TestClient, name: str, store_ids: list[str] | None = None) -> str:
    """Create an item over HTTP.

    Args:
        client: The test client.
        name: The item's name.
        store_ids: Stores, or None for anywhere.

    Returns:
        The item's id.
    """
    r = client.post("/api/shopping/items", json={"name": name, "store_ids": store_ids or []})
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestViewsOverHttp:
    def test_outstanding_come_first_then_bought_most_recent_first(
        self, client: TestClient, member_id: UUID, session: Session
    ):
        create(client, "zebra crossing")
        first = create(client, "first bought")
        second = create(client, "second bought")
        buy(client, first, member_id)
        buy(client, second, member_id)
        session.execute(
            text(
                "UPDATE shopping_item_purchases SET bought_at = now() - interval '1 hour' WHERE item_id = :i"
            ),
            {"i": first},
        )

        rows = listed(client)

        assert [r["name"] for r in rows] == ["zebra crossing", "second bought", "first bought"]
        assert rows[0]["purchase"] is None
        assert rows[1]["purchase"] is not None and rows[1]["cleared_at"] is None

    def test_a_cleared_item_is_absent(self, client: TestClient, member_id: UUID):
        item = create(client, "milk")
        buy(client, item, member_id)

        r = client.post("/api/shopping/items/clear-bought")

        assert r.status_code == 200
        assert r.json() == {"cleared": 1}
        assert listed(client) == []

    def test_a_bought_item_follows_its_stores(self, client: TestClient, member_id: UUID):
        lidl = client.post("/api/shopping/stores", json={"name": "Lidl"}).json()["id"]
        aldi = client.post("/api/shopping/stores", json={"name": "Aldi"}).json()["id"]
        item = create(client, "cat litter", [aldi])
        buy(client, item, member_id)

        assert [r["name"] for r in listed(client, store_id=lidl)] == []
        assert [r["name"] for r in listed(client, store_id=aldi)] == ["cat litter"]


class TestClearOverHttp:
    def test_three_bought_two_outstanding(
        self, client: TestClient, member_id: UUID, session: Session
    ):
        create(client, "stay one")
        create(client, "stay two")
        for name in ("a", "b", "c"):
            buy(client, create(client, name), member_id)

        r = client.post("/api/shopping/items/clear-bought")

        assert r.json() == {"cleared": 3}
        assert sorted(x["name"] for x in listed(client)) == ["stay one", "stay two"]
        assert purchase_count(session) == 3

    def test_clearing_twice_reports_zero_the_second_time(self, client: TestClient, member_id: UUID):
        buy(client, create(client, "milk"), member_id)

        assert client.post("/api/shopping/items/clear-bought").json() == {"cleared": 1}
        assert client.post("/api/shopping/items/clear-bought").json() == {"cleared": 0}
