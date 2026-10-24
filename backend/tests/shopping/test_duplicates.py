"""The same thing is not written on the list twice."""

from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

API = "/api/shopping"


def create(client: TestClient, **fields: Any) -> Any:
    """Send a create over HTTP.

    Args:
        client: The test client.
        **fields: The request body.

    Returns:
        The response.
    """
    return client.post(f"{API}/items", json={"store_ids": [], **fields})


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
    store_id: str = r.json()["id"]
    return store_id


class TestDuplicateGuard:
    def test_milk_for_spar_is_refused_when_milk_for_lidl_is_on_the_list(self, client: TestClient):
        lidl = add_store(client, "Lidl")
        spar = add_store(client, "Spar")
        first = create(client, name="milk", store_ids=[lidl]).json()

        r = create(client, name="  Milk ", store_ids=[spar])

        assert r.status_code == 409
        assert r.json()["existing_id"] == first["id"]
        assert "milk" in r.json()["detail"].lower()
        listed = client.get(f"{API}/items").json()
        assert [(i["name"], [s["name"] for s in i["stores"]]) for i in listed] == [
            ("milk", ["Lidl"])
        ]

    def test_a_bought_item_does_not_block_adding_more(self, client: TestClient, member_id: UUID):
        first = create(client, name="milk").json()
        client.post(
            f"{API}/items/{first['id']}/purchase",
            headers={"X-Household-Member": str(member_id)},
        )

        assert create(client, name="milk").status_code == 201

    def test_a_replayed_create_still_returns_its_item(self, client: TestClient):
        item_id = str(uuid4())
        assert create(client, id=item_id, name="milk").status_code == 201

        replay = create(client, id=item_id, name="milk")

        assert replay.status_code == 201
        assert replay.json()["id"] == item_id

    def test_a_refused_add_does_not_touch_the_catalogue(self, client: TestClient):
        lidl = add_store(client, "Lidl")
        create(client, name="ketchup")
        entry_before = next(
            e for e in client.get(f"{API}/catalogue").json() if e["name"] == "ketchup"
        )
        category = client.post(
            f"{API}/categories", json={"name": "Sauces", "icon": "🥫", "colour": "#aa3311"}
        ).json()

        r = create(client, name="ketchup", store_ids=[lidl], category_id=category["id"])

        assert r.status_code == 409
        entry_after = next(
            e for e in client.get(f"{API}/catalogue").json() if e["name"] == "ketchup"
        )
        assert entry_after == entry_before
