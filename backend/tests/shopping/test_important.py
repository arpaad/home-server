"""An important item is the item's own flag, and arranges without filtering."""

from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from app.modules.shopping.domain.item import ShoppingItem

API = "/api/shopping"


def create(client: TestClient, **fields: Any) -> dict[str, Any]:
    """Create an item over HTTP.

    Args:
        client: The test client.
        **fields: The request body.

    Returns:
        The created item.
    """
    r = client.post(f"{API}/items", json={"store_ids": [], **fields})
    assert r.status_code == 201, r.text
    body: dict[str, Any] = r.json()
    return body


def edit(client: TestClient, item_id: str, **fields: Any) -> dict[str, Any]:
    """Edit an item over HTTP.

    Args:
        client: The test client.
        item_id: The item to edit.
        **fields: The request body.

    Returns:
        The edit response: the item and whether the edit applied.
    """
    r = client.patch(f"{API}/items/{item_id}", json=fields)
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def listed(client: TestClient, **params: Any) -> list[dict[str, Any]]:
    """List items over HTTP.

    Args:
        client: The test client.
        **params: Query parameters.

    Returns:
        The items.
    """
    r = client.get(f"{API}/items", params=params)
    assert r.status_code == 200, r.text
    body: list[dict[str, Any]] = r.json()
    return body


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


def test_a_domain_item_is_not_important_by_default():
    assert ShoppingItem(id=UUID(int=1), name="milk").important is False


class TestFlagging:
    def test_an_item_is_not_important_unless_flagged(self, client: TestClient):
        create(client, name="milk")

        assert listed(client)[0]["important"] is False

    def test_an_item_can_be_added_important(self, client: TestClient):
        create(client, name="nappies", important=True)

        assert listed(client)[0]["important"] is True

    def test_an_edit_sets_and_clears_the_flag_and_nothing_else(self, client: TestClient):
        item = create(client, name="nappies", quantity=2)

        flagged = edit(client, item["id"], important=True)["item"]
        assert flagged["important"] is True
        assert flagged["quantity"] == 2

        # An edit that does not mention the flag leaves it alone.
        renamed = edit(client, item["id"], name="pelenka")["item"]
        assert renamed["important"] is True

        cleared = edit(client, item["id"], important=False)["item"]
        assert cleared["important"] is False
        assert cleared["name"] == "pelenka"

    def test_an_older_edit_does_not_change_the_flag(self, client: TestClient):
        item = create(client, name="nappies")
        edit(client, item["id"], important=True, edited_at="2026-10-24T10:05:00+02:00")

        older = edit(client, item["id"], important=False, edited_at="2026-10-24T10:00:00+02:00")

        assert older["applied"] is False
        assert listed(client)[0]["important"] is True

    def test_importance_is_not_remembered_for_the_next_item(
        self, client: TestClient, member_id: UUID
    ):
        first = create(client, name="nappies", important=True)
        bought = client.post(
            f"{API}/items/{first['id']}/purchase", headers={"X-Household-Member": str(member_id)}
        )
        assert bought.status_code == 200, bought.text
        client.post(f"{API}/items/clear-bought")

        again = create(client, name="nappies")

        assert again["catalogue_entry_id"] == first["catalogue_entry_id"]
        assert again["important"] is False


class TestImportanceDoesNotChangeMembership:
    def test_an_important_item_for_lidl_is_not_in_spar(self, client: TestClient):
        lidl = add_store(client, "Lidl")
        spar = add_store(client, "Spar")
        create(client, name="nappies", store_ids=[lidl], important=True)
        create(client, name="milk")

        assert [i["name"] for i in listed(client, store_id=spar)] == ["milk"]
        assert sorted(i["name"] for i in listed(client, store_id=lidl)) == ["milk", "nappies"]
