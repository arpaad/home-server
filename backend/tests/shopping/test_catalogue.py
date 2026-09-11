"""The catalogue: fills itself, suggests, remembers, and can be tidied."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.shopping.domain.catalogue import CatalogueEntry
from app.modules.shopping.domain.category import Category
from app.modules.shopping.errors import (
    CategoryNotFoundError,
    DuplicateEntryNameError,
    EmptyEntryNameError,
    EntryInUseError,
    EntryNotFoundError,
    MergeIntoSelfError,
    UnknownStoresError,
)
from app.modules.shopping.repository.catalogue_repository import SqlAlchemyCatalogueRepository
from app.modules.shopping.repository.category_repository import SqlAlchemyCategoryRepository
from app.modules.shopping.repository.item_repository import SqlAlchemyShoppingItemRepository
from app.modules.shopping.repository.store_repository import SqlAlchemyStoreRepository
from app.modules.shopping.service.catalogue_service import CatalogueService
from app.modules.shopping.service.category_service import CategoryService

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)
EARLIER = NOW - timedelta(days=3)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyCatalogueRepository:
    """Provide the catalogue repository on the test session.

    Args:
        session: The test session.

    Returns:
        A catalogue repository.
    """
    return SqlAlchemyCatalogueRepository(session)


@pytest.fixture
def catalogue(session: Session) -> CatalogueService:
    """Provide the catalogue service on the test session.

    Args:
        session: The test session.

    Returns:
        A catalogue service.
    """
    return CatalogueService(
        SqlAlchemyCatalogueRepository(session),
        SqlAlchemyCategoryRepository(session),
        SqlAlchemyStoreRepository(session),
    )


@pytest.fixture
def categories(session: Session) -> CategoryService:
    """Provide the category service on the test session.

    Args:
        session: The test session.

    Returns:
        A category service.
    """
    return CategoryService(SqlAlchemyCategoryRepository(session))


@pytest.fixture
def items(session: Session) -> SqlAlchemyShoppingItemRepository:
    """Provide the item repository on the test session.

    Args:
        session: The test session.

    Returns:
        An item repository.
    """
    return SqlAlchemyShoppingItemRepository(session)


def add_item(
    items: SqlAlchemyShoppingItemRepository, name: str, session: Session, entry_id: UUID
) -> UUID:
    """Add an item linked to a catalogue entry, the way the service will.

    Args:
        items: The item repository.
        name: The item's name.
        session: The test session, to set the link directly.
        entry_id: The catalogue entry to link.

    Returns:
        The created item's id.
    """
    item = items.add(
        name=name, quantity=1, unit="piece", store_ids=[], available_from=None, origin="manual"
    )
    session.execute(
        text("UPDATE shopping_items SET catalogue_entry_id = :e WHERE id = :i"),
        {"e": entry_id, "i": item.id},
    )
    return item.id


class TestDomain:
    def test_an_entry_constructs_with_and_without_a_category(self):
        category = Category(id=uuid4(), name="Dairy", icon="🧀", colour="#e0b53a", position=10)

        plain = CatalogueEntry(id=uuid4(), name="milk")
        categorised = CatalogueEntry(id=uuid4(), name="milk", category=category)

        assert plain.category is None
        assert categorised.category == category

    def test_an_empty_name_is_rejected(self):
        with pytest.raises(EmptyEntryNameError):
            CatalogueEntry(id=uuid4(), name="  ")


class TestFillingItself:
    def test_a_new_name_creates_exactly_one_entry(self, repo: SqlAlchemyCatalogueRepository):
        entry = repo.find_or_create("sourdough", used_at=NOW)

        assert entry.name == "sourdough"
        assert entry.category is None
        assert [e.name for e in repo.list_all()] == ["sourdough"]

    def test_a_familiar_name_reuses_its_entry_regardless_of_case(
        self, repo: SqlAlchemyCatalogueRepository
    ):
        first = repo.find_or_create("sourdough", used_at=EARLIER)

        second = repo.find_or_create("  Sourdough ", used_at=NOW)

        assert second.id == first.id
        assert len(repo.list_all()) == 1

    def test_reuse_moves_last_used_forward(self, repo: SqlAlchemyCatalogueRepository):
        repo.find_or_create("milk", used_at=EARLIER)

        entry = repo.find_or_create("milk", used_at=NOW)

        assert entry.last_used_at == NOW


class TestSuggestions:
    def test_a_prefix_offers_matching_entries_only(self, repo: SqlAlchemyCatalogueRepository):
        repo.find_or_create("milk", used_at=NOW)
        repo.find_or_create("mild cheddar", used_at=EARLIER)
        repo.find_or_create("bread", used_at=NOW)

        offered = [e.name for e in repo.suggest("mil", limit=8)]

        assert set(offered) == {"milk", "mild cheddar"}
        assert "bread" not in offered

    def test_the_most_recently_used_comes_first(self, repo: SqlAlchemyCatalogueRepository):
        repo.find_or_create("milk", used_at=EARLIER)
        repo.find_or_create("mild cheddar", used_at=NOW)

        assert [e.name for e in repo.suggest("mil", limit=8)] == ["mild cheddar", "milk"]

    def test_matching_is_case_insensitive(self, repo: SqlAlchemyCatalogueRepository):
        repo.find_or_create("Milk", used_at=NOW)

        assert [e.name for e in repo.suggest("MI", limit=8)] == ["Milk"]

    def test_matching_is_on_the_start_of_the_name(self, repo: SqlAlchemyCatalogueRepository):
        repo.find_or_create("oat milk", used_at=NOW)

        assert repo.suggest("milk", limit=8) == []

    def test_like_metacharacters_are_literal(self, repo: SqlAlchemyCatalogueRepository):
        repo.find_or_create("100% juice", used_at=NOW)
        repo.find_or_create("1000 tea bags", used_at=NOW)

        assert [e.name for e in repo.suggest("100%", limit=8)] == ["100% juice"]

    def test_an_empty_prefix_offers_nothing(self, catalogue: CatalogueService):
        catalogue.remember("milk")

        assert catalogue.suggest("   ") == []

    def test_the_suggestion_query_uses_the_name_index(
        self, repo: SqlAlchemyCatalogueRepository, session: Session
    ):
        # Task 2.4: the index on lower(name) must serve the prefix search.
        # With a near-empty table the planner prefers a seq scan, so disable
        # it for this check — the point is that the index *can* be used.
        for i in range(50):
            repo.find_or_create(f"item {i}", used_at=NOW)
        session.execute(text("SET LOCAL enable_seqscan = off"))

        plan = "\n".join(
            session.scalars(
                text(
                    "EXPLAIN SELECT * FROM catalogue_entries "
                    "WHERE lower(name) LIKE 'item 1%' ORDER BY last_used_at DESC"
                )
            ).all()
        )

        assert "ux_catalogue_entries_name_lower" in plan, plan


class TestCorrecting:
    def test_setting_a_category(self, catalogue: CatalogueService, categories: CategoryService):
        bakery = categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")
        entry = catalogue.remember("sourdough")

        updated = catalogue.set_category(entry.id, bakery.id)

        assert updated.category is not None
        assert updated.category.name == "Bakery"

    def test_clearing_a_category(self, catalogue: CatalogueService, categories: CategoryService):
        bakery = categories.add_category(name="Bakery", icon="🥖", colour="#c48a3a")
        entry = catalogue.remember("sourdough")
        catalogue.set_category(entry.id, bakery.id)

        assert catalogue.set_category(entry.id, None).category is None

    def test_an_unknown_category_is_refused(self, catalogue: CatalogueService):
        entry = catalogue.remember("sourdough")

        with pytest.raises(CategoryNotFoundError):
            catalogue.set_category(entry.id, uuid4())

    def test_setting_remembered_stores(self, catalogue: CatalogueService, session: Session):
        stores = SqlAlchemyStoreRepository(session)
        lidl = stores.add("Lidl")
        spar = stores.add("Spar")
        entry = catalogue.remember("ketchup")

        updated = catalogue.set_stores(entry.id, [lidl.id, spar.id, lidl.id])

        assert [s.name for s in updated.stores] == ["Lidl", "Spar"]

    def test_an_unknown_store_is_refused_and_changes_nothing(
        self, catalogue: CatalogueService, session: Session
    ):
        lidl = SqlAlchemyStoreRepository(session).add("Lidl")
        entry = catalogue.remember("ketchup")
        catalogue.set_stores(entry.id, [lidl.id])

        with pytest.raises(UnknownStoresError):
            catalogue.set_stores(entry.id, [uuid4()])

        assert [s.name for s in catalogue.get_entry(entry.id).stores] == ["Lidl"]


class TestRenamingAndMerging:
    def test_a_typo_can_be_renamed(self, catalogue: CatalogueService):
        entry = catalogue.remember("mlik")

        renamed = catalogue.rename(entry.id, "milk")

        assert renamed.name == "milk"
        assert [e.name for e in catalogue.suggest("mil")] == ["milk"]

    def test_renaming_onto_an_existing_name_is_refused_and_offers_the_target(
        self, catalogue: CatalogueService
    ):
        milk = catalogue.remember("milk")
        typo = catalogue.remember("mlik")

        with pytest.raises(DuplicateEntryNameError) as caught:
            catalogue.rename(typo.id, "Milk")

        assert caught.value.existing_id == milk.id
        assert {e.name for e in catalogue.list_entries()} == {"milk", "mlik"}

    def test_renaming_to_its_own_name_in_another_case_is_fine(self, catalogue: CatalogueService):
        entry = catalogue.remember("milk")

        assert catalogue.rename(entry.id, "Milk").name == "Milk"

    def test_merging_moves_items_and_removes_the_source(
        self,
        catalogue: CatalogueService,
        items: SqlAlchemyShoppingItemRepository,
        session: Session,
    ):
        milk = catalogue.remember("milk")
        typo = catalogue.remember("mlik")
        typo_item = add_item(items, "mlik", session, typo.id)
        real_item = add_item(items, "milk", session, milk.id)

        survivor = catalogue.merge(source_id=typo.id, target_id=milk.id)

        assert survivor.id == milk.id
        assert [e.name for e in catalogue.list_entries()] == ["milk"]
        linked = session.scalars(
            text("SELECT catalogue_entry_id FROM shopping_items WHERE id IN (:a, :b)"),
            {"a": typo_item, "b": real_item},
        ).all()
        assert set(linked) == {milk.id}

    def test_merging_into_itself_is_refused(self, catalogue: CatalogueService):
        milk = catalogue.remember("milk")

        with pytest.raises(MergeIntoSelfError):
            catalogue.merge(source_id=milk.id, target_id=milk.id)

    def test_merging_an_unknown_entry_is_refused(self, catalogue: CatalogueService):
        milk = catalogue.remember("milk")

        with pytest.raises(EntryNotFoundError):
            catalogue.merge(source_id=uuid4(), target_id=milk.id)


class TestRemoval:
    def test_an_entry_in_use_cannot_be_removed_and_the_items_are_named(
        self,
        catalogue: CatalogueService,
        items: SqlAlchemyShoppingItemRepository,
        session: Session,
    ):
        milk = catalogue.remember("milk")
        add_item(items, "milk", session, milk.id)

        with pytest.raises(EntryInUseError) as caught:
            catalogue.remove(milk.id)

        assert caught.value.item_names == ("milk",)
        assert catalogue.get_entry(milk.id).name == "milk"

    def test_the_database_itself_refuses_to_drop_a_referenced_entry(
        self,
        catalogue: CatalogueService,
        items: SqlAlchemyShoppingItemRepository,
        session: Session,
    ):
        # Task 2.3: RESTRICT holds even if the service check were bypassed.
        milk = catalogue.remember("milk")
        add_item(items, "milk", session, milk.id)

        with pytest.raises(IntegrityError):
            session.execute(text("DELETE FROM catalogue_entries WHERE id = :e"), {"e": milk.id})
            session.flush()

        session.rollback()

    def test_an_unreferenced_entry_can_be_removed(self, catalogue: CatalogueService):
        stale = catalogue.remember("stale thing")

        catalogue.remove(stale.id)

        assert catalogue.list_entries() == []
