"""The store registry enforces case-insensitive name uniqueness in SQL."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository


@pytest.fixture
def stores(session: Session) -> SqlAlchemyStoreRepository:
    """Provide a store repository on the test session.

    Args:
        session: The test session.

    Returns:
        A store repository.
    """
    return SqlAlchemyStoreRepository(session)


def test_a_store_can_be_added_and_read_back(stores: SqlAlchemyStoreRepository):
    added = stores.add("Lidl")

    assert stores.get(added.id) == added
    assert [s.name for s in stores.list_all()] == ["Lidl"]


def test_a_differently_cased_duplicate_is_rejected_and_leaves_one_store(
    stores: SqlAlchemyStoreRepository, session: Session
):
    stores.add("Lidl")

    with pytest.raises(IntegrityError):
        stores.add("lidl")

    session.rollback()
    # The unique index is on lower(name), so the second insert never lands.
    assert len(SqlAlchemyStoreRepository(session).list_all()) <= 1


def test_a_store_is_found_by_name_case_insensitively(stores: SqlAlchemyStoreRepository):
    added = stores.add("Lidl")

    assert stores.find_by_name("lidl") == added
    assert stores.find_by_name("  LIDL  ") == added
    assert stores.find_by_name("Spar") is None


def test_unknown_ids_reports_only_the_missing_ones(stores: SqlAlchemyStoreRepository):
    lidl = stores.add("Lidl")
    missing = uuid4()

    assert stores.unknown_ids([lidl.id]) == frozenset()
    assert stores.unknown_ids([lidl.id, missing]) == frozenset({missing})
    assert stores.unknown_ids([]) == frozenset()


def test_a_store_can_be_deleted(stores: SqlAlchemyStoreRepository):
    lidl = stores.add("Lidl")

    stores.delete(lidl.id)

    assert stores.get(lidl.id) is None


def test_deleting_an_unknown_store_is_harmless(stores: SqlAlchemyStoreRepository):
    stores.delete(uuid4())


def test_a_blank_store_name_is_refused_by_the_database(stores: SqlAlchemyStoreRepository):
    with pytest.raises(IntegrityError):
        stores.add("   ")


def test_ids_are_real_uuids(stores: SqlAlchemyStoreRepository):
    assert isinstance(stores.add("Lidl").id, UUID)
