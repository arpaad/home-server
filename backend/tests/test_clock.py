"""Today is read in the household's zone, never from a naive clock."""

import unittest
from datetime import UTC, date, datetime, tzinfo
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.core.clock import household_today, now_utc

BUDAPEST = ZoneInfo("Europe/Budapest")


class TestHouseholdToday(unittest.TestCase):
    def test_the_date_boundary_follows_the_household_zone_not_utc(self):
        # 23:30 UTC on the 9th is already 01:30 on the 10th in Budapest.
        # Reading the date in UTC would hold an item back for two more hours.
        instant = datetime(2026, 9, 9, 23, 30, tzinfo=UTC)

        def now_in(tz: tzinfo) -> datetime:
            return instant.astimezone(tz)

        with patch("app.core.clock.datetime") as clock:
            clock.now.side_effect = now_in

            self.assertEqual(household_today(BUDAPEST), date(2026, 9, 10))
            self.assertEqual(household_today(ZoneInfo("UTC")), date(2026, 9, 9))

    def test_today_is_a_plain_date(self):
        self.assertIsInstance(household_today(BUDAPEST), date)

    def test_now_is_always_aware(self):
        self.assertIsNotNone(now_utc().tzinfo)


if __name__ == "__main__":
    unittest.main()
