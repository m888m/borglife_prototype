"""
Exceptions for Archon Adapter

Custom exceptions for different types of Archon service failures.
"""


class ArchonError(Exception):
    """Base exception for Archon adapter errors."""
    pass


class ArchonConnectionError(ArchonError):
    """Raised when unable to connect to Archon services."""
    pass


class ArchonTimeoutError(ArchonError):
    """Raised when Archon requests timeout."""
    pass


class ArchonServiceUnavailableError(ArchonError):
    """Raised when Archon services are unavailable."""
    pass


class ArchonVersionError(ArchonError):
    """Raised when Archon version is incompatible."""
    pass


class ArchonAuthenticationError(ArchonError):
    """Raised when authentication with Archon fails."""
    pass


class ArchonRateLimitError(ArchonError):
    """Raised when Archon rate limits are exceeded."""
    pass


class ArchonValidationError(ArchonError):
    """Raised when request validation fails."""
    pass