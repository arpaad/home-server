"""Typed application settings, loaded once from the environment."""

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import UnknownTimeZoneError

Environment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    """Settings for the H.O.M.E. backend, read from ``HOME_``-prefixed variables."""

    model_config = SettingsConfigDict(
        env_prefix="HOME_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: Environment = "development"

    database_url: str = Field(
        default="postgresql+psycopg://home:home@localhost:5432/home",
        description="SQLAlchemy URL of the household database.",
    )

    household_timezone: str = Field(
        default="Europe/Budapest",
        description=(
            "IANA time zone naming the household's local calendar. Availability "
            "dates are compared against the current date in this zone."
        ),
    )

    @field_validator("household_timezone")
    @classmethod
    def _timezone_must_be_known(cls, value: str) -> str:
        """Reject a time zone the platform cannot resolve.

        Args:
            value: The configured IANA time zone name.

        Returns:
            The value unchanged, once it is known to resolve.

        Raises:
            UnknownTimeZoneError: If the name is not a resolvable IANA time zone.
        """
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise UnknownTimeZoneError(value) from exc
        return value

    @property
    def timezone(self) -> ZoneInfo:
        """The household's time zone as a ``ZoneInfo``.

        Returns:
            The resolved time zone for the configured name.
        """
        return ZoneInfo(self.household_timezone)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, reading the environment on first call.

    Returns:
        The cached settings instance.
    """
    return Settings()
