"""Wire representations for catalogue entries."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shopping.domain.catalogue import CatalogueEntry
from app.modules.shopping.dto.category_dto import CategoryResponse
from app.modules.shopping.dto.store_dto import StoreResponse


class CatalogueEntryResponse(BaseModel):
    """A catalogue entry as returned to a client."""

    id: UUID
    name: str
    category: CategoryResponse | None = Field(default=None, description="None means uncategorised.")
    stores: list[StoreResponse] = Field(
        description="The stores this is usually bought at, offered as a prefill."
    )
    last_used_at: datetime | None = Field(
        default=None, description="When this name was last added to the list."
    )

    @classmethod
    def from_domain(cls, entry: CatalogueEntry) -> Self:
        """Build the response from the domain entry.

        Args:
            entry: The domain entry.

        Returns:
            The wire representation.
        """
        return cls(
            id=entry.id,
            name=entry.name,
            category=(
                CategoryResponse.from_domain(entry.category) if entry.category is not None else None
            ),
            stores=[StoreResponse.from_domain(store) for store in entry.stores],
            last_used_at=entry.last_used_at,
        )


class CatalogueEntryCreateRequest(BaseModel):
    """A request to add an entry directly, without adding an item."""

    name: str = Field(min_length=1, max_length=200, examples=["oat milk"])
    category_id: UUID | None = Field(default=None, description="None means uncategorised.")
    store_ids: list[UUID] = Field(
        default_factory=list[UUID], description="The stores this is usually bought at."
    )


class CatalogueEntryUpdateRequest(BaseModel):
    """A request to correct an entry. Unsupplied fields are left alone."""

    category_id: UUID | None = Field(
        default=None, description="A category to assign, or leave unset to keep the current one."
    )
    clear_category: bool = Field(
        default=False, description="Make the entry uncategorised. Takes precedence."
    )
    store_ids: list[UUID] | None = Field(
        default=None,
        description="The complete new set of remembered stores. Empty clears them.",
    )


class CatalogueEntryRenameRequest(BaseModel):
    """A request to rename an entry."""

    name: str = Field(min_length=1, max_length=200, examples=["milk"])


class CatalogueEntryMergeRequest(BaseModel):
    """A request to fold this entry into another."""

    into_id: UUID = Field(description="The entry that survives; this one's items move to it.")


class RenameCollisionResponse(BaseModel):
    """The body of a refused rename, offering the merge that is usually wanted."""

    detail: str
    existing_id: UUID = Field(description="The entry already carrying that name; merge into it.")


class EntryInUseResponse(BaseModel):
    """The body of a refused removal, naming the items that keep the entry in use."""

    detail: str
    items: list[str]
