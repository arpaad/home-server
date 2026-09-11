"""Wire representations for categories."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shopping.domain.category import Category


class CategoryCreateRequest(BaseModel):
    """A request to add a category."""

    name: str = Field(min_length=1, max_length=60, examples=["Bakery"])
    icon: str = Field(min_length=1, max_length=16, description="An emoji.", examples=["🥖"])
    colour: str = Field(
        pattern=r"^#[0-9a-fA-F]{6}$", description="Hex colour, #rrggbb.", examples=["#c48a3a"]
    )


class CategoryUpdateRequest(BaseModel):
    """A request to change a category. Unsupplied fields are left alone."""

    name: str | None = Field(default=None, min_length=1, max_length=60)
    icon: str | None = Field(default=None, min_length=1, max_length=16)
    colour: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class CategoryReorderRequest(BaseModel):
    """The complete household-wide order."""

    ordered_ids: list[UUID] = Field(
        description="Every category id, in the order groups should appear."
    )


class CategoryResponse(BaseModel):
    """A category as returned to a client."""

    id: UUID
    name: str
    icon: str
    colour: str
    position: int = Field(description="Sort key for the household-wide order.")

    @classmethod
    def from_domain(cls, category: Category) -> Self:
        """Build the response from the domain category.

        Args:
            category: The domain category.

        Returns:
            The wire representation.
        """
        return cls(
            id=category.id,
            name=category.name,
            icon=category.icon,
            colour=category.colour,
            position=category.position,
        )


class CategoryRemovalResponse(BaseModel):
    """What removing a category did."""

    entries_uncategorised: int = Field(
        description="How many catalogue entries lost their category."
    )


class CategoryRemovalPreview(BaseModel):
    """What removing a category would do, for a confirmation prompt."""

    entries_uncategorised: int = Field(
        description="How many catalogue entries would lose their category."
    )
