"""Business rules for the household's catalogue of what it buys."""

from collections.abc import Iterable
from uuid import UUID

from app.core.clock import now_utc
from app.modules.shopping.domain.catalogue import CatalogueEntry, ensure_valid_entry_name
from app.modules.shopping.errors import (
    CategoryNotFoundError,
    DuplicateEntryNameError,
    EntryInUseError,
    EntryNotFoundError,
    MergeIntoSelfError,
    UnknownStoresError,
)
from app.modules.shopping.repository.interfaces import (
    CatalogueRepository,
    CategoryRepository,
    StoreRepository,
)

SUGGESTION_LIMIT = 8


class CatalogueService:
    """Remembers what the household buys and offers it back while typing."""

    def __init__(
        self,
        catalogue: CatalogueRepository,
        categories: CategoryRepository,
        stores: StoreRepository,
    ) -> None:
        """Bind the service to its repositories.

        Args:
            catalogue: The catalogue.
            categories: The category registry, to validate assignments.
            stores: The store registry, to validate remembered stores.
        """
        self._catalogue = catalogue
        self._categories = categories
        self._stores = stores

    def _require_entry(self, entry_id: UUID) -> CatalogueEntry:
        """Return an entry, refusing when it does not exist.

        Args:
            entry_id: The entry to look up.

        Returns:
            The entry.

        Raises:
            EntryNotFoundError: If no entry has that id.
        """
        entry = self._catalogue.get(entry_id)
        if entry is None:
            raise EntryNotFoundError(entry_id)
        return entry

    # ---- reads ----

    def get_entry(self, entry_id: UUID) -> CatalogueEntry:
        """Return one entry.

        Args:
            entry_id: The entry to look up.

        Returns:
            The entry.
        """
        return self._require_entry(entry_id)

    def list_entries(self) -> list[CatalogueEntry]:
        """Return the whole catalogue, ordered by name.

        Returns:
            Every entry.
        """
        return self._catalogue.list_all()

    def suggest(self, prefix: str) -> list[CatalogueEntry]:
        """Offer entries matching the start of what a member is typing.

        An empty prefix offers nothing: suggestions are for narrowing, and
        the whole catalogue is on its own page.

        Args:
            prefix: What has been typed so far.

        Returns:
            Matching entries, most recently used first.
        """
        if not prefix.strip():
            return []
        return self._catalogue.suggest(prefix, limit=SUGGESTION_LIMIT)

    # ---- writes ----

    def remember(self, name: str) -> CatalogueEntry:
        """Record that a name was used, creating its entry if new.

        Called by the shopping list when an item is added; a member never
        calls this directly. It is what makes the catalogue fill itself.

        Args:
            name: The item name as typed.

        Returns:
            The entry now carrying this name.
        """
        return self._catalogue.find_or_create(ensure_valid_entry_name(name), used_at=now_utc())

    def create(
        self,
        *,
        name: str,
        category_id: UUID | None = None,
        store_ids: Iterable[UUID] = (),
    ) -> CatalogueEntry:
        """Add an entry directly, without putting anything on the list.

        For setting up the things the household knows it buys before the
        first time they are needed. Refuses a name another entry already
        carries, naming it, so the client can point at the existing one.

        Args:
            name: The entry's name.
            category_id: Its category, or None for uncategorised.
            store_ids: The stores it is usually bought at.

        Returns:
            The created entry.

        Raises:
            DuplicateEntryNameError: If an entry already has that name.
            CategoryNotFoundError: If the category does not exist.
            UnknownStoresError: If any store id matches no store.
        """
        cleaned = ensure_valid_entry_name(name)
        existing = self._catalogue.find_by_name(cleaned)
        if existing is not None:
            raise DuplicateEntryNameError(cleaned, existing.id)
        if category_id is not None and self._categories.get(category_id) is None:
            raise CategoryNotFoundError(category_id)
        wanted = list(dict.fromkeys(store_ids))
        unknown = self._stores.unknown_ids(wanted)
        if unknown:
            raise UnknownStoresError(unknown)

        entry = self._catalogue.find_or_create(cleaned, used_at=now_utc())
        return self._catalogue.update(entry.id, category_id=category_id, store_ids=wanted)

    def set_category(self, entry_id: UUID, category_id: UUID | None) -> CatalogueEntry:
        """Set or clear an entry's category.

        Because items derive their category from the entry, this regroups
        every item referring to it — including ones already on the list.

        Args:
            entry_id: The entry to change.
            category_id: The new category, or None to make it uncategorised.

        Returns:
            The updated entry.

        Raises:
            CategoryNotFoundError: If the category does not exist.
        """
        self._require_entry(entry_id)
        if category_id is None:
            return self._catalogue.update(entry_id, clear_category=True)
        if self._categories.get(category_id) is None:
            raise CategoryNotFoundError(category_id)
        return self._catalogue.update(entry_id, category_id=category_id)

    def set_stores(self, entry_id: UUID, store_ids: Iterable[UUID]) -> CatalogueEntry:
        """Set the stores an entry is usually bought at.

        Args:
            entry_id: The entry to change.
            store_ids: The complete new set; empty means no prefill.

        Returns:
            The updated entry.

        Raises:
            UnknownStoresError: If any id matches no store.
        """
        self._require_entry(entry_id)
        wanted = list(dict.fromkeys(store_ids))
        unknown = self._stores.unknown_ids(wanted)
        if unknown:
            raise UnknownStoresError(unknown)
        return self._catalogue.update(entry_id, store_ids=wanted)

    def rename(self, entry_id: UUID, name: str) -> CatalogueEntry:
        """Rename an entry, refusing a name another entry already carries.

        The refusal names the existing entry so the client can offer a merge
        instead — which is what a member almost always wants when they hit
        this.

        Args:
            entry_id: The entry to rename.
            name: The new name.

        Returns:
            The renamed entry.

        Raises:
            DuplicateEntryNameError: If another entry has that name.
        """
        self._require_entry(entry_id)
        cleaned = ensure_valid_entry_name(name)
        existing = self._catalogue.find_by_name(cleaned)
        if existing is not None and existing.id != entry_id:
            raise DuplicateEntryNameError(cleaned, existing.id)
        return self._catalogue.rename(entry_id, cleaned)

    def merge(self, *, source_id: UUID, target_id: UUID) -> CatalogueEntry:
        """Fold one entry into another, moving its items across.

        Args:
            source_id: The entry being merged away, typically the typo.
            target_id: The entry that survives.

        Returns:
            The surviving entry.

        Raises:
            MergeIntoSelfError: If both ids name the same entry.
        """
        if source_id == target_id:
            raise MergeIntoSelfError(source_id)
        self._require_entry(source_id)
        self._require_entry(target_id)
        return self._catalogue.merge(source_id=source_id, target_id=target_id)

    def remove(self, entry_id: UUID) -> None:
        """Remove an entry, refusing while items still refer to it.

        Args:
            entry_id: The entry to remove.

        Raises:
            EntryInUseError: If items refer to the entry; merging is the way
                to remove a duplicate that has history.
        """
        self._require_entry(entry_id)
        referencing = self._catalogue.item_names_referencing(entry_id)
        if referencing:
            raise EntryInUseError(entry_id, referencing)
        self._catalogue.delete(entry_id)
