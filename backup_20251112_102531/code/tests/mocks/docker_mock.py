# borglife_prototype/tests/mocks/docker_mock.py
"""
Mock implementation of Docker service interactions for testing.

Provides deterministic responses for Docker container operations without
requiring actual Docker daemon connections.
"""

import asyncio
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock


class DockerServiceMock:
    """
    Mock Docker service for testing container operations.

    Simulates Docker container lifecycle, health checks, and service
    discovery with configurable behavior for different test scenarios.
    """

    def __init__(self):
        self.containers: Dict[str, Dict[str, Any]] = {}
        self.images: Dict[str, Dict[str, Any]] = {}
        self.networks: Dict[str, Dict[str, Any]] = {}
        self.call_history: List[Dict[str, Any]] = []
        self.should_fail = False
        self.fail_on_next_calls = 0

    def create_container(self, name: str, image: str, **kwargs) -> Dict[str, Any]:
        """Create a mock container."""
        self._record_call('create_container', name=name, image=image, **kwargs)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: create_container {name}")

        container = {
            'id': f'mock_container_{name}_{len(self.containers)}',
            'name': name,
            'image': image,
            'status': 'created',
            'created': asyncio.get_event_loop().time(),
            'config': kwargs,
            'ports': kwargs.get('ports', {}),
            'env': kwargs.get('environment', [])
        }

        self.containers[name] = container
        return container

    def start_container(self, name: str) -> bool:
        """Start a mock container."""
        self._record_call('start_container', name=name)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: start_container {name}")

        if name not in self.containers:
            raise Exception(f"Container {name} not found")

        self.containers[name]['status'] = 'running'
        self.containers[name]['started_at'] = asyncio.get_event_loop().time()
        return True

    def stop_container(self, name: str) -> bool:
        """Stop a mock container."""
        self._record_call('stop_container', name=name)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: stop_container {name}")

        if name not in self.containers:
            raise Exception(f"Container {name} not found")

        self.containers[name]['status'] = 'stopped'
        return True

    def remove_container(self, name: str) -> bool:
        """Remove a mock container."""
        self._record_call('remove_container', name=name)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: remove_container {name}")

        if name not in self.containers:
            raise Exception(f"Container {name} not found")

        del self.containers[name]
        return True

    def get_container_status(self, name: str) -> Dict[str, Any]:
        """Get mock container status."""
        self._record_call('get_container_status', name=name)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: get_container_status {name}")

        if name not in self.containers:
            raise Exception(f"Container {name} not found")

        container = self.containers[name].copy()

        # Add uptime calculation
        if container.get('started_at'):
            uptime = asyncio.get_event_loop().time() - container['started_at']
            container['uptime'] = uptime

        return container

    def list_containers(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List mock containers with optional filtering."""
        self._record_call('list_containers', filters=filters)

        if self._should_fail():
            raise Exception("Mock Docker failure: list_containers")

        containers = list(self.containers.values())

        if filters:
            # Apply basic filtering
            if 'status' in filters:
                containers = [c for c in containers if c['status'] == filters['status']]
            if 'name' in filters:
                containers = [c for c in containers if filters['name'] in c['name']]

        return containers

    def get_container_logs(self, name: str, tail: int = 100) -> List[str]:
        """Get mock container logs."""
        self._record_call('get_container_logs', name=name, tail=tail)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: get_container_logs {name}")

        if name not in self.containers:
            raise Exception(f"Container {name} not found")

        # Return mock logs
        return [
            f"Mock log line 1 for {name}",
            f"Mock log line 2 for {name}",
            f"Container {name} started successfully",
            f"Service running on port {self.containers[name].get('ports', {}).get('8080/tcp', '8080')}"
        ][:tail]

    def execute_in_container(self, name: str, command: str) -> Dict[str, Any]:
        """Execute command in mock container."""
        self._record_call('execute_in_container', name=name, command=command)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: execute_in_container {name}")

        if name not in self.containers:
            raise Exception(f"Container {name} not found")

        # Mock command execution results
        mock_results = {
            'echo hello': {'exit_code': 0, 'output': 'hello\n'},
            'ls -la': {'exit_code': 0, 'output': 'drwxr-xr-x 1 user user 4096 Oct 30 12:00 .\n'},
            'health_check': {'exit_code': 0, 'output': 'Service is healthy\n'},
            'failing_command': {'exit_code': 1, 'output': 'Command failed\n'}
        }

        result = mock_results.get(command, {'exit_code': 0, 'output': f'Mock execution of: {command}\n'})
        return result

    def get_container_stats(self, name: str) -> Dict[str, Any]:
        """Get mock container statistics."""
        self._record_call('get_container_stats', name=name)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: get_container_stats {name}")

        if name not in self.containers:
            raise Exception(f"Container {name} not found")

        return {
            'cpu_percent': 15.5,
            'memory_usage': 256 * 1024 * 1024,  # 256MB
            'memory_limit': 1024 * 1024 * 1024,  # 1GB
            'network_rx': 1024 * 1024,  # 1MB
            'network_tx': 512 * 1024,   # 512KB
            'block_read': 0,
            'block_write': 1024 * 1024  # 1MB
        }

    def create_network(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a mock network."""
        self._record_call('create_network', name=name, **kwargs)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: create_network {name}")

        network = {
            'id': f'mock_network_{name}_{len(self.networks)}',
            'name': name,
            'driver': kwargs.get('driver', 'bridge'),
            'created': asyncio.get_event_loop().time()
        }

        self.networks[name] = network
        return network

    def connect_container_to_network(self, container_name: str, network_name: str) -> bool:
        """Connect mock container to network."""
        self._record_call('connect_container_to_network', container_name=container_name, network_name=network_name)

        if self._should_fail():
            raise Exception(f"Mock Docker failure: connect_container_to_network")

        if container_name not in self.containers:
            raise Exception(f"Container {container_name} not found")

        if network_name not in self.networks:
            raise Exception(f"Network {network_name} not found")

        # Mock successful connection
        return True

    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """Get mock service health status."""
        self._record_call('get_service_health', service_name=service_name)

        if self._should_fail():
            return {'status': 'unhealthy', 'error': f'Mock failure for {service_name}'}

        # Mock health based on container status
        container_name = f"archon-{service_name}"
        if container_name in self.containers:
            status = self.containers[container_name]['status']
            if status == 'running':
                return {
                    'status': 'healthy',
                    'uptime': asyncio.get_event_loop().time() - self.containers[container_name].get('started_at', 0),
                    'version': '1.0.0'
                }

        return {
            'status': 'stopped',
            'uptime': 0,
            'message': f'Service {service_name} is not running'
        }

    def _record_call(self, method: str, **kwargs):
        """Record method call for testing verification."""
        self.call_history.append({
            'method': method,
            'args': kwargs,
            'timestamp': asyncio.get_event_loop().time()
        })

    def _should_fail(self) -> bool:
        """Determine if current call should fail."""
        if self.fail_on_next_calls > 0:
            self.fail_on_next_calls -= 1
            return True
        return self.should_fail

    def configure_failure(self, should_fail: bool = True, fail_next_n: int = 0):
        """Configure mock to fail on subsequent calls."""
        self.should_fail = should_fail
        self.fail_on_next_calls = fail_next_n

    def reset_state(self):
        """Reset mock state for testing."""
        self.containers.clear()
        self.images.clear()
        self.networks.clear()
        self.call_history.clear()
        self.should_fail = False
        self.fail_on_next_calls = 0

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get recorded call history."""
        return self.call_history.copy()

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reset_state()