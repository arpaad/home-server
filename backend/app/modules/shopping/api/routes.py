"""HTTP endpoints for the shared shopping list.

These routes translate HTTP and nothing else: every rule lives in the service
layer, and the layering test enforces that this module never reaches a
repository directly.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.modules.household.providers import CurrentMember
from app.modules.shopping.dto.item_dto import (
    ItemCreateRequest,
    ItemResponse,
    ItemUpdateRequest,
    PurchaseResponse,
)
from app.modules.shopping.dto.store_dto import (
    StoreCreateRequest,
    StoreInUseResponse,
    StoreResponse,
)
from app.modules.shopping.providers import ShoppingListServiceDep, StoreServiceDep

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


# ---- items ----


@router.get("/items", summary="List outstanding items")
def list_items(
    shopping: ShoppingListServiceDep,
    store_id: Annotated[
        UUID | None,
        Query(
            description=(
                "Show only what can be bought at this store. Items with no "
                "store assigned appear under every store."
            ),
        ),
    ] = None,
    include_upcoming: Annotated[
        bool,
        Query(
            description=(
                "Include items whose availability date has not arrived yet. "
                "Use this for reviewing the whole list at home."
            ),
        ),
    ] = False,
) -> list[ItemResponse]:
    """Return the outstanding items, optionally filtered to one store.

    Args:
        shopping: The shopping list service.
        store_id: Restrict to items buyable at this store.
        include_upcoming: Include items not yet available.

    Returns:
        The matching items, ordered by name.
    """
    items = shopping.list_items(store_id=store_id, include_upcoming=include_upcoming)
    return [ItemResponse.from_domain(item) for item in items]


@router.get("/items/{item_id}", summary="Read one item")
def read_item(item_id: UUID, shopping: ShoppingListServiceDep) -> ItemResponse:
    """Return one item.

    Args:
        item_id: The item to read.
        shopping: The shopping list service.

    Returns:
        The item.
    """
    return ItemResponse.from_domain(shopping.get_item(item_id))


@router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to the shared list",
)
def create_item(payload: ItemCreateRequest, shopping: ShoppingListServiceDep) -> ItemResponse:
    """Put an item on the list and return it.

    Args:
        payload: The item to create.
        shopping: The shopping list service.

    Returns:
        The created item, including its generated id.
    """
    item = shopping.add_item(
        name=payload.name,
        quantity=payload.quantity,
        unit=payload.unit,
        store_ids=payload.store_ids,
        available_from=payload.available_from,
    )
    return ItemResponse.from_domain(item)


@router.patch("/items/{item_id}", summary="Change an item")
def update_item(
    item_id: UUID, payload: ItemUpdateRequest, shopping: ShoppingListServiceDep
) -> ItemResponse:
    """Change an item, leaving unsupplied fields alone.

    Args:
        item_id: The item to change.
        payload: The fields to change.
        shopping: The shopping list service.

    Returns:
        The updated item.
    """
    item = shopping.edit_item(
        item_id,
        name=payload.name,
        quantity=payload.quantity,
        unit=payload.unit,
        store_ids=payload.store_ids,
        available_from=payload.available_from,
        clear_available_from=payload.clear_available_from,
    )
    return ItemResponse.from_domain(item)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item nobody wants any more",
)
def delete_item(item_id: UUID, shopping: ShoppingListServiceDep) -> Response:
    """Take an item off the list without recording a purchase.

    Args:
        item_id: The item to remove.
        shopping: The shopping list service.

    Returns:
        An empty 204 response.
    """
    shopping.remove_item(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- purchases ----


@router.post(
    "/items/{item_id}/purchase",
    summary="Mark an item as bought",
)
def buy_item(
    item_id: UUID, member: CurrentMember, shopping: ShoppingListServiceDep
) -> PurchaseResponse:
    """Record that the acting member bought an item.

    Idempotent: marking an already-bought item returns the existing purchase,
    so both members marking the same item at once is harmless.

    Args:
        item_id: The item that was bought.
        member: The acting member.
        shopping: The shopping list service.

    Returns:
        The purchase recorded against the item.
    """
    return PurchaseResponse.from_domain(shopping.mark_bought(item_id, member.id))


@router.delete(
    "/items/{item_id}/purchase",
    summary="Undo a purchase made in error",
)
def undo_purchase(item_id: UUID, shopping: ShoppingListServiceDep) -> ItemResponse:
    """Return an item to the outstanding list.

    Args:
        item_id: The item to restore.
        shopping: The shopping list service.

    Returns:
        The item, outstanding again.
    """
    return ItemResponse.from_domain(shopping.undo_purchase(item_id))


# ---- stores ----


@router.get("/stores", summary="List the household's stores")
def list_stores(stores: StoreServiceDep) -> list[StoreResponse]:
    """Return every store items may be assigned to.

    Args:
        stores: The store service.

    Returns:
        The stores, ordered by name.
    """
    return [StoreResponse.from_domain(store) for store in stores.list_stores()]


@router.post(
    "/stores",
    status_code=status.HTTP_201_CREATED,
    summary="Add a store",
)
def create_store(payload: StoreCreateRequest, stores: StoreServiceDep) -> StoreResponse:
    """Add a store to the registry and return it.

    Args:
        payload: The store to create.
        stores: The store service.

    Returns:
        The created store.
    """
    return StoreResponse.from_domain(stores.add_store(payload.name))


@router.delete(
    "/stores/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a store",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": StoreInUseResponse,
            "description": "Outstanding items still reference this store.",
        }
    },
)
def delete_store(store_id: UUID, stores: StoreServiceDep) -> Response:
    """Delete a store, refusing while outstanding items reference it.

    Args:
        store_id: The store to delete.
        stores: The store service.

    Returns:
        An empty 204 response.
    """
    stores.delete_store(store_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
