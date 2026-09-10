"""The unit set an item's quantity is expressed in.

Carried over from the prototype unchanged. Whether units should become a
lookup table with conversions is an open question the recipe module will
force; the fixed set is sufficient until then.
"""

from typing import Literal, get_args

Unit = Literal["piece", "box", "kg", "g", "l", "dl", "m", "cm"]

UNITS: tuple[Unit, ...] = get_args(Unit)

DEFAULT_UNIT: Unit = "piece"
DEFAULT_QUANTITY = 1.0
