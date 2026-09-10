"""Wire representations for household members."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.household.domain.member import HouseholdMember


class MemberResponse(BaseModel):
    """A household member as returned to a client."""

    id: UUID = Field(description="The member's identifier.")
    name: str = Field(description="The member's display name.", examples=["Árpád"])

    @classmethod
    def from_domain(cls, member: HouseholdMember) -> Self:
        """Build the response from the domain member.

        Args:
            member: The domain member.

        Returns:
            The wire representation.
        """
        return cls(id=member.id, name=member.name)
