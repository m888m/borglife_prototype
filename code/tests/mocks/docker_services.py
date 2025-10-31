# borglife_prototype/tests/mocks/docker_services.py
"""
Mock Docker services for development testing.

Provides mock implementations of Docker service operations that don't require
actual Docker daemon, enabling tests to run in environments without Docker.
"""

import asyncio
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock, AsyncMock


class MockDockerClient:
    """
    Mock Docker client that simulates Docker operations.

    Provides the same interface as docker.from_env() but with in-memory
    state management and predictable behavior.
    """

    def __init__(self):
        self.containers = MockContainerManager()
        self.images = MockImageManager()
        self.networks = MockNetworkManager()
        self.api = MockDockerAPI()

    def close(self):
        """Mock close method."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MockContainerManager:
    """Mock container management operations."""

    def __init__(self):
        self._containers: Dict[str, Dict[str, Any]] = {}

    def get(self, name: str) -> 'MockContainer':
        """Get a mock container by name."""
        if name not in self._containers:
            raise Exception(f"Container {name} not found")
        return MockContainer(name, self._containers[name])

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List['MockContainer']:
        """List mock containers with optional filtering."""
        containers = []
        for name, config in self._containers.items():
            container = MockContainer(name, config)
            if self._matches_filters(container, filters):
                containers.append(container)
        return containers

    def create(self, image: str, name: str, **kwargs) -> 'MockContainer':
        """Create a new mock container."""
        config = {
            'image': image,
            'name': name,
            'status': 'created',
            'created_at': asyncio.get_event_loop().time(),
            **kwargs
        }
        self._containers[name] = config
        return MockContainer(name, config)

    def _matches_filters(self, container: 'MockContainer', filters: Optional[Dict[str, Any]]) -> bool:
        """Check if container matches filters."""
        if not filters:
            return True

        for key, value in filters.items():
            if key == 'status' and container.status != value:
                return False
            elif key == 'name' and value not in container.name:
                return False

        return True


class MockContainer:
    """Mock Docker container."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self._config = config
        self.attrs = self._generate_attrs()

    @property
    def status(self) -> str:
        """Get container status."""
        return self._config.get('status', 'created')

    def start(self):
        """Start the container."""
        self._config['status'] = 'running'
        self._config['started_at'] = asyncio.get_event_loop().time()

    def stop(self):
        """Stop the container."""
        self._config['status'] = 'stopped'

    def remove(self):
        """Remove the container."""
        self._config['status'] = 'removed'

    def logs(self, **kwargs) -> str:
        """Get container logs."""
        return f"Mock logs for container {self.name}\nService started successfully\n"

    def exec_run(self, cmd: str, **kwargs) -> tuple:
        """Execute command in container."""
        # Mock successful execution
        return (0, f"Mock execution result for: {cmd}\n".encode(), b"")

    def stats(self, **kwargs):
        """Get container stats."""
        return {
            'cpu_stats': {'usage': {'total': 1000000}},
            'memory_stats': {'usage': 50 * 1024 * 1024},  # 50MB
            'networks': {'eth0': {'rx_bytes': 1024, 'tx_bytes': 512}}
        }

    def _generate_attrs(self) -> Dict[str, Any]:
        """Generate container attributes similar to Docker."""
        return {
            'Id': f'mock_{self.name}_id',
            'Name': f'/{self.name}',
            'State': {
                'Status': self._config.get('status', 'created'),
                'Running': self._config.get('status') == 'running',
                'StartedAt': '2025-10-30T12:00:00Z' if self._config.get('started_at') else None
            },
            'Config': {
                'Image': self._config.get('image', 'mock:latest'),
                'Env': self._config.get('environment', [])
            }
        }


class MockImageManager:
    """Mock image management operations."""

    def __init__(self):
        self._images: Dict[str, Dict[str, Any]] = {}

    def pull(self, image: str, **kwargs):
        """Pull a mock image."""
        self._images[image] = {
            'id': f'mock_{image.replace(":", "_")}_id',
            'tags': [image],
            'size': 100 * 1024 * 1024  # 100MB
        }

    def list(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List mock images."""
        if name:
            return [self._images.get(name, {})]
        return list(self._images.values())


class MockNetworkManager:
    """Mock network management operations."""

    def __init__(self):
        self._networks: Dict[str, Dict[str, Any]] = {}

    def create(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a mock network."""
        network = {
            'id': f'mock_network_{name}_id',
            'name': name,
            'driver': kwargs.get('driver', 'bridge'),
            'created': asyncio.get_event_loop().time()
        }
        self._networks[name] = network
        return network

    def get(self, name: str) -> Dict[str, Any]:
        """Get a mock network."""
        return self._networks.get(name, {})


class MockDockerAPI:
    """Mock Docker API operations."""

    def info(self) -> Dict[str, Any]:
        """Get mock Docker info."""
        return {
            'ID': 'mock_docker_id',
            'Containers': 5,
            'ContainersRunning': 3,
            'Images': 10,
            'Driver': 'mock',
            'Architecture': 'x86_64'
        }

    def ping(self) -> bool:
        """Mock ping operation."""
        return True


# Global mock client instance
_mock_client = None


def from_env() -> MockDockerClient:
    """Mock docker.from_env() function."""
    global _mock_client
    if _mock_client is None:
        _mock_client = MockDockerClient()
    return _mock_client


def reset_mock_client():
    """Reset the global mock client for testing."""
    global _mock_client
    _mock_client = None