"""A member of the household."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.household.errors import EmptyMemberNameError


@dataclass(frozen=True, slots=True)
class HouseholdMember:
    """A person in the household, used to attribute purchases.

    Members are identified, not authenticated. This release is reachable from
    the household network only; see the authentication change.
    """

    id: UUID
    name: str

    def __post_init__(self) -> None:
        """Reject a member whose name carries no content.

        Raises:
            EmptyMemberNameError: If the name is empty or only whitespace.
        """
        if not self.name.strip():
            raise EmptyMemberNameError
