"""The starter pack goes in once, and stays out of the household's way after."""

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.seed import load_starter_pack, seed_catalogue, seed_categories
from app.modules.shopping.repository.orm import CatalogueEntryORM, CategoryORM


def count(session: Session, model: type[CategoryORM] | type[CatalogueEntryORM]) -> int:
    """Count rows of a model.

    Args:
        session: The test session.
        model: The ORM model.

    Returns:
        The row count.
    """
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_the_pack_is_well_formed():
    pack = load_starter_pack()
    names = [e["name"].lower() for e in pack["entries"]]
    category_names = {c["name"] for c in pack["categories"]}

    assert len(pack["categories"]) >= 25
    assert len(pack["entries"]) >= 500
    assert len(names) == len(set(names)), "duplicate entry names"
    assert all(e["category"] in category_names for e in pack["entries"]), (
        "entry with unknown category"
    )
    assert all(c["colour"].startswith("#") and len(c["colour"]) == 7 for c in pack["categories"])


def test_seeding_an_empty_database_inserts_everything_linked(session: Session):
    pack = load_starter_pack()

    categories = seed_categories(session, pack)
    entries = seed_catalogue(session, pack)

    assert len(categories) == len(pack["categories"])
    assert entries == len(pack["entries"])
    unlinked = session.scalar(
        select(func.count())
        .select_from(CatalogueEntryORM)
        .where(CatalogueEntryORM.category_id.is_(None))
    )
    assert unlinked == 0
    # Order is the pack's order.
    first = session.scalars(select(CategoryORM).order_by(CategoryORM.position)).first()
    assert first is not None and first.name == pack["categories"][0]["name"]


def test_seeding_twice_changes_nothing(session: Session):
    pack = load_starter_pack()
    seed_categories(session, pack)
    seed_catalogue(session, pack)

    assert seed_categories(session, pack) == []
    assert seed_catalogue(session, pack) == 0
    assert count(session, CategoryORM) == len(pack["categories"])
    assert count(session, CatalogueEntryORM) == len(pack["entries"])


def test_a_deleted_starter_category_stays_deleted(session: Session):
    # The old seed re-inserted any "missing" default on every run, which
    # resurrected what the household had removed on purpose.
    pack = load_starter_pack()
    seed_categories(session, pack)
    session.execute(
        text("DELETE FROM categories WHERE name = :n"), {"n": pack["categories"][0]["name"]}
    )

    assert seed_categories(session, pack) == []
    assert count(session, CategoryORM) == len(pack["categories"]) - 1


def test_a_renamed_category_still_gets_its_entries(session: Session):
    # Categories seeded, one renamed, then the catalogue seeded: entries for
    # the renamed one are inserted uncategorised, not dropped.
    pack = load_starter_pack()
    seed_categories(session, pack)
    original = pack["categories"][0]["name"]
    session.execute(text("UPDATE categories SET name = 'Renamed' WHERE name = :n"), {"n": original})

    seed_catalogue(session, pack)

    expected_uncategorised = sum(1 for e in pack["entries"] if e["category"] == original)
    unlinked = session.scalar(
        select(func.count())
        .select_from(CatalogueEntryORM)
        .where(CatalogueEntryORM.category_id.is_(None))
    )
    assert unlinked == expected_uncategorised
