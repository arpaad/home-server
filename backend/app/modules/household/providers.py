"""Dependency wiring for the household module."""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.household.domain.member import HouseholdMember
from app.modules.household.repository.member_repository import SqlAlchemyMemberRepository
from app.modules.household.service.member_service import MemberService

SessionDep = Annotated[Session, Depends(get_session)]


def get_member_service(session: SessionDep) -> Iterator[MemberService]:
    """Provide the member service for one request.

    Args:
        session: The request's database session.

    Yields:
        A member service bound to that session.
    """
    yield MemberService(SqlAlchemyMemberRepository(session))


MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]


def get_current_member(
    members: MemberServiceDep,
    x_household_member: Annotated[
        UUID | None,
        Header(
            description=(
                "Identifier of the member performing the action. This release "
                "TRUSTS THIS HEADER COMPLETELY: it identifies the caller but "
                "does not authenticate them, and the service is intended to be "
                "reachable only from the household's own network. The "
                "authentication change replaces the body of this dependency, "
                "and no endpoint changes."
            ),
        ),
    ] = None,
) -> HouseholdMember:
    """Resolve the member acting on this request.

    Every endpoint that attributes an action depends on this one function, so
    that adding authentication later is a change in one place.

    Args:
        members: The member service.
        x_household_member: The claimed member id, from the request header.

    Returns:
        The acting member.
    """
    return members.resolve_acting_member(x_household_member)


CurrentMember = Annotated[HouseholdMember, Depends(get_current_member)]
