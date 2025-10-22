# borglife_prototype/archon_adapter/exceptions.py
"""
Custom exceptions for Archon adapter.

Provides specific exception types for different failure scenarios
to enable proper error handling and fallback strategies.
"""

from typing import Optional, Dict, Any

class ArchonError(Exception):
    """Base exception for Archon adapter errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ServiceUnavailableError(ArchonError):
    """Raised when an Archon service is unavailable."""

    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        message = f"Archon service '{service}' is unavailable"
        super().__init__(message, details)
        self.service = service

class CircuitBreakerOpenError(ServiceUnavailableError):
    """Raised when circuit breaker is open for a service."""

    def __init__(self, service: str, failures: int, last_failure_time: Optional[str] = None):
        details = {
            'failures': failures,
            'last_failure_time': last_failure_time
        }
        super().__init__(service, details)
        self.failures = failures
        self.last_failure_time = last_failure_time

class AuthenticationError(ArchonError):
    """Raised when authentication fails."""

    def __init__(self, service: str, message: str = "Authentication failed"):
        super().__init__(f"{service}: {message}")
        self.service = service

class AuthorizationError(ArchonError):
    """Raised when authorization fails."""

    def __init__(self, service: str, resource: str, message: str = "Authorization failed"):
        full_message = f"{service}: {message} for resource '{resource}'"
        super().__init__(full_message)
        self.service = service
        self.resource = resource

class RateLimitExceededError(ArchonError):
    """Raised when rate limit is exceeded."""

    def __init__(self, service: str, limit: int, reset_time: Optional[str] = None):
        message = f"Rate limit exceeded for {service} (limit: {limit})"
        details = {'limit': limit, 'reset_time': reset_time}
        super().__init__(message, details)
        self.service = service
        self.limit = limit
        self.reset_time = reset_time

class TimeoutError(ArchonError):
    """Raised when a request times out."""

    def __init__(self, service: str, timeout: float, operation: str = "operation"):
        message = f"{service}: {operation} timed out after {timeout}s"
        details = {'timeout': timeout, 'operation': operation}
        super().__init__(message, details)
        self.service = service
        self.timeout = timeout
        self.operation = operation

class ValidationError(ArchonError):
    """Raised when request validation fails."""

    def __init__(self, service: str, field: str, value: Any, reason: str):
        message = f"{service}: Validation failed for field '{field}': {reason}"
        details = {'field': field, 'value': value, 'reason': reason}
        super().__init__(message, details)
        self.service = service
        self.field = field
        self.value = value
        self.reason = reason

class OrganNotFoundError(ArchonError):
    """Raised when a Docker MCP organ is not found."""

    def __init__(self, organ_name: str):
        message = f"Docker MCP organ '{organ_name}' not found"
        super().__init__(message)
        self.organ_name = organ_name

class OrganUnavailableError(ArchonError):
    """Raised when a Docker MCP organ is unavailable."""

    def __init__(self, organ_name: str, reason: Optional[str] = None):
        message = f"Docker MCP organ '{organ_name}' is unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message)
        self.organ_name = organ_name
        self.reason = reason

class AllFallbacksFailedError(ArchonError):
    """Raised when all fallback strategies have been exhausted."""

    def __init__(self, message: str, tried_fallbacks: Optional[list] = None):
        super().__init__(message)
        self.tried_fallbacks = tried_fallbacks or []

class InsufficientFundsError(ArchonError):
    """Raised when borg has insufficient wealth for an operation."""

    def __init__(self, borg_id: str, required: float, available: float, currency: str = "DOT"):
        message = f"Borg {borg_id} has insufficient funds. Required: {required} {currency}, Available: {available} {currency}"
        details = {
            'borg_id': borg_id,
            'required': required,
            'available': available,
            'currency': currency
        }
        super().__init__(message, details)
        self.borg_id = borg_id
        self.required = required
        self.available = available
        self.currency = currency

class DNAParsingError(ArchonError):
    """Raised when DNA parsing fails."""

    def __init__(self, dna_source: str, reason: str, line_number: Optional[int] = None):
        message = f"DNA parsing failed for {dna_source}: {reason}"
        details = {'dna_source': dna_source, 'reason': reason, 'line_number': line_number}
        super().__init__(message, details)
        self.dna_source = dna_source
        self.reason = reason
        self.line_number = line_number

class PhenotypeBuildError(ArchonError):
    """Raised when phenotype building fails."""

    def __init__(self, borg_id: str, reason: str, component: Optional[str] = None):
        message = f"Phenotype build failed for borg {borg_id}"
        if component:
            message += f" at component '{component}'"
        message += f": {reason}"
        details = {'borg_id': borg_id, 'reason': reason, 'component': component}
        super().__init__(message, details)
        self.borg_id = borg_id
        self.reason = reason
        self.component = component

class VersionCompatibilityError(ArchonError):
    """Raised when service versions are incompatible."""

    def __init__(self, service: str, current_version: str, required_version: str):
        message = f"{service} version {current_version} is incompatible (requires {required_version})"
        details = {
            'service': service,
            'current_version': current_version,
            'required_version': required_version
        }
        super().__init__(message, details)
        self.service = service
        self.current_version = current_version
        self.required_version = required_version

class ConfigurationError(ArchonError):
    """Raised when configuration is invalid."""

    def __init__(self, component: str, issues: list):
        message = f"Configuration error in {component}: {', '.join(issues)}"
        details = {'component': component, 'issues': issues}
        super().__init__(message, details)
        self.component = component
        self.issues = issues

class CacheError(ArchonError):
    """Raised when caching operations fail."""

    def __init__(self, operation: str, key: str, reason: str):
        message = f"Cache {operation} failed for key '{key}': {reason}"
        details = {'operation': operation, 'key': key, 'reason': reason}
        super().__init__(message, details)
        self.operation = operation
        self.key = key
        self.reason = reason

class DatabaseError(ArchonError):
    """Raised when database operations fail."""

    def __init__(self, operation: str, table: str, reason: str):
        message = f"Database {operation} failed on table '{table}': {reason}"
        details = {'operation': operation, 'table': table, 'reason': reason}
        super().__init__(message, details)
        self.operation = operation
        self.table = table
        self.reason = reason

class SecurityError(ArchonError):
    """Raised when security violations are detected."""

    def __init__(self, violation_type: str, details: Dict[str, Any]):
        message = f"Security violation: {violation_type}"
        super().__init__(message, details)
        self.violation_type = violation_type

# Exception hierarchy for easier catching
ARCHON_EXCEPTIONS = (
    ArchonError,
    ServiceUnavailableError,
    CircuitBreakerOpenError,
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
    TimeoutError,
    ValidationError,
    OrganNotFoundError,
    OrganUnavailableError,
    AllFallbacksFailedError,
    InsufficientFundsError,
    DNAParsingError,
    PhenotypeBuildError,
    VersionCompatibilityError,
    ConfigurationError,
    CacheError,
    DatabaseError,
    SecurityError,
)