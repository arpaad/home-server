"""Translation from domain errors to HTTP responses.

Services raise domain errors and know nothing about HTTP; this module is the
single place that decides what each one means on the wire, so two endpoints
cannot answer the same refusal with different status codes.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.modules.household.errors import UnknownMemberError
from app.modules.shopping.errors import (
    CategoryNotFoundError,
    DuplicateCategoryNameError,
    DuplicateEntryNameError,
    DuplicateStoreNameError,
    EmptyCategoryIconError,
    EmptyCategoryNameError,
    EmptyEntryNameError,
    EmptyItemNameError,
    EmptyStoreNameError,
    EntryInUseError,
    EntryNotFoundError,
    InvalidCategoryColourError,
    ItemNotFoundError,
    MergeIntoSelfError,
    NonPositiveQuantityError,
    StoreInUseError,
    StoreNotFoundError,
    UnknownStoresError,
)

STATUS_BY_ERROR: dict[type[Exception], int] = {
    ItemNotFoundError: status.HTTP_404_NOT_FOUND,
    StoreNotFoundError: status.HTTP_404_NOT_FOUND,
    CategoryNotFoundError: status.HTTP_404_NOT_FOUND,
    EntryNotFoundError: status.HTTP_404_NOT_FOUND,
    EmptyItemNameError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EmptyStoreNameError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EmptyCategoryNameError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EmptyCategoryIconError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidCategoryColourError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EmptyEntryNameError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NonPositiveQuantityError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    UnknownStoresError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    MergeIntoSelfError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    DuplicateStoreNameError: status.HTTP_409_CONFLICT,
    DuplicateCategoryNameError: status.HTTP_409_CONFLICT,
    # Identified, not authenticated: a missing header is a malformed request,
    # not a failed login.
    UnknownMemberError: status.HTTP_400_BAD_REQUEST,
}


def _plain(status_code: int):
    """Build a handler answering with the error's message.

    Args:
        status_code: The status to answer with.

    Returns:
        A Starlette exception handler.
    """

    def handle(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handle


def _store_in_use(_: Request, exc: Exception) -> JSONResponse:
    """Answer a refused store deletion, naming the items in the way.

    A refusal that does not say which items block it is merely obstructive.

    Args:
        _: The request, unused.
        exc: The raised StoreInUseError.

    Returns:
        A 409 carrying the referencing items' names.
    """
    names = exc.item_names if isinstance(exc, StoreInUseError) else ()
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc), "items": list(names)},
    )


def _entry_in_use(_: Request, exc: Exception) -> JSONResponse:
    """Answer a refused entry removal, naming the items in the way.

    Args:
        _: The request, unused.
        exc: The raised EntryInUseError.

    Returns:
        A 409 carrying the referring items' names.
    """
    names = exc.item_names if isinstance(exc, EntryInUseError) else ()
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc), "items": list(names)},
    )


def _rename_collision(_: Request, exc: Exception) -> JSONResponse:
    """Answer a refused rename with the entry to merge into instead.

    A member who hits this almost always wants the merge, so the response
    carries what the client needs to offer it in one tap.

    Args:
        _: The request, unused.
        exc: The raised DuplicateEntryNameError.

    Returns:
        A 409 carrying the colliding entry's id.
    """
    existing = str(exc.existing_id) if isinstance(exc, DuplicateEntryNameError) else None
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc), "existing_id": existing},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Install the handlers translating domain errors into responses.

    Args:
        app: The application to install them on.
    """
    for error, status_code in STATUS_BY_ERROR.items():
        app.add_exception_handler(error, _plain(status_code))

    app.add_exception_handler(StoreInUseError, _store_in_use)
    app.add_exception_handler(EntryInUseError, _entry_in_use)
    app.add_exception_handler(DuplicateEntryNameError, _rename_collision)
