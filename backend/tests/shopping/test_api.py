"""Contract tests: the spec's scenarios, exercised over HTTP."""

from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

# Far enough ahead that it stays in the future however long this repo lives.
NOT_YET = date(2099, 1, 1)


def add_store(client: TestClient, name: str) -> str:
    """Create a store and return its id.

    Args:
        client: The test client.
        name: The store's name.

    Returns:
        The created store's id.
    """
    response = client.post("/api/shopping/stores", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def add_item(client: TestClient, name: str, **fields: Any) -> dict[str, Any]:
    """Create an item and return its representation.

    Args:
        client: The test client.
        name: The item's name.
        **fields: Any other fields to send.

    Returns:
        The created item.
    """
    response = client.post("/api/shopping/items", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def names_in(client: TestClient, **params: Any) -> list[str]:
    """List item names matching the given query.

    Args:
        client: The test client.
        **params: Query parameters.

    Returns:
        The matching items' names.
    """
    response = client.get("/api/shopping/items", params=params)
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()
    return [item["name"] for item in items]


class TestStoreFilteredShoppingView:
    def test_the_ketchup_scenario_end_to_end(self, client: TestClient):
        lidl = add_store(client, "Lidl")
        spar = add_store(client, "Spar")
        aldi = add_store(client, "Aldi")

        add_item(client, "ketchup", store_ids=[lidl, spar])
        add_item(client, "milk")
        add_item(client, "cat litter", store_ids=[aldi])

        assert names_in(client, store_id=lidl) == ["ketchup", "milk"]
        assert names_in(client, store_id=spar) == ["ketchup", "milk"]
        assert names_in(client, store_id=aldi) == ["cat litter", "milk"]

    def test_a_postponed_item_is_excluded_from_the_store_view(self, client: TestClient):
        lidl = add_store(client, "Lidl")
        add_item(client, "sale coffee", store_ids=[lidl], available_from=NOT_YET.isoformat())

        assert names_in(client, store_id=lidl) == []


class TestFullListView:
    def test_the_full_list_shows_upcoming_items_with_their_stores_and_dates(
        self, client: TestClient
    ):
        lidl = add_store(client, "Lidl")
        add_item(client, "now", store_ids=[lidl])
        add_item(client, "later", store_ids=[lidl], available_from=NOT_YET.isoformat())

        response = client.get("/api/shopping/items", params={"include_upcoming": True})
        payload: list[dict[str, Any]] = response.json()
        items = {item["name"]: item for item in payload}

        assert set(items) == {"now", "later"}
        assert items["later"]["available_from"] == NOT_YET.isoformat()
        assert [s["name"] for s in items["later"]["stores"]] == ["Lidl"]


class TestAddingItems:
    def test_creation_returns_the_created_item(self, client: TestClient):
        created = add_item(client, "ketchup")

        assert UUID(created["id"])
        assert created["quantity"] == pytest.approx(1.0)
        assert created["unit"] == "piece"
        assert created["stores"] == []
        assert created["origin"] == "manual"

    def test_an_empty_name_is_rejected(self, client: TestClient):
        response = client.post("/api/shopping/items", json={"name": "   "})

        assert response.status_code == 422
        assert names_in(client) == []

    def test_a_non_positive_quantity_is_rejected(self, client: TestClient):
        response = client.post("/api/shopping/items", json={"name": "milk", "quantity": 0})

        assert response.status_code == 422

    def test_an_unknown_store_is_rejected(self, client: TestClient):
        response = client.post(
            "/api/shopping/items", json={"name": "ketchup", "store_ids": [str(uuid4())]}
        )

        assert response.status_code == 422
        assert names_in(client) == []


class TestEditing:
    def test_stores_can_be_corrected(self, client: TestClient):
        lidl = add_store(client, "Lidl")
        spar = add_store(client, "Spar")
        item = add_item(client, "ketchup", store_ids=[lidl])

        response = client.patch(
            f"/api/shopping/items/{item['id']}", json={"store_ids": [lidl, spar]}
        )

        assert response.status_code == 200
        assert [s["name"] for s in response.json()["stores"]] == ["Lidl", "Spar"]
        assert names_in(client, store_id=spar) == ["ketchup"]

    def test_patching_an_unknown_item_is_a_404(self, client: TestClient):
        response = client.patch(f"/api/shopping/items/{uuid4()}", json={"name": "nope"})

        assert response.status_code == 404


class TestRemoving:
    def test_deleting_takes_the_item_off_the_list_without_a_purchase(
        self, client: TestClient, session: Session
    ):
        item = add_item(client, "milk")

        response = client.delete(f"/api/shopping/items/{item['id']}")

        assert response.status_code == 204
        assert names_in(client) == []
        assert (
            session.execute(text("SELECT count(*) FROM shopping_item_purchases")).scalar_one() == 0
        )


class TestBuying:
    def test_buying_removes_the_item_from_both_its_stores(
        self, client: TestClient, member_id: UUID
    ):
        lidl = add_store(client, "Lidl")
        spar = add_store(client, "Spar")
        item = add_item(client, "ketchup", store_ids=[lidl, spar])

        response = client.post(
            f"/api/shopping/items/{item['id']}/purchase",
            headers={"X-Household-Member": str(member_id)},
        )

        assert response.status_code == 200
        assert response.json()["member_id"] == str(member_id)
        assert names_in(client, store_id=lidl) == []
        assert names_in(client, store_id=spar) == []

    def test_buying_twice_records_one_purchase(
        self, client: TestClient, member_id: UUID, session: Session
    ):
        item = add_item(client, "milk")
        headers = {"X-Household-Member": str(member_id)}

        first = client.post(f"/api/shopping/items/{item['id']}/purchase", headers=headers)
        second = client.post(f"/api/shopping/items/{item['id']}/purchase", headers=headers)

        assert first.status_code == second.status_code == 200
        assert first.json()["bought_at"] == second.json()["bought_at"]
        assert (
            session.execute(text("SELECT count(*) FROM shopping_item_purchases")).scalar_one() == 1
        )

    def test_undo_returns_the_item_to_the_list(self, client: TestClient, member_id: UUID):
        item = add_item(client, "milk")
        client.post(
            f"/api/shopping/items/{item['id']}/purchase",
            headers={"X-Household-Member": str(member_id)},
        )

        response = client.delete(f"/api/shopping/items/{item['id']}/purchase")

        assert response.status_code == 200
        assert response.json()["purchase"] is None
        assert names_in(client) == ["milk"]

    def test_a_missing_member_header_is_rejected(self, client: TestClient):
        item = add_item(client, "milk")

        response = client.post(f"/api/shopping/items/{item['id']}/purchase")

        assert response.status_code == 400

    def test_an_unknown_member_is_rejected(self, client: TestClient):
        item = add_item(client, "milk")

        response = client.post(
            f"/api/shopping/items/{item['id']}/purchase",
            headers={"X-Household-Member": str(uuid4())},
        )

        assert response.status_code == 400


class TestStores:
    def test_a_duplicate_store_name_is_a_conflict(self, client: TestClient):
        add_store(client, "Lidl")

        response = client.post("/api/shopping/stores", json={"name": "lidl"})

        assert response.status_code == 409

    def test_deleting_a_store_in_use_is_a_conflict_naming_the_items(self, client: TestClient):
        lidl = add_store(client, "Lidl")
        add_item(client, "ketchup", store_ids=[lidl])
        add_item(client, "bread", store_ids=[lidl])

        response = client.delete(f"/api/shopping/stores/{lidl}")

        assert response.status_code == 409
        assert response.json()["items"] == ["bread", "ketchup"]

    def test_deleting_an_unused_store_succeeds(self, client: TestClient):
        aldi = add_store(client, "Aldi")

        assert client.delete(f"/api/shopping/stores/{aldi}").status_code == 204
        assert client.get("/api/shopping/stores").json() == []


class TestHouseholdMembers:
    def test_the_seeded_members_are_listed(self, client: TestClient, member_id: UUID):
        response = client.get("/api/household/members")

        assert response.status_code == 200
        listed: list[dict[str, Any]] = response.json()
        assert str(member_id) in [m["id"] for m in listed]
