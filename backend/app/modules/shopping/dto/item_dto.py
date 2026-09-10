"""Wire representations for shopping list items."""

from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shopping.domain.item import ItemOrigin, ShoppingItem
from app.modules.shopping.domain.purchase import Purchase
from app.modules.shopping.domain.units import DEFAULT_QUANTITY, DEFAULT_UNIT, Unit
from app.modules.shopping.dto.store_dto import StoreResponse


class ItemCreateRequest(BaseModel):
    """A request to put an item on the shared list."""

    name: str = Field(min_length=1, max_length=200, examples=["ketchup"])
    quantity: float = Field(default=DEFAULT_QUANTITY, gt=0, examples=[2.0])
    unit: Unit = Field(default=DEFAULT_UNIT, examples=["piece"])
    store_ids: list[UUID] = Field(
        default_factory=list[UUID],
        description=(
            "Stores the item may be bought at. Leave empty to mean anywhere, "
            "which makes the item appear under every store's filter."
        ),
    )
    available_from: date | None = Field(
        default=None,
        description=(
            "The household-local date from which the item is worth buying. "
            "Until then it stays out of the shopping views."
        ),
        examples=["2026-09-15"],
    )


class ItemUpdateRequest(BaseModel):
    """A request to change an item. Unsupplied fields are left alone."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: float | None = Field(default=None, gt=0)
    unit: Unit | None = None
    store_ids: list[UUID] | None = Field(
        default=None,
        description=(
            "The item's complete new set of stores. An empty list clears them, "
            "making the item buyable anywhere."
        ),
    )
    available_from: date | None = None
    clear_available_from: bool = Field(
        default=False,
        description="Remove the availability date. Takes precedence over available_from.",
    )


class PurchaseResponse(BaseModel):
    """A recorded purchase as returned to a client."""

    member_id: UUID = Field(description="Who marked the item bought.")
    bought_at: datetime = Field(description="When it was marked, in UTC.")

    @classmethod
    def from_domain(cls, purchase: Purchase) -> Self:
        """Build the response from the domain purchase.

        Args:
            purchase: The domain purchase.

        Returns:
            The wire representation.
        """
        return cls(member_id=purchase.member_id, bought_at=purchase.bought_at)


class ItemResponse(BaseModel):
    """An item as returned to a client."""

    id: UUID
    name: str
    quantity: float
    unit: Unit
    stores: list[StoreResponse] = Field(
        description="The stores the item may be bought at; empty means anywhere."
    )
    available_from: date | None
    origin: ItemOrigin = Field(description="How the item came to be on the list.")
    purchase: PurchaseResponse | None = Field(
        default=None, description="The purchase, when the item has been bought."
    )

    @classmethod
    def from_domain(cls, item: ShoppingItem) -> Self:
        """Build the response from the domain item.

        Args:
            item: The domain item.

        Returns:
            The wire representation.
        """
        return cls(
            id=item.id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            stores=[StoreResponse.from_domain(store) for store in item.stores],
            available_from=item.available_from,
            origin=item.origin,
            purchase=(
                PurchaseResponse.from_domain(item.purchase) if item.purchase is not None else None
            ),
        )
