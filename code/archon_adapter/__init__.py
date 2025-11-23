"""
Archon Service Adapter for BorgLife

This module provides a clean interface between BorgLife and Archon services,
enabling loose coupling and independent evolution of both systems.
"""

from .adapter import ArchonServiceAdapter
from .cache_manager import CacheManager
from .compatibility_matrix import DockerMCPCompatibilityMatrix
from .config import ArchonConfig
from .dependency_monitor import ArchonDependencyMonitor
from .docker_discovery import DockerMCPDiscovery
from .docker_mcp_auth import DockerMCPAuthManager
from .docker_monitor import DockerMCPMonitor
from .exceptions import (AllFallbacksFailedError, InsufficientFundsError,
                         OrganUnavailableError, RateLimitExceededError)
from .fallback_manager import FallbackLevel, OrganFallbackManager
from .mcp_client import MCPClient
from .rate_limiter import OrganRateLimiter

__all__ = [
    "ArchonServiceAdapter",
    "ArchonConfig",
    "OrganUnavailableError",
    "RateLimitExceededError",
    "InsufficientFundsError",
    "AllFallbacksFailedError",
    "OrganFallbackManager",
    "FallbackLevel",
    "CacheManager",
    "DockerMCPDiscovery",
    "DockerMCPCompatibilityMatrix",
    "MCPClient",
    "DockerMCPAuthManager",
    "DockerMCPMonitor",
    "ArchonDependencyMonitor",
    "OrganRateLimiter",
]
