"""Seed the data a fresh database needs before the app is usable.

Run by `make seed`, and safe to run repeatedly: seeding inserts only the
members that are missing, so it never duplicates a member or renames one.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.household.repository.member_orm import HouseholdMemberORM


def seed_household_members(session: Session, names: tuple[str, ...]) -> list[str]:
    """Insert any configured member that is not already present.

    Args:
        session: The session to insert through.
        names: The configured household member names.

    Returns:
        The names that were newly inserted, in configuration order.
    """
    existing = set(session.scalars(select(HouseholdMemberORM.name)).all())
    added = [name for name in names if name not in existing]
    session.add_all(HouseholdMemberORM(name=name) for name in added)
    return added


def main() -> None:
    """Seed the configured household members into the configured database."""
    settings = get_settings()
    with get_session_factory()() as session:
        added = seed_household_members(session, settings.household_members)
        session.commit()

    if added:
        print(f"seeded household members: {', '.join(added)}")
    else:
        print("household members already seeded; nothing to do")


if __name__ == "__main__":
    main()
