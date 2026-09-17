"""Seed the data a fresh database needs before the app is usable.

Run by `make seed` and by the container entrypoint. Two kinds of seed, with
different rules:

- **Household members** are configuration. Any configured member that is
  missing is inserted, every run, so changing the setting takes effect.
- **Categories and the catalogue** are a starter pack. They are inserted
  only into an *empty* table, once. After that they belong to the
  household: what is renamed stays renamed, what is deleted stays deleted.
  Re-inserting "missing" starter rows on every restart would resurrect
  exactly the things someone removed on purpose — which is what the
  previous seed did, and what the spec's "seeded categories carry no special
  status" forbids.

The starter pack lives in `seed_data/catalogue.hu.json`, as data, so it can
be read by tooling and tests without importing this module.
"""

import json
from importlib import resources
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import now_utc
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.household.repository.member_orm import HouseholdMemberORM
from app.modules.shopping.repository.orm import CatalogueEntryORM, CategoryORM


class SeedCategory(TypedDict):
    name: str
    icon: str
    colour: str


class SeedEntry(TypedDict):
    name: str
    category: str


class StarterPack(TypedDict):
    categories: list[SeedCategory]
    entries: list[SeedEntry]


def load_starter_pack() -> StarterPack:
    """Read the starter pack shipped with the application.

    Returns:
        The categories and catalogue entries a fresh installation starts with.
    """
    text = resources.files("app.db.seed_data").joinpath("catalogue.hu.json").read_text("utf-8")
    pack: StarterPack = json.loads(text)
    return pack


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


def seed_categories(session: Session, pack: StarterPack) -> list[str]:
    """Insert the starter categories, in order, into an empty table only.

    Args:
        session: The session to insert through.
        pack: The starter pack.

    Returns:
        The names inserted, or an empty list when the table already had rows.
    """
    if session.scalar(select(func.count()).select_from(CategoryORM)):
        return []
    for position, category in enumerate(pack["categories"], start=1):
        session.add(
            CategoryORM(
                name=category["name"],
                icon=category["icon"],
                colour=category["colour"],
                position=position * 10,
            )
        )
    session.flush()
    return [c["name"] for c in pack["categories"]]


def seed_catalogue(session: Session, pack: StarterPack) -> int:
    """Insert the starter catalogue, into an empty table only.

    Each entry is linked to its category by name; an entry whose category is
    not present (renamed before the catalogue was seeded) is inserted
    uncategorised rather than skipped, so nothing silently goes missing.

    Args:
        session: The session to insert through.
        pack: The starter pack.

    Returns:
        How many entries were inserted; zero when the table already had rows.
    """
    if session.scalar(select(func.count()).select_from(CatalogueEntryORM)):
        return 0
    by_name = {
        name.lower(): category_id
        for name, category_id in session.execute(select(CategoryORM.name, CategoryORM.id)).all()
    }
    used_at = now_utc()
    for entry in pack["entries"]:
        session.add(
            CatalogueEntryORM(
                name=entry["name"],
                category_id=by_name.get(entry["category"].lower()),
                last_used_at=used_at,
            )
        )
    session.flush()
    return len(pack["entries"])


def main() -> None:
    """Seed the configured members and, into an empty database, the starter pack."""
    settings = get_settings()
    pack = load_starter_pack()
    with get_session_factory()() as session:
        members = seed_household_members(session, settings.household_members)
        categories = seed_categories(session, pack)
        entries = seed_catalogue(session, pack)
        session.commit()

    if members:
        print(f"seeded household members: {', '.join(members)}")
    else:
        print("household members already seeded; nothing to do")
    if categories:
        print(f"seeded {len(categories)} starter categories")
    else:
        print("categories present; starter pack not applied")
    if entries:
        print(f"seeded {entries} starter catalogue entries")
    else:
        print("catalogue present; starter pack not applied")


if __name__ == "__main__":
    main()
