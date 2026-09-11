"""Serving the built progressive web client next to the API.

The client is static files once built, so the API serves them from the same
origin — which also removes CORS from the picture rather than configuring it.

Any path that is not an API route returns the client's entry document, because
a client-side route reloaded in the browser would otherwise 404.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

CLIENT_ROOT = Path(__file__).resolve().parent / "client"
INDEX = CLIENT_ROOT / "index.html"

# Paths the client must never be served for: they belong to the API and its
# documentation, and answering them with HTML would turn a 404 into a
# confusing 200.
API_PREFIXES = ("/api", "/docs", "/redoc", "/openapi.json", "/health")


def client_is_built() -> bool:
    """Whether a built client is present to serve.

    Returns:
        True when the client's entry document exists.
    """
    return INDEX.is_file()


def mount_client(app: FastAPI) -> None:
    """Serve the built client, when one has been built into the image.

    In development the client runs from its own dev server, so a missing
    build is normal and must not stop the API from starting.

    Args:
        app: The application to mount the client on.
    """
    if not client_is_built():
        return

    app.mount(
        "/assets",
        StaticFiles(directory=CLIENT_ROOT / "assets", check_dir=False),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_client(full_path: str) -> FileResponse:
        """Return the client's entry document for any non-API path.

        Args:
            full_path: The requested path.

        Returns:
            The client's entry document.

        Raises:
            HTTPException: 404 when the path belongs to the API.
        """
        if any(f"/{full_path}".startswith(prefix) for prefix in API_PREFIXES):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        candidate = CLIENT_ROOT / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(INDEX)
