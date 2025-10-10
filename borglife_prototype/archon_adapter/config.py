"""
Configuration for Archon Adapter

Pydantic-based configuration with validation and environment variable support.
"""

from pydantic import BaseSettings, Field
from typing import Optional


class ArchonConfig(BaseSettings):
    """
    Configuration for Archon service connections.

    Supports environment variables and validation.
    """

    # Server endpoints
    archon_server_url: str = Field(
        default="http://archon-server:8181",
        description="Archon server base URL"
    )
    archon_mcp_url: str = Field(
        default="http://archon-mcp:8051",
        description="Archon MCP server URL"
    )
    archon_agents_url: str = Field(
        default="http://archon-agents:8052",
        description="Archon agents service URL"
    )

    # Timeouts and retries
    request_timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts"
    )
    retry_backoff: float = Field(
        default=1.0,
        description="Retry backoff multiplier"
    )

    # Health check settings
    health_check_interval: int = Field(
        default=30,
        description="Health check interval in seconds"
    )
    health_check_timeout: float = Field(
        default=5.0,
        description="Health check timeout in seconds"
    )

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Failures before opening circuit"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60,
        description="Seconds to wait before retrying"
    )

    # Version compatibility
    min_archon_version: str = Field(
        default="0.1.0",
        description="Minimum supported Archon version"
    )
    max_archon_version: str = Field(
        default="0.2.0",
        description="Maximum supported Archon version"
    )

    # Feature flags
    enable_rag: bool = Field(
        default=True,
        description="Enable RAG queries"
    )
    enable_tasks: bool = Field(
        default=True,
        description="Enable task management"
    )
    enable_crawling: bool = Field(
        default=True,
        description="Enable web crawling"
    )

    class Config:
        env_prefix = "ARCHON_"
        case_sensitive = False

    def get_service_urls(self) -> dict:
        """Get all service URLs as dictionary."""
        return {
            'server': self.archon_server_url,
            'mcp': self.archon_mcp_url,
            'agents': self.archon_agents_url
        }

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        feature_map = {
            'rag': self.enable_rag,
            'tasks': self.enable_tasks,
            'crawling': self.enable_crawling
        }
        return feature_map.get(feature, False)