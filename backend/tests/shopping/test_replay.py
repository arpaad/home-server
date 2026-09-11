"""Every list operation is safe to replay from an offline queue.

A queued change may reach the server twice (response lost, then retried),
late (a phone syncing hours after the edit), or after the other phone has
already acted. None of those may duplicate, overwrite a newer edit, or fail.
"""

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

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


def listed(client: TestClient) -> list[dict[str, Any]]:
    """List items over HTTP.

    Args:
        client: The test client.

    Returns:
        The items.
    """
    body: list[dict[str, Any]] = client.get(f"{API}/items").json()
    return body


class TestCreateIsIdempotent:
    def test_the_same_create_sent_twice_lands_once(self, client: TestClient):
        item_id = str(uuid4())

        first = create(client, id=item_id, name="ketchup")
        second = create(client, id=item_id, name="ketchup")

        assert first["id"] == item_id
        assert second["id"] == item_id
        assert [i["name"] for i in listed(client)] == ["ketchup"]

    def test_a_replayed_create_returns_the_item_as_it_now_is(self, client: TestClient):
        # The item may have been edited between the original create and its
        # replay; the replay must not reset it.
        item_id = str(uuid4())
        create(client, id=item_id, name="milk", quantity=1)
        client.patch(f"{API}/items/{item_id}", json={"quantity": 3})

        replayed = create(client, id=item_id, name="milk", quantity=1)

        assert replayed["quantity"] == 3

    def test_a_create_without_an_id_still_gets_one(self, client: TestClient):
        created = create(client, name="bread")

        assert created["id"]
        assert [i["name"] for i in listed(client)] == ["bread"]


class TestLaterEditWins:
    def test_an_older_edit_arriving_later_is_not_applied(self, client: TestClient):
        item = create(client, name="milk", quantity=1)

        newer = client.patch(
            f"{API}/items/{item['id']}",
            json={"quantity": 3, "edited_at": "2026-09-11T10:05:00+02:00"},
        )
        older = client.patch(
            f"{API}/items/{item['id']}",
            json={"quantity": 2, "edited_at": "2026-09-11T10:00:00+02:00"},
        )

        assert newer.json()["applied"] is True
        assert older.status_code == 200
        assert older.json()["applied"] is False
        assert older.json()["item"]["quantity"] == 3
        assert listed(client)[0]["quantity"] == 3

    def test_a_newer_edit_applies_over_an_older_one(self, client: TestClient):
        item = create(client, name="milk", quantity=1)
        client.patch(
            f"{API}/items/{item['id']}",
            json={"quantity": 2, "edited_at": "2026-09-11T10:00:00+02:00"},
        )

        r = client.patch(
            f"{API}/items/{item['id']}",
            json={"quantity": 3, "edited_at": "2026-09-11T10:05:00+02:00"},
        )

        assert r.json()["applied"] is True
        assert listed(client)[0]["quantity"] == 3

    def test_an_edit_without_a_time_always_applies(self, client: TestClient):
        item = create(client, name="milk", quantity=1)
        client.patch(
            f"{API}/items/{item['id']}",
            json={"quantity": 3, "edited_at": "2026-09-11T10:05:00+02:00"},
        )

        r = client.patch(f"{API}/items/{item['id']}", json={"quantity": 5})

        assert r.json()["applied"] is True
        assert listed(client)[0]["quantity"] == 5

    def test_the_response_carries_the_item_and_the_flag(self, client: TestClient):
        item = create(client, name="milk")

        r = client.patch(f"{API}/items/{item['id']}", json={"name": "oat milk"})

        assert set(r.json()) == {"item", "applied"}
        assert r.json()["item"]["name"] == "oat milk"


class TestRemoveIsTolerant:
    def test_removing_a_missing_item_is_a_204(self, client: TestClient):
        assert client.delete(f"{API}/items/{uuid4()}").status_code == 204

    def test_removing_twice_is_a_204_both_times(self, client: TestClient):
        item = create(client, name="milk")

        assert client.delete(f"{API}/items/{item['id']}").status_code == 204
        assert client.delete(f"{API}/items/{item['id']}").status_code == 204
        assert listed(client) == []
