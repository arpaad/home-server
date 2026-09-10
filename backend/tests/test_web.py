"""The API serves the built client, without shadowing its own routes.

Reloading the page on a client-side route must return the app, not a 404 —
which is the failure mode of serving a single-page client from an API.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import web


@pytest.fixture
def built_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Provide a client for an app with a stand-in built client mounted.

    Args:
        tmp_path: A temporary directory standing in for the build output.
        monkeypatch: Used to point the module at that directory.

    Returns:
        A test client for the mounted app.
    """
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>H.O.M.E.</title>")
    (tmp_path / "manifest.webmanifest").write_text('{"name":"H.O.M.E."}')

    monkeypatch.setattr(web, "CLIENT_ROOT", tmp_path)
    monkeypatch.setattr(web, "INDEX", tmp_path / "index.html")

    app = FastAPI()

    @app.get("/api/shopping/items")
    def items() -> list[str]:
        return []

    web.mount_client(app)
    return TestClient(app)


def test_the_entry_document_is_served_at_the_root(built_client: TestClient):
    response = built_client.get("/")

    assert response.status_code == 200
    assert "H.O.M.E." in response.text


def test_reloading_a_client_side_route_returns_the_app_not_a_404(built_client: TestClient):
    response = built_client.get("/shopping/lidl")

    assert response.status_code == 200
    assert "<!doctype html>" in response.text


def test_a_real_client_file_is_served_as_itself(built_client: TestClient):
    response = built_client.get("/manifest.webmanifest")

    assert response.status_code == 200
    assert "H.O.M.E." in response.text


def test_the_catch_all_does_not_shadow_the_api(built_client: TestClient):
    response = built_client.get("/api/shopping/items")

    assert response.status_code == 200
    assert response.json() == []


def test_an_unknown_api_path_is_a_404_not_the_client(built_client: TestClient):
    response = built_client.get("/api/nope")

    assert response.status_code == 404
    assert "<!doctype html>" not in response.text


def test_nothing_is_mounted_when_the_client_is_not_built(monkeypatch: pytest.MonkeyPatch):
    # In development the client runs from its own dev server; a missing build
    # must not stop the API from starting.
    monkeypatch.setattr(web, "INDEX", Path("/nonexistent/index.html"))
    app = FastAPI()

    web.mount_client(app)

    assert TestClient(app).get("/").status_code == 404
