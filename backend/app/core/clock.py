"""Access to the current time, always zone-aware.

The project's ruff `DTZ` rules forbid naive clock reads. Availability dates are
compared against the household's own calendar date, so the household's time
zone is a required argument rather than a default.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def household_today(timezone: ZoneInfo) -> date:
    """Return the current calendar date in the household's time zone.

    Args:
        timezone: The household's time zone.

    Returns:
        Today's date as the household reckons it.
    """
    return datetime.now(timezone).date()


def now_utc() -> datetime:
    """Return the current instant in UTC.

    Purchases are stamped in UTC and rendered in the household's zone, so that
    a time zone change never rewrites recorded history.

    Returns:
        The current aware UTC datetime.
    """
    return datetime.now(UTC)
