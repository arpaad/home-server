"""Business rules for the household's store registry."""

from uuid import UUID

from app.modules.shopping.domain.store import Store
from app.modules.shopping.errors import (
    DuplicateStoreNameError,
    EmptyStoreNameError,
    StoreInUseError,
    StoreNotFoundError,
)
from app.modules.shopping.repository.interfaces import (
    ShoppingItemRepository,
    StoreRepository,
)


class StoreService:
    """Adds, lists and removes the stores items may be assigned to."""

    def __init__(self, stores: StoreRepository, items: ShoppingItemRepository) -> None:
        """Bind the service to its repositories.

        Args:
            stores: The store registry.
            items: The shopping list, consulted before deleting a store.
        """
        self._stores = stores
        self._items = items

    def list_stores(self) -> list[Store]:
        """Return every store, ordered by name.

        Returns:
            The stores in the registry.
        """
        return self._stores.list_all()

    def get_store(self, store_id: UUID) -> Store:
        """Return one store.

        Args:
            store_id: The store to look up.

        Returns:
            The store.

        Raises:
            StoreNotFoundError: If no store has that id.
        """
        store = self._stores.get(store_id)
        if store is None:
            raise StoreNotFoundError(store_id)
        return store

    def add_store(self, name: str) -> Store:
        """Add a store, refusing a name that already exists.

        The duplicate check is case-insensitive, matching the unique index.
        Two stores differing only in case would split one shop's items across
        two filters, hiding half of them.

        Args:
            name: The store's name.

        Returns:
            The created store.

        Raises:
            EmptyStoreNameError: If the name is empty or only whitespace.
            DuplicateStoreNameError: If a store with that name exists.
        """
        cleaned = name.strip()
        if not cleaned:
            raise EmptyStoreNameError
        if self._stores.find_by_name(cleaned) is not None:
            raise DuplicateStoreNameError(cleaned)
        return self._stores.add(cleaned)

    def delete_store(self, store_id: UUID) -> None:
        """Delete a store, refusing while outstanding items reference it.

        Unassigning instead would turn a restricted item into an unrestricted
        one, making it appear in every store's view — the exact failure this
        capability exists to remove. The refusal names the items so that it is
        actionable rather than merely obstructive.

        Args:
            store_id: The store to delete.

        Raises:
            StoreNotFoundError: If no store has that id.
            StoreInUseError: If outstanding items still reference the store.
        """
        store = self._stores.get(store_id)
        if store is None:
            raise StoreNotFoundError(store_id)

        referencing = self._items.outstanding_names_referencing(store_id)
        if referencing:
            raise StoreInUseError(store_id, referencing)

        # Items already bought may still link to this store. The link means
        # "may be bought here", not "was bought here", so dropping it loses no
        # history — and without this the foreign key would refuse the delete
        # for a store whose outstanding items are all gone.
        self._items.detach_store_from_bought_items(store_id)
        self._stores.delete(store_id)
