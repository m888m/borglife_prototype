# borglife_prototype/archon_adapter/config.py
"""
Configuration management for Archon adapter.

Handles environment variables, service discovery, and configuration validation.
"""

import logging
import os
from typing import Optional

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ArchonConfig(BaseModel):
    """Configuration for Archon service integration."""

    # Service URLs
    archon_server_url: str = Field(default="http://archon-server:8181")
    archon_mcp_url: str = Field(default="http://archon-mcp:8051")
    archon_agents_url: str = Field(default="http://archon-agents:8052")

    # Supabase (shared with Archon)
    supabase_url: str = Field(default="")
    supabase_service_key: str = Field(default="")

    @property
    def supabase_client(self):
        """Get Supabase client instance."""
        try:
            # Skip if credentials not configured
            if not self.supabase_url or not self.supabase_service_key:
                logger.warning(
                    "Supabase credentials not configured - using mock client"
                )
                raise ValueError("Supabase not configured")

            from supabase import create_client

            return create_client(self.supabase_url, self.supabase_service_key)
        except (ImportError, ValueError, Exception) as e:
            # Mock client for testing or when Supabase unavailable
            logger.debug(f"Using mock Supabase client: {e}")

            class MockSupabaseClient:
                def table(self, name):
                    return self

                def select(self, *args):
                    return self

                def insert(self, *args):
                    return self

                def update(self, *args):
                    return self

                def delete(self, *args):
                    return self

                def execute(self):
                    return {"data": [], "error": None}

            return MockSupabaseClient()

    # Docker MCP Configuration
    enable_docker_mcp_organs: bool = Field(default=True)
    docker_mcp_health_timeout: int = Field(default=30)
    docker_mcp_retry_attempts: int = Field(default=3)

    # Caching
    redis_url: str = Field(default="redis://localhost:6379")
    cache_default_ttl: int = Field(default=3600)

    # Rate Limiting
    rate_limit_redis_url: str = Field(default="redis://localhost:6379")

    # Circuit Breaker
    circuit_breaker_failure_threshold: int = Field(default=5)
    circuit_breaker_reset_timeout: int = Field(default=300)  # 5 minutes

    # Retry Configuration
    retry_max_attempts: int = Field(default=3)
    retry_backoff_multiplier: float = Field(default=1.0)
    retry_backoff_max: float = Field(default=10.0)

    # Logging
    log_level: str = Field(default="INFO")

    # Version compatibility
    min_archon_version: str = Field(default="0.1.0")
    max_archon_version: str = Field(default="0.2.0")

    @validator("archon_server_url", "archon_mcp_url", "archon_agents_url")
    def validate_urls(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @validator("supabase_url")
    def validate_supabase_url(cls, v):
        """Validate Supabase URL."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Supabase URL must start with http:// or https://")
        return v

    @classmethod
    def from_env(cls) -> "ArchonConfig":
        """Create configuration from environment variables."""
        return cls(
            archon_server_url=os.getenv(
                "ARCHON_SERVER_URL", "http://archon-server:8181"
            ),
            archon_mcp_url=os.getenv("ARCHON_MCP_URL", "http://archon-mcp:8051"),
            archon_agents_url=os.getenv(
                "ARCHON_AGENTS_URL", "http://archon-agents:8052"
            ),
            supabase_url=os.getenv("ARCHON_SUPABASE_URL", os.getenv("SUPABASE_URL", "")),
            supabase_service_key=os.getenv("ARCHON_SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_SERVICE_KEY", "")),
            enable_docker_mcp_organs=os.getenv(
                "ENABLE_DOCKER_MCP_ORGANS", "true"
            ).lower()
            == "true",
            docker_mcp_health_timeout=int(os.getenv("DOCKER_MCP_HEALTH_TIMEOUT", "30")),
            docker_mcp_retry_attempts=int(os.getenv("DOCKER_MCP_RETRY_ATTEMPTS", "3")),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            cache_default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
            rate_limit_redis_url=os.getenv(
                "RATE_LIMIT_REDIS_URL", "redis://localhost:6379"
            ),
            circuit_breaker_failure_threshold=int(
                os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")
            ),
            circuit_breaker_reset_timeout=int(
                os.getenv("CIRCUIT_BREAKER_RESET_TIMEOUT", "300")
            ),
            retry_max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
            retry_backoff_multiplier=float(
                os.getenv("RETRY_BACKOFF_MULTIPLIER", "1.0")
            ),
            retry_backoff_max=float(os.getenv("RETRY_BACKOFF_MAX", "10.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            min_archon_version=os.getenv("MIN_ARCHON_VERSION", "0.1.0"),
            max_archon_version=os.getenv("MAX_ARCHON_VERSION", "0.2.0"),
        )

    def validate(self) -> bool:
        """
        Validate configuration completeness.

        Returns:
            True if configuration is valid
        """
        errors = []

        # Check required URLs
        if not self.archon_server_url:
            errors.append("Archon server URL is required")

        if not self.archon_mcp_url:
            errors.append("Archon MCP URL is required")

        if not self.archon_agents_url:
            errors.append("Archon agents URL is required")

        # Check Supabase if Docker MCP is enabled
        if self.enable_docker_mcp_organs:
            if not self.supabase_url:
                errors.append("Supabase URL is required for Docker MCP organs")

            if not self.supabase_service_key:
                errors.append("Supabase service key is required for Docker MCP organs")

        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False

        logger.info("Configuration validation passed")
        return True

    def get_service_endpoints(self) -> dict:
        """Get all service endpoints."""
        return {
            "server": self.archon_server_url,
            "mcp": self.archon_mcp_url,
            "agents": self.archon_agents_url,
        }

    def is_docker_mcp_enabled(self) -> bool:
        """Check if Docker MCP organs are enabled."""
        return self.enable_docker_mcp_organs

    def get_retry_config(self) -> dict:
        """Get retry configuration."""
        return {
            "max_attempts": self.retry_max_attempts,
            "backoff_multiplier": self.retry_backoff_multiplier,
            "backoff_max": self.retry_backoff_max,
        }

    def get_circuit_breaker_config(self) -> dict:
        """Get circuit breaker configuration."""
        return {
            "failure_threshold": self.circuit_breaker_failure_threshold,
            "reset_timeout": self.circuit_breaker_reset_timeout,
        }

    def get_cache_config(self) -> dict:
        """Get cache configuration."""
        return {"redis_url": self.redis_url, "default_ttl": self.cache_default_ttl}

    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration."""
        return {"redis_url": self.rate_limit_redis_url}


class BorglifeConfig(BaseModel):
    """Configuration for Borglife services."""

    # Service ports
    borglife_mcp_port: int = Field(default=8053)
    borglife_agent_port: int = Field(default=8054)
    borglife_ui_port: int = Field(default=8501)

    # Blockchain
    kusama_rpc_url: str = Field(default="wss://kusama-rpc.polkadot.io")
    borg_wallet_seed: str = Field(default="")
    jam_mock_mode: bool = Field(default=True)

    # AI/ML
    openai_api_key: str = Field(default="")
    default_llm_model: str = Field(default="gpt-4")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536)

    # Wealth tracking
    initial_borg_wealth: float = Field(default=1.0)  # 1 DOT
    max_wealth_per_borg: float = Field(default=100.0)  # 100 DOT

    # Task execution
    max_task_execution_time: int = Field(default=300)  # 5 minutes
    max_concurrent_tasks: int = Field(default=10)

    # Reputation system
    reputation_update_interval: int = Field(default=3600)  # 1 hour
    min_feedbacks_for_reputation: int = Field(default=3)

    @classmethod
    def from_env(cls) -> "BorglifeConfig":
        """Create configuration from environment variables."""
        return cls(
            borglife_mcp_port=int(os.getenv("BORGLIFE_MCP_PORT", "8053")),
            borglife_agent_port=int(os.getenv("BORGLIFE_AGENT_PORT", "8054")),
            borglife_ui_port=int(os.getenv("BORGLIFE_UI_PORT", "8501")),
            kusama_rpc_url=os.getenv("KUSAMA_RPC_URL", "wss://kusama-rpc.polkadot.io"),
            borg_wallet_seed=os.getenv("BORG_WALLET_SEED", ""),
            jam_mock_mode=os.getenv("JAM_MOCK_MODE", "true").lower() == "true",
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            default_llm_model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
            initial_borg_wealth=float(os.getenv("INITIAL_BORG_WEALTH", "1.0")),
            max_wealth_per_borg=float(os.getenv("MAX_WEALTH_PER_BORG", "100.0")),
            max_task_execution_time=int(os.getenv("MAX_TASK_EXECUTION_TIME", "300")),
            max_concurrent_tasks=int(os.getenv("MAX_CONCURRENT_TASKS", "10")),
            reputation_update_interval=int(
                os.getenv("REPUTATION_UPDATE_INTERVAL", "3600")
            ),
            min_feedbacks_for_reputation=int(
                os.getenv("MIN_FEEDBACKS_FOR_REPUTATION", "3")
            ),
        )

    def validate(self) -> bool:
        """
        Validate Borglife configuration.

        Returns:
            True if configuration is valid
        """
        errors = []

        # Check required API keys
        if not self.openai_api_key:
            errors.append("OpenAI API key is required")

        # Check wallet seed if not in mock mode
        if not self.jam_mock_mode and not self.borg_wallet_seed:
            errors.append("Borg wallet seed is required when not in JAM mock mode")

        # Validate ports
        ports = [
            self.borglife_mcp_port,
            self.borglife_agent_port,
            self.borglife_ui_port,
        ]
        if len(set(ports)) != len(ports):
            errors.append("All service ports must be unique")

        for port_name, port in [
            ("MCP", self.borglife_mcp_port),
            ("Agent", self.borglife_agent_port),
            ("UI", self.borglife_ui_port),
        ]:
            if not (1024 <= port <= 65535):
                errors.append(
                    f"{port_name} port {port} is not in valid range (1024-65535)"
                )

        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False

        logger.info("Borglife configuration validation passed")
        return True
