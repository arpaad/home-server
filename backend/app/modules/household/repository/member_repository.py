"""Persistence for household members."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.household.domain.member import HouseholdMember
from app.modules.household.repository.member_orm import HouseholdMemberORM


class MemberRepository(Protocol):
    """Reads the household's members."""

    def list_all(self) -> list[HouseholdMember]:
        """Return every member, ordered by name.

        Returns:
            The household's members.
        """
        ...

    def get(self, member_id: UUID) -> HouseholdMember | None:
        """Return one member.

        Args:
            member_id: The member to look up.

        Returns:
            The member, or None when no member has that id.
        """
        ...


class SqlAlchemyMemberRepository:
    """Household members, backed by the ``household_members`` table."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to a session.

        Args:
            session: The session this repository reads through.
        """
        self._session = session

    def list_all(self) -> list[HouseholdMember]:
        """Return every member, ordered by name.

        Returns:
            The household's members.
        """
        rows = self._session.scalars(
            select(HouseholdMemberORM).order_by(HouseholdMemberORM.name)
        ).all()
        return [HouseholdMember(id=row.id, name=row.name) for row in rows]

    def get(self, member_id: UUID) -> HouseholdMember | None:
        """Return one member.

        Args:
            member_id: The member to look up.

        Returns:
            The member, or None when no member has that id.
        """
        row = self._session.get(HouseholdMemberORM, member_id)
        return HouseholdMember(id=row.id, name=row.name) if row else None
