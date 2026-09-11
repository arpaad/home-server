"""HTTP endpoints for the catalogue and for suggestions while typing."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.modules.shopping.dto.catalogue_dto import (
    CatalogueEntryMergeRequest,
    CatalogueEntryRenameRequest,
    CatalogueEntryResponse,
    CatalogueEntryUpdateRequest,
    EntryInUseResponse,
    RenameCollisionResponse,
)
from app.modules.shopping.providers import CatalogueServiceDep

router = APIRouter(prefix="/api/shopping/catalogue", tags=["catalogue"])


@router.get("", summary="List the whole catalogue")
def list_entries(catalogue: CatalogueServiceDep) -> list[CatalogueEntryResponse]:
    """Return every entry, ordered by name.

    Args:
        catalogue: The catalogue service.

    Returns:
        The catalogue.
    """
    return [CatalogueEntryResponse.from_domain(e) for e in catalogue.list_entries()]


@router.get("/suggest", summary="Offer entries matching what is being typed")
def suggest(
    catalogue: CatalogueServiceDep,
    q: Annotated[
        str,
        Query(
            description="The start of an item name, compared case-insensitively.",
            max_length=200,
        ),
    ] = "",
) -> list[CatalogueEntryResponse]:
    """Return entries whose name starts with the query, most recently used first.

    Args:
        catalogue: The catalogue service.
        q: What has been typed so far.

    Returns:
        Matching entries.
    """
    return [CatalogueEntryResponse.from_domain(e) for e in catalogue.suggest(q)]


@router.get("/{entry_id}", summary="Read one entry")
def read_entry(entry_id: UUID, catalogue: CatalogueServiceDep) -> CatalogueEntryResponse:
    """Return one entry.

    Args:
        entry_id: The entry to read.
        catalogue: The catalogue service.

    Returns:
        The entry.
    """
    return CatalogueEntryResponse.from_domain(catalogue.get_entry(entry_id))


@router.patch("/{entry_id}", summary="Correct an entry's category or stores")
def update_entry(
    entry_id: UUID, payload: CatalogueEntryUpdateRequest, catalogue: CatalogueServiceDep
) -> CatalogueEntryResponse:
    """Set or clear the category, and set the remembered stores.

    Changing the category regroups every item referring to this entry,
    including ones already on the list.

    Args:
        entry_id: The entry to change.
        payload: The fields to change.
        catalogue: The catalogue service.

    Returns:
        The updated entry.
    """
    entry = catalogue.get_entry(entry_id)
    if payload.clear_category:
        entry = catalogue.set_category(entry_id, None)
    elif payload.category_id is not None:
        entry = catalogue.set_category(entry_id, payload.category_id)
    if payload.store_ids is not None:
        entry = catalogue.set_stores(entry_id, payload.store_ids)
    return CatalogueEntryResponse.from_domain(entry)


@router.post(
    "/{entry_id}/rename",
    summary="Rename an entry",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": RenameCollisionResponse,
            "description": "Another entry has that name; merge into it instead.",
        }
    },
)
def rename_entry(
    entry_id: UUID, payload: CatalogueEntryRenameRequest, catalogue: CatalogueServiceDep
) -> CatalogueEntryResponse:
    """Rename an entry, refusing a collision and offering the merge instead.

    Args:
        entry_id: The entry to rename.
        payload: The new name.
        catalogue: The catalogue service.

    Returns:
        The renamed entry.
    """
    return CatalogueEntryResponse.from_domain(catalogue.rename(entry_id, payload.name))


@router.post("/{entry_id}/merge", summary="Fold this entry into another")
def merge_entry(
    entry_id: UUID, payload: CatalogueEntryMergeRequest, catalogue: CatalogueServiceDep
) -> CatalogueEntryResponse:
    """Move this entry's items to another entry and remove this one.

    Args:
        entry_id: The entry being merged away, typically the typo.
        payload: The entry that survives.
        catalogue: The catalogue service.

    Returns:
        The surviving entry.
    """
    survivor = catalogue.merge(source_id=entry_id, target_id=payload.into_id)
    return CatalogueEntryResponse.from_domain(survivor)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an entry nothing refers to",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": EntryInUseResponse,
            "description": "Items still refer to this entry; merge it instead.",
        }
    },
)
def delete_entry(entry_id: UUID, catalogue: CatalogueServiceDep) -> Response:
    """Remove an entry, refusing while items refer to it.

    Args:
        entry_id: The entry to remove.
        catalogue: The catalogue service.

    Returns:
        An empty 204 response.
    """
    catalogue.remove(entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
