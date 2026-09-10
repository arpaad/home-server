"""Errors the shopping module raises deliberately.

Messages live on the classes so that a raise site stays short and every
occurrence of the same refusal reads identically to a caller.
"""

from uuid import UUID

from app.core.errors import HomeError


class ShoppingError(HomeError):
    """Base class for every deliberate refusal in the shopping module."""


class EmptyItemNameError(ShoppingError):
    """An item was given a name that is empty or only whitespace."""

    def __init__(self) -> None:
        """State the rule that was broken."""
        super().__init__("an item name must contain at least one non-whitespace character")


class NonPositiveQuantityError(ShoppingError):
    """An item was given a quantity of zero or less."""

    def __init__(self, quantity: float) -> None:
        """Record the rejected quantity.

        Args:
            quantity: The quantity that was not greater than zero.
        """
        super().__init__(f"an item quantity must be greater than zero, got {quantity}")
        self.quantity = quantity


class EmptyStoreNameError(ShoppingError):
    """A store was given a name that is empty or only whitespace."""

    def __init__(self) -> None:
        """State the rule that was broken."""
        super().__init__("a store name must contain at least one non-whitespace character")


class ItemNotFoundError(ShoppingError):
    """The referenced item is not on the list."""

    def __init__(self, item_id: UUID) -> None:
        """Record which item could not be found.

        Args:
            item_id: The identifier that matched no item.
        """
        super().__init__(f"no shopping item with id {item_id}")
        self.item_id = item_id


class StoreNotFoundError(ShoppingError):
    """The referenced store is not in the registry."""

    def __init__(self, store_id: UUID) -> None:
        """Record which store could not be found.

        Args:
            store_id: The identifier that matched no store.
        """
        super().__init__(f"no store with id {store_id}")
        self.store_id = store_id


class UnknownStoresError(ShoppingError):
    """An item referenced stores that do not exist in the registry.

    Assigning a store that does not exist is refused rather than ignored: a
    silently dropped store would hide the item from that store's view, which
    is the failure this capability exists to prevent.
    """

    def __init__(self, store_ids: frozenset[UUID]) -> None:
        """Record which stores were unknown.

        Args:
            store_ids: The identifiers that matched no store.
        """
        listed = ", ".join(sorted(str(store_id) for store_id in store_ids))
        super().__init__(f"no store with id {listed}")
        self.store_ids = store_ids


class DuplicateStoreNameError(ShoppingError):
    """A store with this name already exists, compared case-insensitively."""

    def __init__(self, name: str) -> None:
        """Record the name that collided.

        Args:
            name: The store name that already exists.
        """
        super().__init__(f"a store named {name!r} already exists")
        self.name = name


class StoreInUseError(ShoppingError):
    """A store cannot be deleted while outstanding items still reference it.

    Unassigning the store instead would turn a restricted item into an
    unrestricted one, making it appear in every store's view.
    """

    def __init__(self, store_id: UUID, item_names: tuple[str, ...]) -> None:
        """Record the store and the items that keep it in use.

        Args:
            store_id: The store that cannot be deleted.
            item_names: Names of the outstanding items referencing it.
        """
        listed = ", ".join(item_names)
        super().__init__(f"store {store_id} is still referenced by outstanding items: {listed}")
        self.store_id = store_id
        self.item_names = item_names
