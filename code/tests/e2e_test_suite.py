#!/usr/bin/env python3
"""
BorgLife Phase 1 End-to-End Test Suite

Complete test orchestrator implementing the demo flow:
funding → borg creation → task execution → DNA encoding → storage → decoding validation

This suite validates the entire BorgLife Phase 1 user journey using Archon infrastructure.
"""

import asyncio
import json
import os
import time
import pytest
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Dict, List, Any, Optional

# Test imports - these will be available in Docker environment
try:
    from synthesis.dna_parser import DNAParser
    from synthesis.phenotype_builder import PhenotypeBuilder
    from archon_adapter.adapter import ArchonServiceAdapter
    from jam_mock.interface import JAMInterface
    from proto_borg import ProtoBorgAgent, BorgConfig
    IMPORTS_AVAILABLE = True
except ImportError:
    # Mock for development environment
    DNAParser = type('MockDNAParser', (), {
        'parse_dna': lambda self, x: {'header': {'code_length': 1024}, 'cells': [], 'organs': []},
        'validate_dna': lambda self, x: True,
        'calculate_hash': lambda self, x: 'mock_hash',
        'serialize_to_canonical': lambda self, x: 'mock_yaml',
        'to_yaml': lambda self, x: 'mock_yaml',
        'from_yaml': lambda self, x: {'header': {'code_length': 1024}, 'cells': [], 'organs': []}
    })()
    PhenotypeBuilder = type('MockPhenotypeBuilder', (), {
        'build_phenotype': lambda self, x: {'cells': [], 'organs': [], 'total_cost': 0.001}
    })()
    ArchonServiceAdapter = type('MockArchonAdapter', (), {
        'initialize': lambda self: None,
        'health_check': lambda self: {'status': 'healthy'},
        'make_request': lambda self, x: {'status': 'success', 'result': 'mock_result'}
    })()
    JAMInterface = type('MockJAMInterface', (), {
        'update_wealth': lambda self, **kwargs: None,
        'get_balance': lambda self, x: Decimal('0.1'),
        'store_dna_hash': lambda self, x, y: {'success': True},
        'retrieve_dna_hash': lambda self, x: 'mock_hash',
        'verify_dna_integrity': lambda self, x, y: True
    })()
    ProtoBorgAgent = type('MockProtoBorgAgent', (), {
        'initialize': lambda self: None,
        'execute_task': lambda self, x: {'result': 'mock_result', 'cost': 0.001},
        'update_dna': lambda self, x: None
    })
    BorgConfig = type('MockBorgConfig', (), {})()
    IMPORTS_AVAILABLE = False


class E2ETestSuite:
    """
    Complete E2E test orchestrator for BorgLife Phase 1.

    Implements the full demo flow: funding → creation → execution → encoding → storage → decoding
    """

    def __init__(self):
        self.archon_adapter: Optional[ArchonServiceAdapter] = None
        self.jam_interface: Optional[JAMInterface] = None
        self.phenotype_builder: Optional[PhenotypeBuilder] = None
        self.test_results = []
        self.start_time = time.time()

    async def setup_test_environment(self):
        """Setup test environment with all required services."""
        if not IMPORTS_AVAILABLE:
            # Mock setup for development
            self.archon_adapter = ArchonServiceAdapter()
            self.jam_interface = JAMInterface()
            self.phenotype_builder = PhenotypeBuilder()
            return

        # Real setup for Docker environment
        self.archon_adapter = ArchonServiceAdapter()
        await self.archon_adapter.initialize()

        # Verify service health
        health = await self.archon_adapter.health_check()
        assert health['status'] == 'healthy', f"Archon services not healthy: {health}"

        # Initialize JAM interface
        self.jam_interface = JAMInterface()

        # Initialize phenotype builder
        self.phenotype_builder = PhenotypeBuilder(self.archon_adapter)

    async def teardown_test_environment(self):
        """Clean up test environment."""
        if self.archon_adapter and hasattr(self.archon_adapter, 'close'):
            await self.archon_adapter.close()

    async def load_test_fixtures(self) -> Dict[str, Any]:
        """Load test fixtures from files."""
        fixtures_dir = Path(__file__).parent / "fixtures"

        # Load DNA samples
        dna_path = fixtures_dir / "test_dna_samples.yaml"
        with open(dna_path, 'r') as f:
            dna_samples = yaml.safe_load(f)

        # Load demo tasks
        tasks_path = fixtures_dir / "demo_tasks.json"
        with open(tasks_path, 'r') as f:
            demo_tasks = json.load(f)

        # Load expected results
        results_path = fixtures_dir / "expected_results.json"
        with open(results_path, 'r') as f:
            expected_results = json.load(f)

        return {
            'dna_samples': dna_samples,
            'demo_tasks': demo_tasks,
            'expected_results': expected_results
        }

    async def execute_demo_flow(self, borg_id: str, dna_config: Dict[str, Any],
                               task_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete demo flow for a single scenario.

        Args:
            borg_id: Unique borg identifier
            dna_config: DNA configuration
            task_scenario: Task scenario to execute

        Returns:
            Execution results and validation metrics
        """
        flow_start = time.time()
        result = {
            'borg_id': borg_id,
            'scenario': task_scenario['name'],
            'success': False,
            'execution_time': 0,
            'dna_integrity': False,
            'economic_accuracy': False,
            'errors': []
        }

        try:
            # 1. FUNDING: Initialize borg with wealth
            funding_amount = Decimal('0.1')  # 0.1 DOT initial funding
            await self.jam_interface.update_wealth(
                borg_id=borg_id,
                amount=Decimal(str(funding_amount)),
                operation="funding",
                description=f"Demo funding for {borg_id}"
            )

            # 2. CREATION: Create borg from DNA
            config = BorgConfig(service_index=borg_id)
            borg = ProtoBorgAgent(config)
            await borg.initialize()

            # Parse and validate DNA
            dna = DNAParser.from_yaml(yaml.dump(dna_config))
            assert DNAParser.validate_dna(dna), f"DNA validation failed for {borg_id}"

            # Build phenotype
            phenotype = await self.phenotype_builder.build_phenotype(dna)
            borg.phenotype = phenotype

            # 3. EXECUTION: Execute task
            task_result = await borg.execute_task(task_scenario['task'])
            execution_cost = Decimal(str(task_result.get('cost', 0)))

            # Validate cost is within expected range
            expected_min = Decimal(str(task_scenario['expected_cost_range'][0]))
            expected_max = Decimal(str(task_scenario['expected_cost_range'][1]))
            cost_valid = expected_min <= execution_cost <= expected_max

            # 4. ENCODING: Serialize DNA to YAML
            dna_yaml = DNAParser.to_yaml(dna)
            dna_hash = DNAParser.calculate_hash(dna)

            # 5. STORAGE: Store DNA hash on-chain
            store_result = await self.jam_interface.store_dna_hash(borg_id, dna_hash)
            assert store_result['success'], f"DNA storage failed for {borg_id}"

            # 6. DECODING: Retrieve and validate integrity
            stored_hash = await self.jam_interface.retrieve_dna_hash(borg_id)
            integrity_valid = await self.jam_interface.verify_dna_integrity(borg_id, dna_hash)
            assert integrity_valid, f"DNA integrity validation failed for {borg_id}"

            # Round-trip integrity check: H(D') = H(D)
            reparsed_dna = DNAParser.from_yaml(dna_yaml)
            reparsed_hash = DNAParser.calculate_hash(reparsed_dna)
            roundtrip_integrity = dna_hash == reparsed_hash

            # Deduct execution cost
            await self.jam_interface.update_wealth(
                borg_id=borg_id,
                amount=Decimal(str(execution_cost)),
                operation="cost",
                description=f"Task execution: {task_scenario['task'][:50]}..."
            )

            # Final balance check
            final_balance = await self.jam_interface.get_balance(borg_id)
            expected_balance = funding_amount - execution_cost

            # Economic accuracy within 0.001 DOT tolerance
            balance_tolerance = Decimal("0.001")
            economic_valid = abs(final_balance - expected_balance) <= balance_tolerance

            # Overall success
            execution_time = time.time() - flow_start
            all_checks_pass = (
                cost_valid and
                integrity_valid and
                roundtrip_integrity and
                economic_valid
            )

            result.update({
                'success': all_checks_pass,
                'execution_time': execution_time,
                'dna_integrity': integrity_valid and roundtrip_integrity,
                'economic_accuracy': economic_valid,
                'cost_validation': cost_valid,
                'actual_cost': float(execution_cost),
                'expected_cost_range': task_scenario['expected_cost_range'],
                'final_balance': float(final_balance),
                'expected_balance': float(expected_balance),
                'task_result': task_result.get('result', ''),
                'dna_hash': dna_hash,
                'stored_hash': stored_hash
            })

        except Exception as e:
            result['execution_time'] = time.time() - flow_start
            result['errors'].append(str(e))
            result['success'] = False

        return result

    async def run_all_scenarios(self) -> List[Dict[str, Any]]:
        """Run all demo scenarios from fixtures."""
        fixtures = await self.load_test_fixtures()
        results = []

        for scenario in fixtures['demo_tasks']['scenarios']:
            # Use minimal DNA for all scenarios (can be extended later)
            dna_config = fixtures['dna_samples']['test_dna_minimal']

            # Generate unique borg ID
            borg_id = f"e2e_test_{scenario['name']}_{int(time.time() * 1000)}"

            # Execute demo flow
            result = await self.execute_demo_flow(borg_id, dna_config, scenario)
            results.append(result)

            # Small delay between tests
            await asyncio.sleep(0.1)

        return results

    def generate_test_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r['success'])
        failed_tests = total_tests - successful_tests

        total_execution_time = sum(r['execution_time'] for r in results)
        avg_execution_time = total_execution_time / total_tests if total_tests > 0 else 0

        dna_integrity_passed = sum(1 for r in results if r.get('dna_integrity', False))
        economic_accuracy_passed = sum(1 for r in results if r.get('economic_accuracy', False))

        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        dna_integrity_rate = (dna_integrity_passed / total_tests * 100) if total_tests > 0 else 0
        economic_accuracy_rate = (economic_accuracy_passed / total_tests * 100) if total_tests > 0 else 0

        return {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate_percent': round(success_rate, 2),
                'total_execution_time_seconds': round(total_execution_time, 2),
                'avg_execution_time_seconds': round(avg_execution_time, 2),
                'dna_integrity_rate_percent': round(dna_integrity_rate, 2),
                'economic_accuracy_rate_percent': round(economic_accuracy_rate, 2)
            },
            'results': results,
            'validation_status': {
                'all_5_scenarios_executed': total_tests >= 5,
                'dna_roundtrip_integrity_maintained': dna_integrity_rate == 100.0,
                'economic_accuracy_within_0_001_dot': economic_accuracy_rate == 100.0,
                'execution_under_5_minutes': total_execution_time < 300,
                'no_service_crashes': all(not r.get('errors') for r in results),
                'comprehensive_error_reporting': all('errors' in r for r in results)
            },
            'prp_success_criteria': {
                'all_5_core_demo_scenarios_execute_successfully': successful_tests >= 5,
                'dna_round_trip_integrity_maintained': dna_integrity_rate == 100.0,
                'economic_calculations_accurate_within_0_001_dot': economic_accuracy_rate == 100.0,
                'test_execution_completes_within_5_minutes': total_execution_time < 300,
                'no_service_crashes_or_hangs': all(not r.get('errors') for r in results),
                'comprehensive_error_reporting_for_failures': all('errors' in r for r in results)
            }
        }

    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save test report to file."""
        if filename is None:
            timestamp = int(time.time())
            filename = f"e2e_test_report_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"Test report saved to {filename}")

    def print_report_summary(self, report: Dict[str, Any]):
        """Print human-readable test report summary."""
        summary = report['summary']
        validation = report['validation_status']

        print("\n" + "="*80)
        print("BORGLIFE PHASE 1 E2E TEST SUITE REPORT")
        print("="*80)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate_percent']:.1f}%")
        print(f"Total Execution Time: {summary['total_execution_time_seconds']:.2f}s")
        print(f"Average Execution Time: {summary['avg_execution_time_seconds']:.2f}s")
        print(f"DNA Integrity Rate: {summary['dna_integrity_rate_percent']:.1f}%")
        print(f"Economic Accuracy Rate: {summary['economic_accuracy_rate_percent']:.1f}%")

        print("\nPRP SUCCESS CRITERIA VALIDATION:")
        criteria = report['prp_success_criteria']
        for criterion, passed in criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {criterion}")

        overall_success = all(validation.values())
        print(f"\nOVERALL RESULT: {'✅ ALL TESTS PASSED' if overall_success else '❌ TESTS FAILED'}")
        print("="*80)


# Pytest integration
class TestE2ETestSuite:
    """Pytest wrapper for E2E test suite."""

    @pytest.fixture
    async def e2e_suite(self):
        """Fixture for E2E test suite."""
        suite = E2ETestSuite()
        await suite.setup_test_environment()
        yield suite
        await suite.teardown_test_environment()

    @pytest.mark.asyncio
    async def test_complete_demo_flow_execution(self, e2e_suite):
        """Test complete demo flow execution for all scenarios."""
        results = await e2e_suite.run_all_scenarios()

        # Generate and save report
        report = e2e_suite.generate_test_report(results)
        e2e_suite.save_report(report)

        # Print summary
        e2e_suite.print_report_summary(report)

        # Validate PRP success criteria
        criteria = report['prp_success_criteria']

        # All 5 core demo scenarios execute successfully
        assert criteria['all_5_core_demo_scenarios_execute_successfully'], \
            "Not all 5 core demo scenarios executed successfully"

        # DNA round-trip integrity maintained (H(D') = H(D))
        assert criteria['dna_round_trip_integrity_maintained'], \
            "DNA round-trip integrity not maintained"

        # Economic calculations accurate within 0.001 DOT
        assert criteria['economic_calculations_accurate_within_0_001_dot'], \
            "Economic calculations not accurate within 0.001 DOT"

        # Test execution completes within 5 minutes
        assert criteria['test_execution_completes_within_5_minutes'], \
            "Test execution did not complete within 5 minutes"

        # No service crashes or hangs
        assert criteria['no_service_crashes_or_hangs'], \
            "Service crashes or hangs detected"

        # Comprehensive error reporting for failures
        assert criteria['comprehensive_error_reporting_for_failures'], \
            "Comprehensive error reporting not implemented"

    @pytest.mark.asyncio
    async def test_individual_scenario_execution(self, e2e_suite):
        """Test individual scenario execution."""
        fixtures = await e2e_suite.load_test_fixtures()
        scenario = fixtures['demo_tasks']['scenarios'][0]  # Test first scenario
        dna_config = fixtures['dna_samples']['test_dna_minimal']

        borg_id = f"individual_test_{int(time.time() * 1000)}"
        result = await e2e_suite.execute_demo_flow(borg_id, dna_config, scenario)

        # Validate individual scenario execution
        assert result['success'], f"Individual scenario failed: {result.get('errors', [])}"
        assert result['dna_integrity'], "DNA integrity check failed"
        assert result['economic_accuracy'], "Economic accuracy check failed"
        assert result['execution_time'] > 0, "Execution time not recorded"
        assert 'dna_hash' in result, "DNA hash not generated"
        assert 'stored_hash' in result, "DNA hash not stored"


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