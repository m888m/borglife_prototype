# borglife_prototype/tests/config/test_env.py
"""
Test environment configuration and detection.

Provides utilities for detecting test environment, configuring test-specific
settings, and managing environment variables for different test scenarios.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional


class TestEnvironment:
    """
    Test environment configuration manager.

    Detects and configures test environment settings, provides environment-specific
    fixtures and configurations for reliable testing across different contexts.
    """

    def __init__(self):
        self._env_cache: Dict[str, Any] = {}
        self._detect_environment()

    def _detect_environment(self):
        """Detect current test environment."""
        # Check for CI environment
        self.is_ci = self._is_ci_environment()

        # Check for Docker environment
        self.is_docker = self._is_docker_environment()

        # Check for local development
        self.is_local = not self.is_ci and not self.is_docker

        # Determine test scope
        self.test_scope = os.getenv("TEST_SCOPE", "unit")  # unit, integration, e2e

        # Determine mock level
        self.mock_level = os.getenv("MOCK_LEVEL", "full")  # none, partial, full

    def _is_ci_environment(self) -> bool:
        """Detect if running in CI environment."""
        ci_indicators = [
            "CI",
            "CONTINUOUS_INTEGRATION",
            "BUILD_NUMBER",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "JENKINS_HOME",
        ]
        return any(os.getenv(indicator) for indicator in ci_indicators)

    def _is_docker_environment(self) -> bool:
        """Detect if running in Docker environment."""
        docker_indicators = [
            Path("/.dockerenv").exists(),
            os.getenv("DOCKER_CONTAINER") is not None,
            os.path.exists("/proc/1/cgroup")
            and "docker" in open("/proc/1/cgroup").read(),
        ]
        return any(docker_indicators)

    def get_service_urls(self) -> Dict[str, str]:
        """Get service URLs based on environment."""
        if self.is_ci:
            return {
                "archon_server": "http://archon-server:8181",
                "archon_mcp": "http://archon-mcp:8051",
                "archon_agents": "http://archon-agents:8052",
            }
        elif self.is_docker:
            return {
                "archon_server": "http://host.docker.internal:8181",
                "archon_mcp": "http://host.docker.internal:8051",
                "archon_agents": "http://host.docker.internal:8052",
            }
        else:
            # Local development
            return {
                "archon_server": "http://localhost:8181",
                "archon_mcp": "http://localhost:8051",
                "archon_agents": "http://localhost:8052",
            }

    def should_use_mocks(self, service_name: str) -> bool:
        """Determine if mocks should be used for a service."""
        if self.mock_level == "none":
            return False
        elif self.mock_level == "full":
            return True
        else:  # partial
            # Use mocks for external services in local development
            external_services = ["archon_mcp", "archon_agents"]
            return service_name in external_services or self.is_local

    def get_test_timeout(self, test_type: str = "unit") -> int:
        """Get appropriate timeout for test type."""
        timeouts = {"unit": 30, "integration": 120, "e2e": 300}
        return timeouts.get(test_type, 60)

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for tests."""
        if self.is_ci:
            return {
                "host": os.getenv("DB_HOST", "postgres"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "database": os.getenv("DB_NAME", "archon_test"),
                "user": os.getenv("DB_USER", "archon"),
                "password": os.getenv("DB_PASSWORD", "archon"),
            }
        else:
            # Use SQLite for local testing
            return {"type": "sqlite", "database": ":memory:"}

    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration for tests."""
        if self.is_ci:
            return {
                "type": "redis",
                "host": os.getenv("REDIS_HOST", "redis"),
                "port": int(os.getenv("REDIS_PORT", "6379")),
            }
        else:
            # Use in-memory cache for local testing
            return {"type": "memory"}

    def setup_environment_variables(self):
        """Setup environment variables for testing."""
        # Service URLs
        urls = self.get_service_urls()
        for service, url in urls.items():
            env_key = f"{service.upper().replace('_', '')}_URL"
            os.environ[env_key] = url

        # Test-specific variables
        os.environ["TEST_ENVIRONMENT"] = "true"
        os.environ["MOCK_EXTERNAL_SERVICES"] = str(self.should_use_mocks("all"))
        os.environ["TEST_TIMEOUT_MULTIPLIER"] = "1.0"

        # Database config
        if not self.is_ci:
            os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    def get_fixture_config(self) -> Dict[str, Any]:
        """Get configuration for test fixtures."""
        return {
            "use_real_services": not self.should_use_mocks("all"),
            "cleanup_after_test": True,
            "isolate_tests": True,
            "parallel_execution": self.is_ci,  # Enable parallel in CI
            "capture_logs": True,
            "record_metrics": self.is_ci,
        }

    def get_mock_config(self) -> Dict[str, Any]:
        """Get configuration for mock services."""
        return {
            "archon_mock": {
                "enabled": self.should_use_mocks("archon_server"),
                "record_calls": True,
                "fail_on_unexpected_calls": False,
            },
            "jam_mock": {
                "enabled": self.should_use_mocks("jam"),
                "initial_balance": 100.0,
                "track_transactions": True,
            },
            "docker_mock": {
                "enabled": self.should_use_mocks("docker"),
                "simulate_failures": False,
                "record_operations": True,
            },
        }

    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available in current environment."""
        if self.is_local and service_name in ["archon_mcp", "archon_agents"]:
            # These services might not be running locally
            return False
        return True

    def get_environment_info(self) -> Dict[str, Any]:
        """Get comprehensive environment information."""
        return {
            "is_ci": self.is_ci,
            "is_docker": self.is_docker,
            "is_local": self.is_local,
            "test_scope": self.test_scope,
            "mock_level": self.mock_level,
            "service_urls": self.get_service_urls(),
            "database_config": self.get_database_config(),
            "cache_config": self.get_cache_config(),
            "fixture_config": self.get_fixture_config(),
            "mock_config": self.get_mock_config(),
        }


# Global test environment instance
test_env = TestEnvironment()


def get_test_environment() -> TestEnvironment:
    """Get the global test environment instance."""
    return test_env


def setup_test_environment():
    """Setup test environment for pytest."""
    test_env.setup_environment_variables()


def is_ci() -> bool:
    """Check if running in CI environment."""
    return test_env.is_ci


def is_docker() -> bool:
    """Check if running in Docker environment."""
    return test_env.is_docker


def is_local() -> bool:
    """Check if running in local development environment."""
    return test_env.is_local


def should_mock_service(service_name: str) -> bool:
    """Check if a service should be mocked."""
    return test_env.should_use_mocks(service_name)
