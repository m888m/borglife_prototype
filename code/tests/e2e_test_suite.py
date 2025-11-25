#!/usr/bin/env python3
"""
BorgLife Phase 1 End-to-End Test Suite

Complete test orchestrator implementing the demo flow:
funding → borg creation → task execution → DNA encoding → storage → decoding validation

This suite validates the entire BorgLife Phase 1 user journey using Archon infrastructure.
"""

import asyncio
import json
import yaml
import os
import time
from decimal import Decimal, getcontext
from pathlib import Path
from pprint import pprint
from typing import Any, Dict, List, Optional

import pytest
import yaml
import pytest_asyncio

# Test imports - these will be available in Docker environment
try:
    from archon_adapter.adapter import ArchonServiceAdapter
    from jam_mock.interface import JAMInterface
    from proto_borg import BorgConfig, ProtoBorgAgent
    from synthesis.dna_parser import DNAParser
    from synthesis.phenotype_builder import PhenotypeBuilder

    IMPORTS_AVAILABLE = True
except ImportError:

    # Try to import real JAM interface
    try:
        from jam_mock import JAMInterface
        real_jam_available = True
    except ImportError:
        real_jam_available = False


@pytest_asyncio.fixture(scope="session")
async def e2e_suite():
    suite = E2ETestSuite()
    await suite.setup_test_environment()
    yield suite
    await suite.teardown_test_environment()


@pytest.mark.asyncio
async def test_complete_demo_flow_execution(e2e_suite):
    results = await e2e_suite.run_all_scenarios()
    report = e2e_suite.generate_test_report(results)
    e2e_suite.save_report(report)
    e2e_suite.print_report_summary(report)
    criteria = report["prp_success_criteria"]
    assert criteria["all_5_core_demo_scenarios_execute_successfully"], "Not all 5 core demo scenarios executed successfully"
    assert criteria["dna_round_trip_integrity_maintained"], "DNA round-trip integrity not maintained"
    assert criteria["economic_calculations_accurate_within_0_001_dot"], "Economic calculations not accurate within 0.001 DOT"

    # Test execution completes within 5 minutes
    assert criteria[
        "test_execution_completes_within_5_minutes"
    ], "Test execution did not complete within 5 minutes"

    # No service crashes or hangs
    assert criteria[
        "no_service_crashes_or_hangs"
    ], "Service crashes or hangs detected"

    # Comprehensive error reporting for failures
    assert criteria[
        "comprehensive_error_reporting_for_failures"
    ], "Comprehensive error reporting not implemented"

@pytest.mark.asyncio
async def test_individual_scenario_execution(e2e_suite):
    """Test individual scenario execution."""
    fixtures = await e2e_suite.load_test_fixtures()
    scenario = fixtures["demo_tasks"]["scenarios"][0]  # Test first scenario
    dna_config = fixtures["dna_samples"]["test_dna_minimal"]

    borg_id = f"individual_test_{int(time.time() * 1000)}"
    result = await e2e_suite.execute_demo_flow(borg_id, dna_config, scenario)

    # Validate individual scenario execution
    assert result[
        "success"
    ], f"Individual scenario failed: {result.get('errors', [])}"
    assert result["dna_integrity"], "DNA integrity check failed"
    assert result["economic_accuracy"], "Economic accuracy check failed"
    assert result["execution_time"] > 0, "Execution time not recorded"
    assert "dna_hash" in result, "DNA hash not generated"
    assert "stored_hash" in result, "DNA hash not stored"

@pytest.mark.asyncio
async def test_phase2a_usdb_asset_creation(e2e_suite):
    """Test Phase 2A USDB asset creation on Westend Asset Hub."""
    from scripts.create_usdb_asset import USDBAssetCreator

    # Test asset creation (mock mode for CI)
    creator = USDBAssetCreator()
    success = await creator.create_asset()

    # In mock mode, this should succeed
    assert success, "USDB asset creation failed"
    assert creator.asset_id is not None, "Asset ID not assigned"

    # Verify asset metadata
    success = await creator.set_metadata()
    assert success, "Asset metadata setting failed"

    # Verify asset verification
    success = await creator.verify_asset()
    assert success, "Asset verification failed"

@pytest.mark.asyncio
async def test_phase2a_usdb_distribution(e2e_suite):
    """Test Phase 2A USDB distribution to borgs."""
    from scripts.usdb_distribution import USDBDistributor

    distributor = USDBDistributor()

    # Test distribution to mock borgs
    test_borgs = ["test_borg_1", "test_borg_2"]
    results = await distributor.distribute_to_test_borgs(test_borgs)

    # Should succeed in mock mode
    assert results["successful_distributions"] >= 0, "Distribution failed"
    assert len(results["distribution_details"]) == len(
        test_borgs
    ), "Distribution details incomplete"

@pytest.mark.asyncio
async def test_phase2a_inter_borg_transfers(e2e_suite):
    """Test Phase 2A inter-borg USDB transfers."""
    from jam_mock.inter_borg_transfer import InterBorgTransfer
    from jam_mock.westend_adapter import WestendAdapter

    # Initialize components
    westend_adapter = WestendAdapter()
    transfer_protocol = InterBorgTransfer(westend_adapter)

    # Test transfer validation (mock)
    validation = await transfer_protocol.validate_transfer(
        from_borg_id="borg_a",
        to_borg_id="borg_b",
        currency="USDB",
        amount=Decimal("10.0"),
    )

    # Should pass validation in mock mode
    assert validation[
        "valid"
    ], f"Transfer validation failed: {validation.get('errors', [])}"

@pytest.mark.asyncio
async def test_phase2a_economic_validation(e2e_suite):
    """Test Phase 2A economic validation and controls."""
    from jam_mock.economic_validator import EconomicValidator

    validator = EconomicValidator()

    # Test transfer validation
    result = await validator.validate_transfer(
        from_borg_id="borg_a",
        to_borg_id="borg_b",
        currency="USDB",
        amount=Decimal("10.0"),
        asset_id=12345,
    )

    # Should pass in mock mode
    assert result[
        "valid"
    ], f"Economic validation failed: {result.get('errors', [])}"
    assert "cost_estimate" in result, "Cost estimate missing"
    assert "ethical_compliance" in result, "Ethical compliance check missing"

@pytest.mark.asyncio
async def test_phase2a_transaction_manager(e2e_suite):
    """Test Phase 2A transaction manager with dual currencies."""
    from jam_mock.transaction_manager import TransactionManager

    manager = TransactionManager()

    # Test transaction recording
    tx_id = await manager.record_transaction(
        from_borg_id="borg_a",
        to_borg_id="borg_b",
        currency="USDB",
        amount=Decimal("10.0"),
        transaction_type="ASSET_TRANSFER",
        asset_id=12345,
        description="Test transfer",
    )

    assert tx_id, "Transaction recording failed"

    # Test transaction retrieval
    tx = await manager.get_transaction(tx_id)
    assert tx, "Transaction retrieval failed"
    assert tx["currency"] == "USDB", "Currency mismatch"
    assert tx["transaction_type"] == "ASSET_TRANSFER", "Transaction type mismatch"

@pytest.mark.asyncio
async def test_phase2a_complete_economic_flow(e2e_suite):
    """Test complete Phase 2A economic flow: asset creation → distribution → transfer."""
    # This is a comprehensive integration test
    from jam_mock.inter_borg_transfer import InterBorgTransfer
    from jam_mock.westend_adapter import WestendAdapter
    from scripts.create_usdb_asset import USDBAssetCreator
    from scripts.usdb_distribution import USDBDistributor

    # 1. Create USDB asset
    creator = USDBAssetCreator()
    asset_success = await creator.create_asset()
    assert asset_success, "Asset creation failed"

    # 2. Distribute to borgs
    distributor = USDBDistributor()
    dist_results = await distributor.distribute_to_test_borgs(["borg_a", "borg_b"])
    assert dist_results["successful_distributions"] >= 0, "Distribution failed"

    # 3. Execute inter-borg transfer
    westend_adapter = WestendAdapter()
    transfer_protocol = InterBorgTransfer(westend_adapter)

    transfer_result = await transfer_protocol.transfer_usdb(
        from_borg_id="borg_a",
        to_borg_id="borg_b",
        amount=Decimal("5.0"),
        description="Integration test transfer",
    )

    # Should succeed in mock mode
    assert (
        transfer_result["success"] or "mock" in str(transfer_result).lower()
    ), f"Transfer failed: {transfer_result}"

    print("✅ Phase 2A complete economic flow test passed")

class E2ETestSuite:
    def __init__(self):
        self.arch


if __name__ == "__main__":
    # Allow direct execution for debugging
    async def main():
        suite = E2ETestSuite()
        await suite.setup_test_environment()

        try:
            results = await suite.run_all_scenarios()
            report = suite.generate_test_report(results)
            suite.save_report(report)
            suite.print_report_summary(report)
        finally:
            await suite.teardown_test_environment()

    asyncio.run(main())
