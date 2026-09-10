"""Error types shared across modules.

Every error the backend raises deliberately descends from :class:`HomeError`,
so that a boundary can tell an intentional refusal apart from a bug. Messages
live on the exception class rather than at the raise site.
"""


class HomeError(Exception):
    """Base class for every error the H.O.M.E. backend raises deliberately."""


class ConfigurationError(HomeError, ValueError):
    """The application is configured in a way it cannot run with."""


class UnknownTimeZoneError(ConfigurationError):
    """The configured household time zone is not a resolvable IANA zone."""

    def __init__(self, name: str) -> None:
        """Record which time zone name could not be resolved.

        Args:
            name: The unresolvable time zone name.
        """
        super().__init__(f"unknown household time zone: {name!r}")
        self.name = name
