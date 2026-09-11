"""Wire representations for stores."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shopping.domain.store import Store


class StoreCreateRequest(BaseModel):
    """A request to add a store to the registry."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="The store's name; unique in the household, ignoring case.",
        examples=["Lidl"],
    )


class StoreResponse(BaseModel):
    """A store as returned to a client."""

    id: UUID = Field(description="The store's identifier.")
    name: str = Field(description="The store's name.", examples=["Lidl"])

    @classmethod
    def from_domain(cls, store: Store) -> Self:
        """Build the response from the domain store.

        Args:
            store: The domain store.

        Returns:
            The wire representation.
        """
        return cls(id=store.id, name=store.name)


class StoreInUseResponse(BaseModel):
    """The body of the refusal to delete a store that is still in use."""

    detail: str = Field(description="Why the store could not be deleted.")
    items: list[str] = Field(
        description="Outstanding items still assigned to the store.",
        examples=[["bread", "ketchup"]],
    )
