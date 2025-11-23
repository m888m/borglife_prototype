"""
Service Integration Tests for BorgLife Phase 1 E2E Testing

Tests Archon service connectivity, MCP tool availability, and health checks.
Validates that BorgLife components can successfully interact with Archon infrastructure.
"""

import asyncio
import json
import os
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

# Test imports - these will be available in Docker environment
try:
    from archon_adapter.adapter import ArchonAdapter
    from demo_scenarios import DemoScenarios
    from jam_mock.interface import JAMInterface

    IMPORTS_AVAILABLE = True
except ImportError:
    # Mock for development environment
    ArchonAdapter = MagicMock
    JAMInterface = MagicMock
    DemoScenarios = MagicMock
    IMPORTS_AVAILABLE = False


class TestServiceIntegration:
    """Test suite for service integration and connectivity."""

    @pytest.fixture
    async def archon_adapter(self):
        """Fixture for Archon adapter instance."""
        if not IMPORTS_AVAILABLE:
            # Mock adapter for development
            adapter = AsyncMock()
            adapter.health_check.return_value = {
                "status": "healthy",
                "services": ["mcp", "database"],
            }
            adapter.get_mcp_tools.return_value = [
                "rag_query",
                "create_task",
                "search_code",
            ]
            yield adapter
        else:
            # Real adapter for Docker environment
            adapter = ArchonAdapter()
            await adapter.initialize()
            yield adapter
            await adapter.cleanup()

    @pytest.fixture
    async def jam_interface(self):
        """Fixture for JAM interface instance."""
        if not IMPORTS_AVAILABLE:
            # Mock interface for development
            interface = AsyncMock()
            interface.get_balance.return_value = 1.5
            interface.transfer.return_value = {
                "tx_hash": "0x123",
                "status": "confirmed",
            }
            yield interface
        else:
            # Real interface for Docker environment
            interface = JAMInterface()
            await interface.connect()
            yield interface
            await interface.disconnect()

    @pytest.mark.asyncio
    async def test_archon_health_check(self, archon_adapter):
        """Test that Archon services are healthy and responsive."""
        health_status = await archon_adapter.health_check()

        assert health_status["status"] == "healthy"
        assert "services" in health_status
        assert "mcp" in health_status["services"]
        assert "database" in health_status["services"]

    @pytest.mark.asyncio
    async def test_mcp_tools_available(self, archon_adapter):
        """Test that required MCP tools are available."""
        tools = await archon_adapter.get_mcp_tools()

        required_tools = ["rag_query", "create_task", "search_code"]
        for tool in required_tools:
            assert tool in tools, f"Required MCP tool '{tool}' not available"

    @pytest.mark.asyncio
    async def test_jam_balance_check(self, jam_interface):
        """Test JAM interface balance checking."""
        balance = await jam_interface.get_balance()

        assert isinstance(balance, (int, float))
        assert balance >= 0

    @pytest.mark.asyncio
    async def test_jam_transfer_simulation(self, jam_interface):
        """Test JAM transfer functionality (simulation mode)."""
        transfer_result = await jam_interface.transfer(
            to_address="test_address", amount=0.1, memo="test transfer"
        )

        assert "tx_hash" in transfer_result
        assert "status" in transfer_result
        assert transfer_result["status"] in ["confirmed", "pending", "simulated"]

    @pytest.mark.asyncio
    async def test_demo_scenarios_initialization(self):
        """Test that demo scenarios can be initialized."""
        if not IMPORTS_AVAILABLE:
            # Mock test for development
            scenarios = AsyncMock()
            scenarios.load_scenarios.return_value = [
                "scenario1",
                "scenario2",
                "scenario3",
            ]
            scenarios.validate_scenarios.return_value = True
        else:
            # Real test for Docker environment
            scenarios = DemoScenarios()
            await scenarios.initialize()

        loaded_scenarios = await scenarios.load_scenarios()
        assert len(loaded_scenarios) > 0

        is_valid = await scenarios.validate_scenarios()
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, archon_adapter):
        """Test circuit breaker reset functionality."""
        # Simulate circuit breaker trip
        await archon_adapter.trigger_circuit_breaker()

        # Verify it's tripped
        status = await archon_adapter.get_circuit_breaker_status()
        assert status["state"] == "open"

        # Reset circuit breaker
        await archon_adapter.reset_circuit_breaker()

        # Verify it's reset
        status = await archon_adapter.get_circuit_breaker_status()
        assert status["state"] == "closed"

    @pytest.mark.asyncio
    async def test_service_recovery_after_failure(self, archon_adapter):
        """Test service recovery after simulated failure."""
        # Simulate service failure
        await archon_adapter.simulate_service_failure()

        # Verify service is marked as failed
        health = await archon_adapter.health_check()
        assert health["status"] == "degraded"

        # Wait for recovery
        await asyncio.sleep(2)

        # Verify service recovered
        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_concurrent_service_requests(self, archon_adapter):
        """Test handling of concurrent service requests."""

        async def make_request(request_id: int):
            return await archon_adapter.make_request(f"test_request_{request_id}")

        # Make 10 concurrent requests
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert len(results) == 10
        for result in results:
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_async_initialization_pattern(self, archon_adapter):
        """Test proper async initialization and cleanup patterns."""
        # Test initialization
        init_result = await archon_adapter.initialize()
        assert init_result["status"] == "initialized"

        # Test that adapter is ready for use
        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"

        # Test cleanup
        cleanup_result = await archon_adapter.cleanup()
        assert cleanup_result["status"] == "cleaned_up"

    @pytest.mark.asyncio
    async def test_error_handling_service_unavailable(self, archon_adapter):
        """Test error handling when services are unavailable."""
        # Simulate service unavailability
        await archon_adapter.simulate_service_down()

        # Attempt request - should handle gracefully
        with pytest.raises(Exception) as exc_info:
            await archon_adapter.make_request("test_request")

        assert "service unavailable" in str(exc_info.value).lower()

        # Restore service
        await archon_adapter.restore_service()

        # Verify service is back
        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"
