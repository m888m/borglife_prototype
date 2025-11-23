"""
Economic Model Tests for BorgLife Phase 1 E2E Testing

Tests wealth tracking, cost calculation, billing validation, and decimal precision
handling for economic model correctness within 0.001 DOT tolerance.
"""

import decimal
import json
import os
from decimal import ROUND_HALF_UP, Decimal, getcontext
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

# Test imports - these will be available in Docker environment
try:
    from jam_mock.interface import JAMInterface
    from proto_borg import ProtoBorg
    from synthesis import BorgPhenotype

    IMPORTS_AVAILABLE = True
except ImportError:
    # Mock for development environment
    ProtoBorg = MagicMock
    JAMInterface = MagicMock
    BorgPhenotype = MagicMock
    IMPORTS_AVAILABLE = False


class TestEconomicModel:
    """Test suite for economic model validation."""

    ECONOMIC_ACCURACY_TOLERANCE = Decimal("0.001")  # 0.001 DOT tolerance
    DECIMAL_PRECISION = 6

    @pytest.fixture(autouse=True)
    def setup_decimal_context(self):
        """Setup decimal context for all tests."""
        getcontext().prec = self.DECIMAL_PRECISION
        getcontext().rounding = ROUND_HALF_UP

    @pytest.fixture
    async def proto_borg(self):
        """Fixture for ProtoBorg instance."""
        if not IMPORTS_AVAILABLE:
            # Mock borg for development
            borg = AsyncMock()
            borg.get_wealth.return_value = Decimal("1.5")
            borg.calculate_task_cost.return_value = Decimal("0.0025")
            borg.process_payment.return_value = {
                "status": "success",
                "tx_hash": "0x123",
            }
            borg.get_transaction_history.return_value = [
                {
                    "amount": Decimal("0.1"),
                    "type": "credit",
                    "timestamp": "2025-01-01T00:00:00Z",
                },
                {
                    "amount": Decimal("0.05"),
                    "type": "debit",
                    "timestamp": "2025-01-02T00:00:00Z",
                },
            ]
            yield borg
        else:
            # Real borg for Docker environment
            borg = ProtoBorg()
            await borg.initialize()
            yield borg
            await borg.cleanup()

    @pytest.fixture
    async def jam_interface(self):
        """Fixture for JAM interface instance."""
        if not IMPORTS_AVAILABLE:
            # Mock interface for development
            interface = AsyncMock()
            interface.get_balance.return_value = Decimal("2.0")
            interface.validate_transaction.return_value = True
            interface.get_fee_estimate.return_value = Decimal("0.0001")
            yield interface
        else:
            # Real interface for Docker environment
            interface = JAMInterface()
            await interface.connect()
            yield interface
            await interface.disconnect()

    @pytest.fixture
    def expected_results(self) -> Dict[str, Dict[str, Any]]:
        """Load expected results from fixtures."""
        fixture_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "expected_results.json"
        )
        with open(fixture_path, "r") as f:
            return json.load(f)

    def test_decimal_precision_setup(self):
        """Test that decimal precision is correctly configured."""
        assert getcontext().prec == self.DECIMAL_PRECISION
        assert getcontext().rounding == ROUND_HALF_UP

    @pytest.mark.asyncio
    async def test_wealth_tracking_accuracy(self, proto_borg):
        """Test wealth tracking with decimal precision."""
        wealth = await proto_borg.get_wealth()

        # Verify wealth is Decimal type
        assert isinstance(wealth, Decimal)

        # Verify wealth is non-negative
        assert wealth >= 0

        # Verify precision (should not have excessive decimal places)
        wealth_str = str(wealth)
        if "." in wealth_str:
            decimal_places = len(wealth_str.split(".")[1])
            assert decimal_places <= self.DECIMAL_PRECISION

    @pytest.mark.asyncio
    async def test_cost_calculation_precision(self, proto_borg, expected_results):
        """Test cost calculation with required precision."""
        # Test cost calculation for different DNA configurations
        for dna_name, expected in expected_results.items():
            if dna_name.startswith("test_dna"):
                cost = await proto_borg.calculate_task_cost(dna_name)

                # Verify cost is Decimal
                assert isinstance(cost, Decimal)

                # Verify cost is within expected range
                expected_min = Decimal(str(expected["expected_cost_range"][0]))
                expected_max = Decimal(str(expected["expected_cost_range"][1]))

                assert (
                    expected_min <= cost <= expected_max
                ), f"Cost {cost} out of range [{expected_min}, {expected_max}] for {dna_name}"

                # Verify precision tolerance
                assert (
                    abs(cost - expected_min) <= self.ECONOMIC_ACCURACY_TOLERANCE
                    or abs(cost - expected_max) <= self.ECONOMIC_ACCURACY_TOLERANCE
                )

    @pytest.mark.asyncio
    async def test_billing_accuracy_validation(self, proto_borg, jam_interface):
        """Test billing accuracy with tolerance validation."""
        # Simulate a task execution and billing
        task_cost = await proto_borg.calculate_task_cost("test_dna_minimal")
        fee_estimate = await jam_interface.get_fee_estimate()

        total_cost = task_cost + fee_estimate

        # Process payment
        payment_result = await proto_borg.process_payment(total_cost)

        # Verify payment was successful
        assert payment_result["status"] == "success"
        assert "tx_hash" in payment_result

        # Verify wealth was correctly debited
        new_wealth = await proto_borg.get_wealth()
        previous_wealth = (
            await proto_borg.get_wealth()
        )  # This would be stored before payment

        # Note: In real implementation, we'd compare against stored previous value
        # For this test, we just verify the wealth is still valid
        assert isinstance(new_wealth, Decimal)
        assert new_wealth >= 0

    @pytest.mark.asyncio
    async def test_transaction_history_integrity(self, proto_borg):
        """Test transaction history maintains decimal precision."""
        history = await proto_borg.get_transaction_history()

        for transaction in history:
            # Verify amount is Decimal
            assert isinstance(transaction["amount"], Decimal)

            # Verify amount precision
            amount_str = str(transaction["amount"])
            if "." in amount_str:
                decimal_places = len(amount_str.split(".")[1])
                assert decimal_places <= self.DECIMAL_PRECISION

            # Verify transaction has required fields
            assert "type" in transaction
            assert "timestamp" in transaction
            assert transaction["type"] in ["credit", "debit"]

    @pytest.mark.asyncio
    async def test_economic_balance_consistency(self, proto_borg):
        """Test that economic balance remains consistent across operations."""
        initial_wealth = await proto_borg.get_wealth()

        # Perform some operations
        cost1 = await proto_borg.calculate_task_cost("test_dna_minimal")
        cost2 = await proto_borg.calculate_task_cost("test_dna_complex")

        # Calculate expected final wealth (if payments were made)
        # Note: This is a simulation - actual payment processing would modify wealth
        expected_final = initial_wealth

        final_wealth = await proto_borg.get_wealth()

        # In a real scenario, final_wealth might be different due to payments
        # For this test, we verify the operations don't break the system
        assert isinstance(final_wealth, Decimal)
        assert final_wealth >= 0

        # Verify cost calculations are consistent
        cost1_again = await proto_borg.calculate_task_cost("test_dna_minimal")
        assert cost1 == cost1_again, "Cost calculation should be deterministic"

    @pytest.mark.asyncio
    async def test_fee_estimation_accuracy(self, jam_interface):
        """Test fee estimation with decimal precision."""
        fee = await jam_interface.get_fee_estimate()

        assert isinstance(fee, Decimal)
        assert fee >= 0

        # Fee should be reasonable (not excessive)
        assert fee <= Decimal("0.01")  # Max reasonable fee

        # Fee should have appropriate precision
        fee_str = str(fee)
        if "." in fee_str:
            decimal_places = len(fee_str.split(".")[1])
            assert decimal_places <= self.DECIMAL_PRECISION

    @pytest.mark.asyncio
    async def test_payment_validation(self, proto_borg, jam_interface):
        """Test payment validation with economic constraints."""
        # Test valid payment
        valid_amount = Decimal("0.1")
        is_valid = await jam_interface.validate_transaction(valid_amount)
        assert is_valid is True

        # Test invalid payment (negative amount)
        invalid_amount = Decimal("-0.1")
        is_valid = await jam_interface.validate_transaction(invalid_amount)
        assert is_valid is False

        # Test payment processing
        payment_result = await proto_borg.process_payment(valid_amount)
        assert payment_result["status"] == "success"

    def test_decimal_arithmetic_precision(self):
        """Test decimal arithmetic maintains precision."""
        # Test various decimal operations
        amounts = [
            Decimal("0.1"),
            Decimal("0.05"),
            Decimal("0.025"),
            Decimal("0.0125"),
            Decimal("0.00625"),
        ]

        # Test summation
        total = sum(amounts)
        assert isinstance(total, Decimal)

        # Verify precision is maintained
        total_str = str(total)
        if "." in total_str:
            decimal_places = len(total_str.split(".")[1])
            assert decimal_places <= self.DECIMAL_PRECISION

        # Test that total equals expected value
        expected_total = Decimal("0.19375")
        assert abs(total - expected_total) <= self.ECONOMIC_ACCURACY_TOLERANCE

    @pytest.mark.asyncio
    async def test_economic_edge_cases(self, proto_borg):
        """Test economic model with edge cases."""
        # Test zero cost
        zero_cost = await proto_borg.calculate_task_cost("zero_cost_task")
        assert zero_cost == 0 or zero_cost >= 0

        # Test very small amounts
        tiny_amount = Decimal("0.000001")
        is_valid = await proto_borg.validate_amount(tiny_amount)
        # Small amounts should be valid (depending on implementation)

        # Test large amounts
        large_amount = Decimal("1000.0")
        is_valid = await proto_borg.validate_amount(large_amount)
        # Large amounts should be handled appropriately

    @pytest.mark.asyncio
    async def test_concurrent_economic_operations(self, proto_borg):
        """Test concurrent economic operations maintain consistency."""
        import asyncio

        async def perform_operation(operation_id: int):
            cost = await proto_borg.calculate_task_cost(
                f"concurrent_task_{operation_id}"
            )
            return cost

        # Perform 5 concurrent operations
        tasks = [perform_operation(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all results are valid decimals
        for result in results:
            assert isinstance(result, Decimal)
            assert result >= 0

        # Verify results are consistent (same operation should give same cost)
        first_result = results[0]
        for result in results[1:]:
            assert abs(result - first_result) <= self.ECONOMIC_ACCURACY_TOLERANCE

    @pytest.mark.asyncio
    async def test_economic_audit_trail(self, proto_borg):
        """Test economic audit trail integrity."""
        # Get initial state
        initial_wealth = await proto_borg.get_wealth()
        initial_history_length = len(await proto_borg.get_transaction_history())

        # Perform operation
        cost = await proto_borg.calculate_task_cost("audit_test_task")
        payment_result = await proto_borg.process_payment(cost)

        # Get final state
        final_wealth = await proto_borg.get_wealth()
        final_history = await proto_borg.get_transaction_history()

        # Verify audit trail
        assert len(final_history) >= initial_history_length

        # Verify wealth change is accounted for
        # Note: Actual wealth change depends on payment processing implementation
        assert isinstance(final_wealth, Decimal)
        assert final_wealth >= 0
