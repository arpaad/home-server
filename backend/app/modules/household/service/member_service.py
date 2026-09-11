"""Business rules for household members."""

from uuid import UUID

from app.modules.household.domain.member import HouseholdMember
from app.modules.household.errors import UnknownMemberError
from app.modules.household.repository.member_repository import MemberRepository


class MemberService:
    """Lists members and resolves the one acting on a request."""

    def __init__(self, members: MemberRepository) -> None:
        """Bind the service to its repository.

        Args:
            members: The member repository.
        """
        self._members = members

    def list_members(self) -> list[HouseholdMember]:
        """Return every household member.

        Returns:
            The household's members, ordered by name.
        """
        return self._members.list_all()

    def resolve_acting_member(self, member_id: UUID | None) -> HouseholdMember:
        """Resolve who is acting, refusing an absent or unknown member.

        This release does not authenticate the caller; it only insists on
        knowing which member to attribute a purchase to. See the deferred
        authentication change.

        Args:
            member_id: The claimed member id, or None when none was sent.

        Returns:
            The acting member.

        Raises:
            UnknownMemberError: If no id was sent, or it matches no member.
        """
        if member_id is None:
            raise UnknownMemberError(None)

        member = self._members.get(member_id)
        if member is None:
            raise UnknownMemberError(member_id)
        return member
