"""Errors the household module raises deliberately."""

from uuid import UUID

from app.core.errors import HomeError


class HouseholdError(HomeError):
    """Base class for every deliberate refusal in the household module."""


class EmptyMemberNameError(HouseholdError):
    """A member was given a name that is empty or only whitespace."""

    def __init__(self) -> None:
        """State the rule that was broken."""
        super().__init__("a member name must contain at least one non-whitespace character")


class UnknownMemberError(HouseholdError):
    """The acting member could not be resolved.

    This release does not authenticate members, but it does insist on knowing
    which one is acting, so that a purchase is always attributable.
    """

    def __init__(self, member_id: UUID | str | None) -> None:
        """Record the identifier that matched no member.

        Args:
            member_id: The supplied identifier, or None when none was sent.
        """
        if member_id is None:
            super().__init__("no acting household member was supplied")
        else:
            super().__init__(f"no household member with id {member_id}")
        self.member_id = member_id
