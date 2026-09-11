"""Settings are typed, defaulted, and refuse a time zone that cannot resolve."""

import unittest
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import UnknownTimeZoneError


class TestSettings(unittest.TestCase):
    def test_defaults_are_usable_without_any_environment(self):
        settings = Settings()

        self.assertEqual(settings.environment, "development")
        self.assertIn("postgresql+psycopg://", settings.database_url)
        self.assertEqual(settings.timezone, ZoneInfo("Europe/Budapest"))

    def test_values_are_read_from_the_environment(self):
        settings = Settings(
            environment="production",
            database_url="postgresql+psycopg://u:p@db:5432/home",
            household_timezone="Europe/London",
        )

        self.assertEqual(settings.environment, "production")
        self.assertEqual(settings.timezone, ZoneInfo("Europe/London"))

    def test_an_unresolvable_time_zone_is_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            Settings(household_timezone="Mars/Olympus_Mons")

        self.assertIn("unknown household time zone", str(caught.exception))

    def test_the_validator_itself_raises_a_configuration_error(self):
        # Pydantic wraps any ValueError into a ValidationError, so check the
        # validator directly to pin down the type the rest of the app catches.
        with self.assertRaises(UnknownTimeZoneError):
            Settings._timezone_must_be_known("Mars/Olympus_Mons")  # pyright: ignore[reportPrivateUsage]

    def test_settings_are_immutable(self):
        settings = Settings()

        with self.assertRaises(ValidationError):
            settings.environment = "production"


if __name__ == "__main__":
    unittest.main()
