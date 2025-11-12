"""
Archon Service Adapter for BorgLife

This module provides a clean interface between BorgLife and Archon services,
enabling loose coupling and independent evolution of both systems.
"""

from .adapter import ArchonServiceAdapter
from .config import ArchonConfig
from .exceptions import (
    OrganUnavailableError,
    RateLimitExceededError,
    InsufficientFundsError,
    AllFallbacksFailedError
)
from .fallback_manager import OrganFallbackManager, FallbackLevel
from .cache_manager import CacheManager
from .docker_discovery import DockerMCPDiscovery
from .compatibility_matrix import DockerMCPCompatibilityMatrix
from .mcp_client import MCPClient
from .docker_mcp_auth import DockerMCPAuthManager
from .docker_monitor import DockerMCPMonitor
from .dependency_monitor import ArchonDependencyMonitor
from .rate_limiter import OrganRateLimiter

__all__ = [
    'ArchonServiceAdapter',
    'ArchonConfig',
    'OrganUnavailableError',
    'RateLimitExceededError',
    'InsufficientFundsError',
    'AllFallbacksFailedError',
    'OrganFallbackManager',
    'FallbackLevel',
    'CacheManager',
    'DockerMCPDiscovery',
    'DockerMCPCompatibilityMatrix',
    'MCPClient',
    'DockerMCPAuthManager',
    'DockerMCPMonitor',
    'ArchonDependencyMonitor',
    'OrganRateLimiter'
]