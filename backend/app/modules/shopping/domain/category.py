"""A category the household sorts its shopping into."""

import re
from dataclasses import dataclass
from uuid import UUID

from app.modules.shopping.errors import (
    EmptyCategoryIconError,
    EmptyCategoryNameError,
    InvalidCategoryColourError,
)

_HEX_COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def ensure_valid_category_name(name: str) -> str:
    """Return the name stripped, refusing one that carries no content.

    Args:
        name: The proposed category name.

    Returns:
        The name with surrounding whitespace removed.

    Raises:
        EmptyCategoryNameError: If the name is empty or only whitespace.
    """
    stripped = name.strip()
    if not stripped:
        raise EmptyCategoryNameError
    return stripped


def ensure_valid_icon(icon: str) -> str:
    """Return the icon stripped, refusing an empty one.

    Args:
        icon: The proposed icon, an emoji.

    Returns:
        The icon with surrounding whitespace removed.

    Raises:
        EmptyCategoryIconError: If the icon is empty.
    """
    stripped = icon.strip()
    if not stripped:
        raise EmptyCategoryIconError
    return stripped


def ensure_valid_colour(colour: str) -> str:
    """Return the colour lower-cased, refusing anything but #rrggbb.

    Args:
        colour: The proposed colour.

    Returns:
        The colour in lower-case hex form.

    Raises:
        InvalidCategoryColourError: If the colour is not six hex digits.
    """
    if not _HEX_COLOUR.match(colour):
        raise InvalidCategoryColourError(colour)
    return colour.lower()


@dataclass(frozen=True, slots=True)
class Category:
    """A category with the appearance that lets it be recognised at a glance.

    ``position`` is the household-wide order groups appear in — one sequence
    for every store, because it matches how the household shops rather than
    the aisles of any particular shop.
    """

    id: UUID
    name: str
    icon: str
    colour: str
    position: int

    def __post_init__(self) -> None:
        """Enforce the category invariants.

        Delegates to the `ensure_*` functions, which carry the rules and the
        errors they raise.
        """
        ensure_valid_category_name(self.name)
        ensure_valid_icon(self.icon)
        ensure_valid_colour(self.colour)
