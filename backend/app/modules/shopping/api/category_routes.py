"""HTTP endpoints for categories."""

from uuid import UUID

from fastapi import APIRouter, status

from app.modules.shopping.dto.category_dto import (
    CategoryCreateRequest,
    CategoryRemovalPreview,
    CategoryRemovalResponse,
    CategoryReorderRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.modules.shopping.providers import CategoryServiceDep

router = APIRouter(prefix="/api/shopping/categories", tags=["categories"])


@router.get("", summary="List categories in the household's order")
def list_categories(categories: CategoryServiceDep) -> list[CategoryResponse]:
    """Return every category, in the order groups appear.

    Args:
        categories: The category service.

    Returns:
        The categories.
    """
    return [CategoryResponse.from_domain(c) for c in categories.list_categories()]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Add a category")
def create_category(
    payload: CategoryCreateRequest, categories: CategoryServiceDep
) -> CategoryResponse:
    """Add a category at the end of the order.

    Args:
        payload: The category to create.
        categories: The category service.

    Returns:
        The created category.
    """
    created = categories.add_category(name=payload.name, icon=payload.icon, colour=payload.colour)
    return CategoryResponse.from_domain(created)


@router.put("/order", summary="Set the household-wide category order")
def reorder_categories(
    payload: CategoryReorderRequest, categories: CategoryServiceDep
) -> list[CategoryResponse]:
    """Set the order groups appear in, for every store.

    Args:
        payload: Every category id, in the desired order.
        categories: The category service.

    Returns:
        The categories in their new order.
    """
    reordered = categories.reorder_categories(payload.ordered_ids)
    return [CategoryResponse.from_domain(c) for c in reordered]


@router.patch("/{category_id}", summary="Change a category's name, icon or colour")
def update_category(
    category_id: UUID, payload: CategoryUpdateRequest, categories: CategoryServiceDep
) -> CategoryResponse:
    """Change a category, leaving unsupplied fields alone.

    Args:
        category_id: The category to change.
        payload: The fields to change.
        categories: The category service.

    Returns:
        The updated category.
    """
    updated = categories.edit_category(
        category_id, name=payload.name, icon=payload.icon, colour=payload.colour
    )
    return CategoryResponse.from_domain(updated)


@router.get(
    "/{category_id}/removal-preview",
    summary="Say what removing this category would do",
)
def preview_removal(category_id: UUID, categories: CategoryServiceDep) -> CategoryRemovalPreview:
    """Report how many entries would become uncategorised, for a confirmation.

    Args:
        category_id: The category being considered for removal.
        categories: The category service.

    Returns:
        The count of entries that would lose their category.
    """
    count = categories.entries_that_would_be_uncategorised(category_id)
    return CategoryRemovalPreview(entries_uncategorised=count)


@router.delete("/{category_id}", summary="Remove a category")
def delete_category(category_id: UUID, categories: CategoryServiceDep) -> CategoryRemovalResponse:
    """Remove a category; its entries become uncategorised, nothing disappears.

    Args:
        category_id: The category to remove.
        categories: The category service.

    Returns:
        How many entries became uncategorised.
    """
    result = categories.remove_category(category_id)
    return CategoryRemovalResponse(entries_uncategorised=result.entries_uncategorised)
