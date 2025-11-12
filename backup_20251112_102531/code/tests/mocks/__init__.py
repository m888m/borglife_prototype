# borglife_prototype/tests/mocks/__init__.py
"""
Mock infrastructure for BorgLife testing.

Provides comprehensive mocking for external services, Docker containers,
and network dependencies to enable reliable unit and integration testing.
"""

from .archon_mock import ArchonServiceMock
from .jam_mock import JAMInterfaceMock
from .docker_mock import DockerServiceMock

__all__ = [
    'ArchonServiceMock',
    'JAMInterfaceMock',
    'DockerServiceMock'
]