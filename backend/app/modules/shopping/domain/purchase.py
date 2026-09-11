"""A recorded purchase of an item.

A purchase is an event rather than a flag on the item, because price, receipt
and finance links attach to the purchase, and a staple bought repeatedly has a
history of them.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Purchase:
    """The record that an item was bought, by whom and when."""

    id: UUID
    item_id: UUID
    member_id: UUID
    bought_at: datetime
