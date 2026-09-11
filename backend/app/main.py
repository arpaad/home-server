"""The H.O.M.E. application."""

from fastapi import FastAPI

from app.core.error_handlers import register_error_handlers
from app.router import api_router
from app.web import mount_client

app = FastAPI(
    title="H.O.M.E.",
    description=(
        "Household Operations, Management & Essentials.\n\n"
        "**This release has no authentication.** Members are identified so "
        "that purchases can be attributed, but not authenticated. It is "
        "intended to be reachable only from the household's own network and "
        "must not be exposed to the internet."
    ),
    version="0.1.0",
)

register_error_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["ops"], summary="Liveness probe")
def health() -> dict[str, str]:
    """Report that the process is up.

    Returns:
        A small status document.
    """
    return {"status": "ok", "message": "H.O.M.E. server running"}


# Mounted last: its catch-all route must not shadow the API.
mount_client(app)
