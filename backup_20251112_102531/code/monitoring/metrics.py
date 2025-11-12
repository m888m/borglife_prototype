"""
BorgLife Phase 1 Success Metrics Tracking

Comprehensive metrics collection and reporting for Phase 1 validation.
Tracks all success criteria from the strategy document.
"""

import time
import json
import asyncio
from typing import Dict, List, Any, Optional
from decimal import Decimal
from pathlib import Path

from jam_mock import JAMInterface
from synthesis import DNAParser
from archon_adapter import ArchonServiceAdapter


class Phase1MetricsTracker:
    """
    Tracks Phase 1 success metrics as defined in borglife-archon-strategy.md

    Success Criteria:
    - ✅ Demo Completion: 5 successful end-to-end demo runs
    - ✅ DNA Integrity: >95% round-trip accuracy
    - ✅ Archon Integration: All adapter tests passing, <100ms response times, 99% uptime
    - ✅ On-Chain Storage: 10+ DNA hashes stored on Kusama testnet
    - ✅ User Experience: Sponsor UI functional for task submission and result viewing
    - ✅ Performance: <5s task execution, <2s phenotype build, <0.01 DOT average cost
    - ✅ Testing Coverage: >90% adapter code coverage, integration tests for full loop
    - ✅ Documentation: Complete setup guide, demo walkthrough, troubleshooting
    - ✅ Community Validation: 3+ external beta testers complete demo successfully
    """

    def __init__(self, jam: JAMInterface, archon_adapter: ArchonServiceAdapter):
        """
        Initialize metrics tracker.

        Args:
            jam: JAM interface for on-chain operations
            archon_adapter: Archon adapter for service monitoring
        """
        self.jam = jam
        self.archon_adapter = archon_adapter

        # Metrics storage
        self.metrics = {
            # Demo completion metrics
            'demo_runs_total': 0,
            'demo_runs_successful': 0,
            'demo_runs_failed': 0,
            'demo_execution_times': [],

            # DNA integrity metrics
            'dna_integrity_checks': 0,
            'dna_integrity_passed': 0,
            'dna_roundtrip_tests': 0,
            'dna_roundtrip_passed': 0,

            # Archon integration metrics
            'archon_health_checks': 0,
            'archon_healthy_checks': 0,
            'archon_response_times': [],
            'archon_adapter_tests_run': 0,
            'archon_adapter_tests_passed': 0,

            # On-chain storage metrics
            'dna_hashes_stored_local': 0,
            'dna_hashes_stored_kusama': 0,
            'kusama_transactions': 0,
            'kusama_transaction_successes': 0,

            # Performance metrics
            'task_execution_times': [],
            'phenotype_build_times': [],
            'execution_costs': [],

            # Testing metrics
            'integration_tests_run': 0,
            'integration_tests_passed': 0,
            'code_coverage_percent': 0.0,

            # User experience metrics
            'ui_interactions': 0,
            'ui_errors': 0,
            'task_submissions': 0,
            'result_views': 0,

            # Community validation metrics
            'beta_testers': 0,
            'beta_demo_completions': 0,
            'beta_feedback_scores': [],

            # Timing
            'start_time': time.time(),
            'last_updated': time.time()
        }

    def record_demo_run(self, success: bool, execution_time: float, cost: Optional[Decimal] = None):
        """Record demo execution."""
        self.metrics['demo_runs_total'] += 1
        if success:
            self.metrics['demo_runs_successful'] += 1
        else:
            self.metrics['demo_runs_failed'] += 1

        self.metrics['demo_execution_times'].append(execution_time)
        if cost:
            self.metrics['execution_costs'].append(float(cost))

        self._update_timestamp()

    def record_dna_integrity_check(self, passed: bool):
        """Record DNA integrity verification."""
        self.metrics['dna_integrity_checks'] += 1
        if passed:
            self.metrics['dna_integrity_passed'] += 1
        self._update_timestamp()

    def record_dna_roundtrip_test(self, passed: bool):
        """Record DNA roundtrip test (YAML → BorgDNA → YAML)."""
        self.metrics['dna_roundtrip_tests'] += 1
        if passed:
            self.metrics['dna_roundtrip_passed'] += 1
        self._update_timestamp()

    async def record_archon_health_check(self, healthy: bool, response_time: Optional[float] = None):
        """Record Archon health check."""
        self.metrics['archon_health_checks'] += 1
        if healthy:
            self.metrics['archon_healthy_checks'] += 1

        if response_time:
            self.metrics['archon_response_times'].append(response_time)

        self._update_timestamp()

    def record_archon_adapter_test(self, passed: bool):
        """Record Archon adapter unit test."""
        self.metrics['archon_adapter_tests_run'] += 1
        if passed:
            self.metrics['archon_adapter_tests_passed'] += 1
        self._update_timestamp()

    def record_dna_storage(self, local: bool = True, kusama: bool = False):
        """Record DNA hash storage."""
        if local:
            self.metrics['dna_hashes_stored_local'] += 1
        if kusama:
            self.metrics['dna_hashes_stored_kusama'] += 1
        self._update_timestamp()

    async def record_kusama_transaction(self, success: bool):
        """Record Kusama transaction."""
        self.metrics['kusama_transactions'] += 1
        if success:
            self.metrics['kusama_transaction_successes'] += 1
        self._update_timestamp()

    def record_performance_metric(self, metric_type: str, value: float):
        """Record performance metric."""
        if metric_type == 'task_execution':
            self.metrics['task_execution_times'].append(value)
        elif metric_type == 'phenotype_build':
            self.metrics['phenotype_build_times'].append(value)
        self._update_timestamp()

    def record_integration_test(self, passed: bool):
        """Record integration test result."""
        self.metrics['integration_tests_run'] += 1
        if passed:
            self.metrics['integration_tests_passed'] += 1
        self._update_timestamp()

    def record_ui_interaction(self, interaction_type: str, success: bool = True):
        """Record UI interaction."""
        if interaction_type == 'task_submission':
            self.metrics['task_submissions'] += 1
        elif interaction_type == 'result_view':
            self.metrics['result_views'] += 1

        self.metrics['ui_interactions'] += 1
        if not success:
            self.metrics['ui_errors'] += 1

        self._update_timestamp()

    def record_beta_feedback(self, tester_id: str, completed_demo: bool, feedback_score: Optional[int] = None):
        """Record beta tester feedback."""
        if tester_id not in [f"beta_tester_{i}" for i in range(self.metrics['beta_testers'])]:
            self.metrics['beta_testers'] += 1

        if completed_demo:
            self.metrics['beta_demo_completions'] += 1

        if feedback_score is not None:
            self.metrics['beta_feedback_scores'].append(feedback_score)

        self._update_timestamp()

    def set_code_coverage(self, coverage_percent: float):
        """Set code coverage percentage."""
        self.metrics['code_coverage_percent'] = coverage_percent
        self._update_timestamp()

    def _update_timestamp(self):
        """Update last modified timestamp."""
        self.metrics['last_updated'] = time.time()

    def get_success_criteria_status(self) -> Dict[str, Any]:
        """
        Evaluate Phase 1 success criteria status.

        Returns:
            Dict with each criterion and its status
        """
        criteria = {}

        # Demo Completion: 5 successful end-to-end demo runs
        criteria['demo_completion'] = {
            'target': '5 successful end-to-end demo runs',
            'current': self.metrics['demo_runs_successful'],
            'status': '✅ PASS' if self.metrics['demo_runs_successful'] >= 5 else '⏳ PENDING',
            'progress': f"{self.metrics['demo_runs_successful']}/5"
        }

        # DNA Integrity: >95% round-trip accuracy
        dna_integrity_rate = (self.metrics['dna_integrity_passed'] / self.metrics['dna_integrity_checks'] * 100) if self.metrics['dna_integrity_checks'] > 0 else 0
        criteria['dna_integrity'] = {
            'target': '>95% round-trip accuracy',
            'current': f"{dna_integrity_rate:.1f}%",
            'status': '✅ PASS' if dna_integrity_rate >= 95 else '⏳ PENDING'
        }

        # Archon Integration: All adapter tests passing, <100ms response times, 99% uptime
        adapter_test_rate = (self.metrics['archon_adapter_tests_passed'] / self.metrics['archon_adapter_tests_run'] * 100) if self.metrics['archon_adapter_tests_run'] > 0 else 0
        health_rate = (self.metrics['archon_healthy_checks'] / self.metrics['archon_health_checks'] * 100) if self.metrics['archon_health_checks'] > 0 else 0
        avg_response_time = sum(self.metrics['archon_response_times']) / len(self.metrics['archon_response_times']) if self.metrics['archon_response_times'] else 0

        criteria['archon_integration'] = {
            'target': '99% uptime, <100ms response, 100% adapter tests',
            'current': f"{health_rate:.1f}% uptime, {avg_response_time:.1f}ms avg, {adapter_test_rate:.1f}% tests",
            'status': '✅ PASS' if (health_rate >= 99 and avg_response_time < 100 and adapter_test_rate >= 100) else '⏳ PENDING'
        }

        # On-Chain Storage: 10+ DNA hashes stored on Kusama testnet
        criteria['on_chain_storage'] = {
            'target': '10+ DNA hashes stored on Kusama',
            'current': self.metrics['dna_hashes_stored_kusama'],
            'status': '✅ PASS' if self.metrics['dna_hashes_stored_kusama'] >= 10 else '⏳ PENDING',
            'progress': f"{self.metrics['dna_hashes_stored_kusama']}/10"
        }

        # Performance: <5s task execution, <2s phenotype build, <0.01 DOT average cost
        avg_task_time = sum(self.metrics['task_execution_times']) / len(self.metrics['task_execution_times']) if self.metrics['task_execution_times'] else 0
        avg_build_time = sum(self.metrics['phenotype_build_times']) / len(self.metrics['phenotype_build_times']) if self.metrics['phenotype_build_times'] else 0
        avg_cost = sum(self.metrics['execution_costs']) / len(self.metrics['execution_costs']) if self.metrics['execution_costs'] else 0

        criteria['performance'] = {
            'target': '<5s task execution, <2s phenotype build, <0.01 DOT avg cost',
            'current': f"{avg_task_time:.2f}s task, {avg_build_time:.2f}s build, {avg_cost:.6f} DOT cost",
            'status': '✅ PASS' if (avg_task_time < 5 and avg_build_time < 2 and avg_cost < 0.01) else '⏳ PENDING'
        }

        # Testing Coverage: >90% adapter code coverage, integration tests for full loop
        test_rate = (self.metrics['integration_tests_passed'] / self.metrics['integration_tests_run'] * 100) if self.metrics['integration_tests_run'] > 0 else 0

        criteria['testing_coverage'] = {
            'target': '>90% code coverage, integration tests passing',
            'current': f"{self.metrics['code_coverage_percent']:.1f}% coverage, {test_rate:.1f}% tests",
            'status': '✅ PASS' if (self.metrics['code_coverage_percent'] >= 90 and test_rate >= 95) else '⏳ PENDING'
        }

        # Community Validation: 3+ external beta testers complete demo successfully
        criteria['community_validation'] = {
            'target': '3+ external beta testers complete demo',
            'current': self.metrics['beta_demo_completions'],
            'status': '✅ PASS' if self.metrics['beta_demo_completions'] >= 3 else '⏳ PENDING',
            'progress': f"{self.metrics['beta_demo_completions']}/3"
        }

        return criteria

    def get_overall_status(self) -> Dict[str, Any]:
        """Get overall Phase 1 status."""
        criteria_status = self.get_success_criteria_status()
        passed_criteria = sum(1 for c in criteria_status.values() if c['status'] == '✅ PASS')
        total_criteria = len(criteria_status)

        runtime_seconds = time.time() - self.metrics['start_time']

        return {
            'phase': 'Phase 1',
            'runtime_seconds': runtime_seconds,
            'success_criteria_passed': passed_criteria,
            'success_criteria_total': total_criteria,
            'overall_status': '✅ COMPLETE' if passed_criteria == total_criteria else f'⏳ {passed_criteria}/{total_criteria} criteria met',
            'criteria_details': criteria_status,
            'metrics_summary': self.get_metrics_summary()
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        runtime_seconds = time.time() - self.metrics['start_time']

        return {
            'runtime_seconds': runtime_seconds,
            'demo_runs': {
                'total': self.metrics['demo_runs_total'],
                'successful': self.metrics['demo_runs_successful'],
                'failed': self.metrics['demo_runs_failed'],
                'success_rate': (self.metrics['demo_runs_successful'] / self.metrics['demo_runs_total'] * 100) if self.metrics['demo_runs_total'] > 0 else 0
            },
            'dna_integrity': {
                'checks': self.metrics['dna_integrity_checks'],
                'passed': self.metrics['dna_integrity_passed'],
                'rate': (self.metrics['dna_integrity_passed'] / self.metrics['dna_integrity_checks'] * 100) if self.metrics['dna_integrity_checks'] > 0 else 0
            },
            'archon_integration': {
                'health_checks': self.metrics['archon_health_checks'],
                'healthy': self.metrics['archon_healthy_checks'],
                'uptime_rate': (self.metrics['archon_healthy_checks'] / self.metrics['archon_health_checks'] * 100) if self.metrics['archon_health_checks'] > 0 else 0,
                'avg_response_time_ms': (sum(self.metrics['archon_response_times']) / len(self.metrics['archon_response_times']) * 1000) if self.metrics['archon_response_times'] else 0
            },
            'on_chain_storage': {
                'local_hashes': self.metrics['dna_hashes_stored_local'],
                'kusama_hashes': self.metrics['dna_hashes_stored_kusama'],
                'kusama_transactions': self.metrics['kusama_transactions'],
                'kusama_success_rate': (self.metrics['kusama_transaction_successes'] / self.metrics['kusama_transactions'] * 100) if self.metrics['kusama_transactions'] > 0 else 0
            },
            'performance': {
                'avg_task_execution_time': sum(self.metrics['task_execution_times']) / len(self.metrics['task_execution_times']) if self.metrics['task_execution_times'] else 0,
                'avg_phenotype_build_time': sum(self.metrics['phenotype_build_times']) / len(self.metrics['phenotype_build_times']) if self.metrics['phenotype_build_times'] else 0,
                'avg_execution_cost': sum(self.metrics['execution_costs']) / len(self.metrics['execution_costs']) if self.metrics['execution_costs'] else 0
            },
            'testing': {
                'integration_tests_run': self.metrics['integration_tests_run'],
                'integration_tests_passed': self.metrics['integration_tests_passed'],
                'code_coverage_percent': self.metrics['code_coverage_percent']
            },
            'user_experience': {
                'ui_interactions': self.metrics['ui_interactions'],
                'ui_errors': self.metrics['ui_errors'],
                'task_submissions': self.metrics['task_submissions'],
                'result_views': self.metrics['result_views']
            },
            'community': {
                'beta_testers': self.metrics['beta_testers'],
                'beta_demo_completions': self.metrics['beta_demo_completions'],
                'avg_feedback_score': sum(self.metrics['beta_feedback_scores']) / len(self.metrics['beta_feedback_scores']) if self.metrics['beta_feedback_scores'] else 0
            }
        }

    def save_report(self, filename: Optional[str] = None) -> str:
        """Save comprehensive metrics report to file."""
        if filename is None:
            timestamp = int(time.time())
            filename = f"phase1_metrics_report_{timestamp}.json"

        report = {
            'generated_at': time.time(),
            'phase': 'Phase 1',
            'overall_status': self.get_overall_status(),
            'detailed_metrics': self.get_metrics_summary(),
            'success_criteria': self.get_success_criteria_status()
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return filename

    def print_report(self):
        """Print formatted metrics report."""
        status = self.get_overall_status()
        criteria = status['criteria_details']

        print("\n" + "="*80)
        print("BORGLIFE PHASE 1 SUCCESS METRICS REPORT")
        print("="*80)
        print(f"Runtime: {status['runtime_seconds']:.0f} seconds")
        print(f"Success Criteria: {status['success_criteria_passed']}/{status['success_criteria_total']}")
        print(f"Overall Status: {status['overall_status']}")
        print()

        print("SUCCESS CRITERIA STATUS:")
        print("-" * 40)
        for name, details in criteria.items():
            print(f"• {name.replace('_', ' ').title()}: {details['status']}")
            print(f"  Target: {details['target']}")
            print(f"  Current: {details['current']}")
            if 'progress' in details:
                print(f"  Progress: {details['progress']}")
            print()

        # Key metrics summary
        metrics = status['metrics_summary']
        print("KEY METRICS SUMMARY:")
        print("-" * 40)
        print(f"Demo Runs: {metrics['demo_runs']['successful']}/{metrics['demo_runs']['total']} ({metrics['demo_runs']['success_rate']:.1f}%)")
        print(f"DNA Integrity: {metrics['dna_integrity']['rate']:.1f}%")
        print(f"Archon Uptime: {metrics['archon_integration']['uptime_rate']:.1f}%")
        print(f"Avg Response Time: {metrics['archon_integration']['avg_response_time_ms']:.1f}ms")
        print(f"Kusama Hashes Stored: {metrics['on_chain_storage']['kusama_hashes']}")
        print(f"Avg Task Time: {metrics['performance']['avg_task_execution_time']:.2f}s")
        print(f"Avg Cost: {metrics['performance']['avg_execution_cost']:.6f} DOT")
        print(f"Code Coverage: {metrics['testing']['code_coverage_percent']:.1f}%")
        print(f"Beta Testers: {metrics['community']['beta_demo_completions']}/3")
        print("="*80)