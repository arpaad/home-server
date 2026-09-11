"""Dependency wiring for the shopping module."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.modules.shopping.repository.catalogue_repository import SqlAlchemyCatalogueRepository
from app.modules.shopping.repository.category_repository import SqlAlchemyCategoryRepository
from app.modules.shopping.repository.item_repository import SqlAlchemyShoppingItemRepository
from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository
from app.modules.shopping.service.catalogue_service import CatalogueService
from app.modules.shopping.service.category_service import CategoryService
from app.modules.shopping.service.shopping_list_service import ShoppingListService
from app.modules.shopping.service.store_service import StoreService

# scope="function": the session's exit code — the COMMIT — runs after the
# path function returns but BEFORE the response is sent. With the default
# request scope it runs after the response, so a client that reads straight
# after a 200 can see the world as it was before the write. That was a real
# bug: the UI refetched on success and showed stale data until a reload.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Everything below depends on the session, so it has to share its scope: a
# request-scoped dependency may not depend on a function-scoped one.


def _catalogue_service(session: Session) -> CatalogueService:
    """Build the catalogue service on a session.

    Args:
        session: The request's database session.

    Returns:
        A catalogue service bound to that session.
    """
    return CatalogueService(
        SqlAlchemyCatalogueRepository(session),
        SqlAlchemyCategoryRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def get_catalogue_service(session: SessionDep) -> Iterator[CatalogueService]:
    """Provide the catalogue service for one request.

    Args:
        session: The request's database session.

    Yields:
        A catalogue service bound to that session.
    """
    yield _catalogue_service(session)


def get_category_service(session: SessionDep) -> Iterator[CategoryService]:
    """Provide the category service for one request.

    Args:
        session: The request's database session.

    Yields:
        A category service bound to that session.
    """
    yield CategoryService(SqlAlchemyCategoryRepository(session))


def get_shopping_list_service(
    session: SessionDep, settings: SettingsDep
) -> Iterator[ShoppingListService]:
    """Provide the shopping list service for one request.

    Args:
        session: The request's database session.
        settings: The application settings, carrying the household's zone.

    Yields:
        A shopping list service bound to that session.
    """
    yield ShoppingListService(
        SqlAlchemyShoppingItemRepository(session),
        SqlAlchemyStoreRepository(session),
        _catalogue_service(session),
        settings.timezone,
    )


def get_store_service(session: SessionDep) -> Iterator[StoreService]:
    """Provide the store service for one request.

    Args:
        session: The request's database session.

    Yields:
        A store service bound to that session.
    """
    yield StoreService(
        SqlAlchemyStoreRepository(session),
        SqlAlchemyShoppingItemRepository(session),
    )


ShoppingListServiceDep = Annotated[
    ShoppingListService, Depends(get_shopping_list_service, scope="function")
]
StoreServiceDep = Annotated[StoreService, Depends(get_store_service, scope="function")]
CatalogueServiceDep = Annotated[CatalogueService, Depends(get_catalogue_service, scope="function")]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service, scope="function")]
