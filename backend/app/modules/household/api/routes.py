"""HTTP endpoints for household members."""

from fastapi import APIRouter

from app.modules.household.dto.member_dto import MemberResponse
from app.modules.household.providers import MemberServiceDep

router = APIRouter(prefix="/api/household", tags=["household"])


@router.get("/members", summary="List the household's members")
def list_members(members: MemberServiceDep) -> list[MemberResponse]:
    """Return the members a client can act as.

    Args:
        members: The member service.

    Returns:
        The household's members, ordered by name.
    """
    return [MemberResponse.from_domain(member) for member in members.list_members()]
