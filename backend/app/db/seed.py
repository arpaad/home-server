"""Seed the data a fresh database needs before the app is usable.

Run by `make seed` and by the container entrypoint, and safe to run
repeatedly: seeding inserts only what is missing, so it never duplicates a
row or overwrites a member's edits. Seeded rows carry no special status — a
household that renames "Household" to "Cleaning" keeps its rename.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.household.repository.member_orm import HouseholdMemberORM
from app.modules.shopping.repository.orm import CategoryORM

# (name, emoji icon, colour, position). Positions are spaced out so a
# household can slot a new category between two without renumbering.
DEFAULT_CATEGORIES: tuple[tuple[str, str, str, int], ...] = (
    ("Produce", "🥦", "#4c9a2a", 10),
    ("Bakery", "🥖", "#c48a3a", 20),
    ("Dairy", "🧀", "#e0b53a", 30),
    ("Meat", "🥩", "#b23a3a", 40),
    ("Frozen", "🧊", "#3a8ac4", 50),
    ("Drinks", "🧃", "#7a4cc4", 60),
    ("Household", "🧴", "#5a6b7a", 70),
    ("Other", "📦", "#8a8a8a", 80),
)


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


def seed_categories(session: Session) -> list[str]:
    """Insert any default category whose name is not already present.

    The comparison is case-insensitive, matching the unique index, so a
    household that already has "produce" does not get a second "Produce".

    Args:
        session: The session to insert through.

    Returns:
        The names that were newly inserted, in position order.
    """
    existing = set(session.scalars(select(func.lower(CategoryORM.name))).all())
    added: list[str] = []
    for name, icon, colour, position in DEFAULT_CATEGORIES:
        if name.lower() in existing:
            continue
        session.add(CategoryORM(name=name, icon=icon, colour=colour, position=position))
        added.append(name)
    return added


def main() -> None:
    """Seed the configured members and default categories."""
    settings = get_settings()
    with get_session_factory()() as session:
        members = seed_household_members(session, settings.household_members)
        categories = seed_categories(session)
        session.commit()

    if members:
        print(f"seeded household members: {', '.join(members)}")
    else:
        print("household members already seeded; nothing to do")
    if categories:
        print(f"seeded categories: {', '.join(categories)}")
    else:
        print("categories already seeded; nothing to do")


if __name__ == "__main__":
    main()
