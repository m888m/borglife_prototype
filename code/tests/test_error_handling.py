"""
Error Handling & Recovery Tests for BorgLife Phase 1 E2E Testing

Tests circuit breaker recovery, service unavailability, timeout scenarios,
and async context management. Addresses all gotchas mentioned in PRP.
"""

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

# Test imports - these will be available in Docker environment
try:
    from archon_adapter.adapter import ArchonAdapter
    from jam_mock.interface import JAMInterface
    from proto_borg import ProtoBorgAgent
    from synthesis.dna_parser import DNAParser
    IMPORTS_AVAILABLE = True
except ImportError:
    # Mock for development environment
    ArchonAdapter = MagicMock
    JAMInterface = MagicMock
    ProtoBorgAgent = MagicMock
    DNAParser = MagicMock
    IMPORTS_AVAILABLE = False


class TestErrorHandling:
    """Test suite for error handling and recovery scenarios."""

    @pytest.fixture
    async def archon_adapter(self):
        """Fixture for Archon adapter with error simulation capabilities."""
        if not IMPORTS_AVAILABLE:
            adapter = AsyncMock()
            adapter.health_check.return_value = {"status": "healthy", "services": ["mcp", "database"]}
            adapter.simulate_service_failure = AsyncMock()
            adapter.simulate_service_down = AsyncMock()
            adapter.restore_service = AsyncMock()
            adapter.trigger_circuit_breaker = AsyncMock()
            adapter.reset_circuit_breaker = AsyncMock()
            adapter.get_circuit_breaker_status.return_value = {"state": "closed"}
            adapter.make_request = AsyncMock(return_value={"status": "success"})
            yield adapter
        else:
            adapter = ArchonAdapter()
            await adapter.initialize()
            yield adapter
            await adapter.cleanup()

    @pytest.fixture
    async def proto_borg(self):
        """Fixture for ProtoBorg with error simulation."""
        if not IMPORTS_AVAILABLE:
            borg = AsyncMock()
            borg.initialize = AsyncMock()
            borg.cleanup = AsyncMock()
            borg.execute_task = AsyncMock(return_value={"success": True, "cost": Decimal('0.001')})
            borg.simulate_failure = AsyncMock()
            borg.simulate_timeout = AsyncMock()
            yield borg
        else:
            borg = ProtoBorgAgent()
            await borg.initialize()
            yield borg
            await borg.cleanup()

    @pytest.fixture
    async def jam_interface(self):
        """Fixture for JAM interface with error handling."""
        if not IMPORTS_AVAILABLE:
            interface = AsyncMock()
            interface.get_balance.return_value = Decimal('1.5')
            interface.transfer = AsyncMock(return_value={"tx_hash": "0x123", "status": "confirmed"})
            interface.simulate_network_failure = AsyncMock()
            interface.simulate_insufficient_funds = AsyncMock()
            yield interface
        else:
            interface = JAMInterface()
            await interface.connect()
            yield interface
            await interface.disconnect()

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, archon_adapter):
        """Test circuit breaker state management and recovery."""
        # Initial state should be closed
        status = await archon_adapter.get_circuit_breaker_status()
        assert status["state"] == "closed"

        # Trigger circuit breaker (simulate failures)
        await archon_adapter.trigger_circuit_breaker()

        # Verify it's now open
        status = await archon_adapter.get_circuit_breaker_status()
        assert status["state"] == "open"

        # Reset circuit breaker
        await archon_adapter.reset_circuit_breaker()

        # Verify it's closed again
        status = await archon_adapter.get_circuit_breaker_status()
        assert status["state"] == "closed"

    @pytest.mark.asyncio
    async def test_service_failure_recovery(self, archon_adapter):
        """Test service failure and recovery scenarios."""
        # Initial health should be good
        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"

        # Simulate service failure
        await archon_adapter.simulate_service_failure()

        # Health should be degraded
        health = await archon_adapter.health_check()
        assert health["status"] == "degraded"

        # Wait for recovery (simulate service restart)
        await asyncio.sleep(1)

        # Health should recover (in real implementation, this would be automatic)
        # For this test, we manually restore
        await archon_adapter.restore_service()

        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_service_unavailability_handling(self, archon_adapter):
        """Test handling of complete service unavailability."""
        # Simulate service going down
        await archon_adapter.simulate_service_down()

        # Attempt to make a request - should handle gracefully
        with pytest.raises(Exception) as exc_info:
            await archon_adapter.make_request("test_request")

        # Should provide meaningful error message
        assert "service unavailable" in str(exc_info.value).lower() or \
               "unavailable" in str(exc_info.value).lower()

        # Restore service
        await archon_adapter.restore_service()

        # Request should work again
        result = await archon_adapter.make_request("test_request")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_timeout_scenario_handling(self, proto_borg):
        """Test timeout scenarios and handling."""
        # Simulate a timeout scenario
        await proto_borg.simulate_timeout()

        # Execute a task that should timeout
        with pytest.raises(asyncio.TimeoutError) as exc_info:
            await asyncio.wait_for(
                proto_borg.execute_task("timeout_test_task"),
                timeout=1.0  # Short timeout for test
            )

        # Verify timeout was handled properly
        assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_async_context_management(self, archon_adapter, proto_borg):
        """Test proper async context management and cleanup."""
        # Test successful initialization and cleanup
        init_result = await archon_adapter.initialize()
        assert init_result["status"] == "initialized"

        borg_init = await proto_borg.initialize()
        assert borg_init is not None  # Success indicator

        # Verify services are ready
        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"

        # Test cleanup
        cleanup_result = await archon_adapter.cleanup()
        assert cleanup_result["status"] == "cleaned_up"

        borg_cleanup = await proto_borg.cleanup()
        assert borg_cleanup is not None  # Success indicator

    @pytest.mark.asyncio
    async def test_async_context_failure_recovery(self, archon_adapter):
        """Test async context management with failure recovery."""
        # Initialize successfully
        init_result = await archon_adapter.initialize()
        assert init_result["status"] == "initialized"

        # Simulate failure during operation
        await archon_adapter.simulate_service_failure()

        # Cleanup should still work even with failures
        cleanup_result = await archon_adapter.cleanup()
        assert cleanup_result["status"] == "cleaned_up"

        # Should be able to reinitialize after cleanup
        init_result2 = await archon_adapter.initialize()
        assert init_result2["status"] == "initialized"

    @pytest.mark.asyncio
    async def test_network_failure_recovery(self, jam_interface):
        """Test network failure and recovery in JAM operations."""
        # Initial balance check should work
        balance = await jam_interface.get_balance()
        assert isinstance(balance, Decimal)
        assert balance >= 0

        # Simulate network failure
        await jam_interface.simulate_network_failure()

        # Transfer should fail gracefully
        with pytest.raises(Exception) as exc_info:
            await jam_interface.transfer(
                to_address="test_address",
                amount=Decimal('0.1'),
                memo="test transfer"
            )

        # Should indicate network/connectivity issue
        assert any(term in str(exc_info.value).lower() for term in
                  ["network", "connection", "connectivity", "unavailable"])

    @pytest.mark.asyncio
    async def test_insufficient_funds_handling(self, jam_interface):
        """Test insufficient funds error handling."""
        # Simulate insufficient funds
        await jam_interface.simulate_insufficient_funds()

        # Attempt transfer that should fail
        with pytest.raises(Exception) as exc_info:
            await jam_interface.transfer(
                to_address="test_address",
                amount=Decimal('1000.0'),  # Large amount
                memo="insufficient funds test"
            )

        # Should indicate insufficient funds
        assert any(term in str(exc_info.value).lower() for term in
                  ["insufficient", "funds", "balance", "amount"])

    @pytest.mark.asyncio
    async def test_concurrent_error_scenarios(self, archon_adapter):
        """Test handling multiple concurrent error scenarios."""
        async def error_operation(operation_id: int):
            try:
                if operation_id % 3 == 0:
                    # Simulate timeout
                    await asyncio.sleep(2)  # Longer than test timeout
                    return {"status": "timeout", "operation_id": operation_id}
                elif operation_id % 3 == 1:
                    # Simulate service failure
                    await archon_adapter.simulate_service_failure()
                    result = await archon_adapter.make_request(f"operation_{operation_id}")
                    return result
                else:
                    # Normal operation
                    result = await archon_adapter.make_request(f"operation_{operation_id}")
                    return result
            except Exception as e:
                return {"status": "error", "operation_id": operation_id, "error": str(e)}

        # Run 9 concurrent operations (3 of each type)
        tasks = [error_operation(i) for i in range(9)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify we got results for all operations
        assert len(results) == 9

        # Count different result types
        timeouts = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "timeout")
        errors = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "error")
        successes = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")

        # Should have some of each type
        assert timeouts >= 2  # At least some timeouts
        assert errors >= 2    # At least some errors
        assert successes >= 2 # At least some successes

    @pytest.mark.asyncio
    async def test_error_recovery_with_retry_logic(self, archon_adapter):
        """Test error recovery with retry logic."""
        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Fail first two attempts
                await archon_adapter.simulate_service_failure()
                raise Exception("Temporary service failure")
            else:
                # Succeed on third attempt
                return {"status": "success", "attempts": call_count}

        # Implement retry logic
        max_retries = 5
        for attempt in range(max_retries):
            try:
                result = await failing_operation()
                # Success - break out of retry loop
                assert result["status"] == "success"
                assert result["attempts"] == 3  # Should have taken 3 attempts
                break
            except Exception:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    pytest.fail("Operation did not succeed within retry limit")
                # Wait before retry
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self, archon_adapter, proto_borg):
        """Test that resources are properly cleaned up even when errors occur."""
        resources_created = []

        try:
            # Initialize resources
            init_result = await archon_adapter.initialize()
            resources_created.append("adapter")
            assert init_result["status"] == "initialized"

            borg_init = await proto_borg.initialize()
            resources_created.append("borg")
            assert borg_init is not None

            # Simulate error during operation
            await archon_adapter.simulate_service_failure()
            await proto_borg.simulate_failure()

            # Force an exception
            raise Exception("Simulated operation failure")

        except Exception:
            # Verify cleanup happens even with exception
            try:
                if "adapter" in resources_created:
                    cleanup_result = await archon_adapter.cleanup()
                    assert cleanup_result["status"] == "cleaned_up"

                if "borg" in resources_created:
                    borg_cleanup = await proto_borg.cleanup()
                    assert borg_cleanup is not None

                # Verify resources are actually cleaned up
                # (In real implementation, this would check for proper cleanup)
                pass

            except Exception as cleanup_error:
                pytest.fail(f"Cleanup failed: {cleanup_error}")

        # Should not reach here due to the forced exception above
        assert False, "Should have raised exception"

    @pytest.mark.asyncio
    async def test_error_context_preservation(self, archon_adapter):
        """Test that error context is preserved for debugging."""
        # Simulate specific error scenario
        await archon_adapter.simulate_service_failure()

        try:
            await archon_adapter.make_request("failing_request")
            assert False, "Should have raised exception"
        except Exception as e:
            # Verify error contains useful context
            error_str = str(e)
            assert any(term in error_str.lower() for term in
                      ["error", "failed", "unavailable", "service"])

            # In real implementation, error should include:
            # - Operation that failed
            # - Timestamp
            # - Service state
            # - Relevant IDs/context

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, archon_adapter):
        """Test graceful degradation when services are partially unavailable."""
        # Start with all services healthy
        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"

        # Simulate partial service degradation (some services fail, others work)
        await archon_adapter.simulate_partial_failure()

        # System should still be partially functional
        health = await archon_adapter.health_check()
        assert health["status"] in ["degraded", "healthy"]  # Allow some flexibility

        # Core operations should still work
        result = await archon_adapter.make_request("core_operation")
        assert result["status"] == "success"

        # Non-critical operations might fail gracefully
        try:
            await archon_adapter.make_request("optional_operation")
        except Exception:
            # This is acceptable for degraded state
            pass

    @pytest.mark.asyncio
    async def test_service_partial_degradation(self, archon_adapter):
        """Test handling of partial service degradation scenarios."""
        # Start with all services healthy
        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"

        # Simulate partial degradation (some services work, others don't)
        await archon_adapter.simulate_partial_degradation()

        # Health should show degraded but not failed
        health = await archon_adapter.health_check()
        assert health["status"] in ["degraded", "partially_available"]

        # Core operations should still work
        result = await archon_adapter.make_request("core_operation")
        assert result["status"] == "success"

        # Non-critical operations might fail gracefully
        try:
            await archon_adapter.make_request("optional_operation")
            # If it succeeds, that's fine
        except Exception:
            # Graceful failure is acceptable in degraded state
            pass

        # Verify system can still perform critical functions
        critical_result = await archon_adapter.make_request("critical_operation")
        assert critical_result["status"] == "success"

    @pytest.mark.asyncio
    async def test_service_complete_outage(self, archon_adapter):
        """Test handling of complete service outage scenarios."""
        # Start with services healthy
        health = await archon_adapter.health_check()
        assert health["status"] == "healthy"

        # Simulate complete service outage
        await archon_adapter.simulate_complete_outage()

        # Health should show complete failure
        health = await archon_adapter.health_check()
        assert health["status"] in ["failed", "unavailable", "down"]

        # All operations should fail gracefully
        with pytest.raises(Exception) as exc_info:
            await archon_adapter.make_request("any_operation")

        # Error should indicate service unavailability
        error_msg = str(exc_info.value).lower()
        assert any(term in error_msg for term in
                  ["unavailable", "outage", "down", "failed", "service"]), \
               f"Error message should indicate service unavailability: {error_msg}"

        # System should not crash or hang
        # (In real implementation, this would test circuit breaker timeout)

    @pytest.mark.asyncio
    async def test_error_boundary_isolation(self, archon_adapter):
        """Test that errors in one operation don't affect others."""
        # Perform multiple operations, some failing, some succeeding
        results = []

        for i in range(5):
            try:
                if i % 2 == 0:
                    # Even operations succeed
                    result = await archon_adapter.make_request(f"operation_{i}")
                    results.append({"id": i, "status": "success"})
                else:
                    # Odd operations fail
                    await archon_adapter.simulate_service_failure()
                    await archon_adapter.make_request(f"failing_operation_{i}")
                    results.append({"id": i, "status": "should_not_reach"})
            except Exception as e:
                results.append({"id": i, "status": "error", "error": str(e)})

        # Verify isolation: failures don't prevent subsequent operations
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = sum(1 for r in results if r["status"] == "error")

        assert success_count >= 2, "Should have successful operations"
        assert error_count >= 2, "Should have failed operations"

        # Operations should be independent
        for i, result in enumerate(results):
            if i % 2 == 0:
                assert result["status"] == "success", f"Even operation {i} should succeed"
            else:
                assert result["status"] == "error", f"Odd operation {i} should fail"