"""Contract tests for categories, the catalogue and suggestions over HTTP."""

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

API = "/api/shopping"


def add_category(client: TestClient, name: str, icon: str = "📦", colour: str = "#8a8a8a") -> str:
    """Create a category and return its id.

    Args:
        client: The test client.
        name: The category's name.
        icon: Its emoji.
        colour: Its hex colour.

    Returns:
        The created category's id.
    """
    r = client.post(f"{API}/categories", json={"name": name, "icon": icon, "colour": colour})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_store(client: TestClient, name: str) -> str:
    """Create a store and return its id.

    Args:
        client: The test client.
        name: The store's name.

    Returns:
        The created store's id.
    """
    r = client.post(f"{API}/stores", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_item(client: TestClient, name: str, **fields: Any) -> dict[str, Any]:
    """Create an item and return its representation.

    Args:
        client: The test client.
        name: The item's name.
        **fields: Any other fields to send.

    Returns:
        The created item.
    """
    r = client.post(f"{API}/items", json={"name": name, **fields})
    assert r.status_code == 201, r.text
    created: dict[str, Any] = r.json()
    return created


def entry_id_for(client: TestClient, name: str) -> str:
    """Find the catalogue entry id for a name.

    Args:
        client: The test client.
        name: The entry's name.

    Returns:
        The entry's id.
    """
    entries: list[dict[str, Any]] = client.get(f"{API}/catalogue").json()
    return next(e["id"] for e in entries if e["name"].lower() == name.lower())


class TestCategories:
    def test_categories_come_back_in_order_and_can_be_reordered(self, client: TestClient):
        produce = add_category(client, "Produce")
        dairy = add_category(client, "Dairy")
        household = add_category(client, "Household")

        assert [c["name"] for c in client.get(f"{API}/categories").json()] == [
            "Produce",
            "Dairy",
            "Household",
        ]

        r = client.put(f"{API}/categories/order", json={"ordered_ids": [household, produce, dairy]})

        assert r.status_code == 200
        assert [c["name"] for c in r.json()] == ["Household", "Produce", "Dairy"]

    def test_a_duplicate_name_is_a_conflict(self, client: TestClient):
        add_category(client, "Bakery")

        r = client.post(
            f"{API}/categories", json={"name": "bakery", "icon": "🍞", "colour": "#000000"}
        )

        assert r.status_code == 409

    def test_a_bad_colour_is_rejected(self, client: TestClient):
        r = client.post(
            f"{API}/categories", json={"name": "Bakery", "icon": "🍞", "colour": "brown"}
        )

        assert r.status_code == 422

    def test_delete_reports_how_many_entries_became_uncategorised(self, client: TestClient):
        bakery = add_category(client, "Bakery")
        add_item(client, "bread")
        add_item(client, "rolls")
        for name in ("bread", "rolls"):
            client.patch(
                f"{API}/catalogue/{entry_id_for(client, name)}", json={"category_id": bakery}
            )

        preview = client.get(f"{API}/categories/{bakery}/removal-preview")
        assert preview.json() == {"entries_uncategorised": 2}

        r = client.delete(f"{API}/categories/{bakery}")

        assert r.status_code == 200
        assert r.json() == {"entries_uncategorised": 2}
        # Nothing vanished from the list.
        assert {i["name"] for i in client.get(f"{API}/items").json()} == {"bread", "rolls"}

    def test_an_unknown_category_is_a_404(self, client: TestClient):
        assert client.delete(f"{API}/categories/{uuid4()}").status_code == 404


class TestCatalogue:
    def test_adding_items_fills_the_catalogue(self, client: TestClient):
        add_item(client, "milk")
        add_item(client, "Milk")
        add_item(client, "bread")

        names = [e["name"] for e in client.get(f"{API}/catalogue").json()]

        assert names == ["bread", "milk"]

    def test_an_entry_can_be_categorised_and_given_stores(self, client: TestClient):
        dairy = add_category(client, "Dairy")
        lidl = add_store(client, "Lidl")
        add_item(client, "milk")
        entry = entry_id_for(client, "milk")

        r = client.patch(
            f"{API}/catalogue/{entry}", json={"category_id": dairy, "store_ids": [lidl]}
        )

        assert r.status_code == 200
        assert r.json()["category"]["name"] == "Dairy"
        assert [s["name"] for s in r.json()["stores"]] == ["Lidl"]

    def test_a_rename_collision_is_a_conflict_naming_the_existing_entry(self, client: TestClient):
        add_item(client, "milk")
        add_item(client, "mlik")
        milk = entry_id_for(client, "milk")
        typo = entry_id_for(client, "mlik")

        r = client.post(f"{API}/catalogue/{typo}/rename", json={"name": "Milk"})

        assert r.status_code == 409
        assert r.json()["existing_id"] == milk

    def test_merge_repoints_the_items_and_removes_the_source(
        self, client: TestClient, session: Session
    ):
        typo_item = add_item(client, "mlik")
        real_item = add_item(client, "milk")
        milk = entry_id_for(client, "milk")
        typo = entry_id_for(client, "mlik")

        r = client.post(f"{API}/catalogue/{typo}/merge", json={"into_id": milk})

        assert r.status_code == 200
        assert r.json()["id"] == milk
        assert [e["name"] for e in client.get(f"{API}/catalogue").json()] == ["milk"]
        linked = session.scalars(
            text("SELECT catalogue_entry_id::text FROM shopping_items WHERE id IN (:a, :b)"),
            {"a": typo_item["id"], "b": real_item["id"]},
        ).all()
        assert set(linked) == {milk}

    def test_removing_an_entry_in_use_is_a_conflict_naming_the_items(self, client: TestClient):
        add_item(client, "milk")
        entry = entry_id_for(client, "milk")

        r = client.delete(f"{API}/catalogue/{entry}")

        assert r.status_code == 409
        assert r.json()["items"] == ["milk"]

    def test_removing_an_unreferenced_entry_succeeds(self, client: TestClient):
        item = add_item(client, "stale")
        entry = entry_id_for(client, "stale")
        client.delete(f"{API}/items/{item['id']}")

        assert client.delete(f"{API}/catalogue/{entry}").status_code == 204
        assert client.get(f"{API}/catalogue").json() == []


class TestSuggestions:
    def test_the_spec_scenarios(self, client: TestClient):
        add_item(client, "milk")
        add_item(client, "mild cheddar")
        add_item(client, "bread")

        offered = [
            e["name"] for e in client.get(f"{API}/catalogue/suggest", params={"q": "mil"}).json()
        ]

        # Most recently used first: mild cheddar was added after milk.
        assert offered == ["mild cheddar", "milk"]

    def test_an_empty_query_offers_nothing(self, client: TestClient):
        add_item(client, "milk")

        assert client.get(f"{API}/catalogue/suggest", params={"q": ""}).json() == []

    def test_a_suggestion_carries_category_and_stores(self, client: TestClient):
        dairy = add_category(client, "Dairy")
        lidl = add_store(client, "Lidl")
        add_item(client, "milk")
        client.patch(
            f"{API}/catalogue/{entry_id_for(client, 'milk')}",
            json={"category_id": dairy, "store_ids": [lidl]},
        )

        [offered] = client.get(f"{API}/catalogue/suggest", params={"q": "mi"}).json()

        assert offered["category"]["name"] == "Dairy"
        assert [s["name"] for s in offered["stores"]] == ["Lidl"]


class TestItemRepresentation:
    def test_an_item_reports_its_derived_category(self, client: TestClient):
        dairy = add_category(client, "Dairy")
        add_item(client, "milk")
        client.patch(f"{API}/catalogue/{entry_id_for(client, 'milk')}", json={"category_id": dairy})

        [item] = client.get(f"{API}/items").json()

        assert item["category"]["name"] == "Dairy"
        assert item["catalogue_entry_id"] == entry_id_for(client, "milk")

    def test_an_uncategorised_item_reports_no_category_rather_than_failing(
        self, client: TestClient
    ):
        created = add_item(client, "mystery")

        assert created["category"] is None
        [item] = client.get(f"{API}/items").json()
        assert item["category"] is None

    def test_omitting_store_ids_takes_the_catalogue_prefill(self, client: TestClient):
        lidl = add_store(client, "Lidl")
        add_item(client, "ketchup", store_ids=[])
        client.patch(
            f"{API}/catalogue/{entry_id_for(client, 'ketchup')}", json={"store_ids": [lidl]}
        )

        prefilled = add_item(client, "ketchup")
        overridden = add_item(client, "ketchup", store_ids=[])

        assert [s["name"] for s in prefilled["stores"]] == ["Lidl"]
        assert overridden["stores"] == []

    def test_the_list_is_ordered_by_category_with_uncategorised_last(self, client: TestClient):
        produce = add_category(client, "Produce")
        dairy = add_category(client, "Dairy")
        for name in ("cheese", "mystery", "apples"):
            add_item(client, name)
        client.patch(
            f"{API}/catalogue/{entry_id_for(client, 'cheese')}", json={"category_id": dairy}
        )
        client.patch(
            f"{API}/catalogue/{entry_id_for(client, 'apples')}", json={"category_id": produce}
        )

        names = [i["name"] for i in client.get(f"{API}/items").json()]

        assert names == ["apples", "cheese", "mystery"]
