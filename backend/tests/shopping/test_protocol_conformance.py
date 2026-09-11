"""The SQLAlchemy repositories satisfy the Protocols the service depends on.

These assignments are the test: pyright rejects the file if an implementation
drifts from its interface, so the service layer's dependency stays honest
without any runtime assertion.
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.modules.shopping.repository.catalogue_repository import SqlAlchemyCatalogueRepository
from app.modules.shopping.repository.category_repository import SqlAlchemyCategoryRepository
from app.modules.shopping.repository.interfaces import (
    CatalogueRepository,
    CategoryRepository,
    ShoppingItemRepository,
    StoreRepository,
)
from app.modules.shopping.repository.item_repository import SqlAlchemyShoppingItemRepository
from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository


def test_the_sqlalchemy_implementations_satisfy_their_protocols(session: Session):
    stores: StoreRepository = SqlAlchemyStoreRepository(session)
    items: ShoppingItemRepository = SqlAlchemyShoppingItemRepository(session)
    categories: CategoryRepository = SqlAlchemyCategoryRepository(session)
    catalogue: CatalogueRepository = SqlAlchemyCatalogueRepository(session)

    assert stores.list_all() == []
    assert items.outstanding_names_referencing(uuid4()) == ()
    assert categories.list_all() == []
    assert catalogue.suggest("x", limit=1) == []
