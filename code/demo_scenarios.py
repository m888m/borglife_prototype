#!/usr/bin/env python3
"""
BorgLife Phase 1 End-to-End Demo Scenarios

Executable demo scripts that showcase the complete BorgLife workflow:
funding → execution → encoding → storage → decoding

These scenarios validate the integration between all components and
demonstrate the Phase 1 capabilities.
"""

import asyncio
import time
import json
from decimal import Decimal
from typing import Dict, List, Any
from pathlib import Path

from jam_mock import LocalJAMMock, WestendAdapter
from synthesis import DNAParser, PhenotypeBuilder, BorgDNA
from archon_adapter import ArchonServiceAdapter, ArchonConfig


class DemoMetrics:
    """Track demo execution metrics."""

    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            'demo_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_execution_time': 0,
            'dna_integrity_checks': 0,
            'dna_integrity_passed': 0,
            'total_cost': Decimal('0'),
            'borgs_created': 0,
            'tasks_executed': 0,
            'archon_calls': 0,
            'archon_errors': 0
        }

    def record_demo_start(self):
        """Record demo execution start."""
        self.start_time = time.time()

    def record_demo_success(self, execution_time: float, cost: Decimal):
        """Record successful demo completion."""
        self.metrics['demo_runs'] += 1
        self.metrics['successful_runs'] += 1
        self.metrics['total_execution_time'] += execution_time
        self.metrics['total_cost'] += cost

    def record_demo_failure(self, execution_time: float):
        """Record failed demo execution."""
        self.metrics['demo_runs'] += 1
        self.metrics['failed_runs'] += 1
        self.metrics['total_execution_time'] += execution_time

    def record_dna_integrity_check(self, passed: bool):
        """Record DNA integrity verification."""
        self.metrics['dna_integrity_checks'] += 1
        if passed:
            self.metrics['dna_integrity_passed'] += 1

    def record_borg_creation(self):
        """Record borg creation."""
        self.metrics['borgs_created'] += 1

    def record_task_execution(self):
        """Record task execution."""
        self.metrics['tasks_executed'] += 1

    def record_archon_call(self, success: bool = True):
        """Record Archon service call."""
        self.metrics['archon_calls'] += 1
        if not success:
            self.metrics['archon_errors'] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        total_time = time.time() - self.start_time
        success_rate = (self.metrics['successful_runs'] / self.metrics['demo_runs'] * 100) if self.metrics['demo_runs'] > 0 else 0
        dna_integrity_rate = (self.metrics['dna_integrity_passed'] / self.metrics['dna_integrity_checks'] * 100) if self.metrics['dna_integrity_checks'] > 0 else 0

        return {
            'total_runtime_seconds': total_time,
            'demo_runs': self.metrics['demo_runs'],
            'successful_runs': self.metrics['successful_runs'],
            'failed_runs': self.metrics['failed_runs'],
            'success_rate_percent': round(success_rate, 2),
            'avg_execution_time_seconds': round(self.metrics['total_execution_time'] / self.metrics['demo_runs'], 2) if self.metrics['demo_runs'] > 0 else 0,
            'total_cost_dot': float(self.metrics['total_cost']),
            'dna_integrity_rate_percent': round(dna_integrity_rate, 2),
            'borgs_created': self.metrics['borgs_created'],
            'tasks_executed': self.metrics['tasks_executed'],
            'archon_calls': self.metrics['archon_calls'],
            'archon_errors': self.metrics['archon_errors'],
            'archon_success_rate_percent': round((self.metrics['archon_calls'] - self.metrics['archon_errors']) / self.metrics['archon_calls'] * 100, 2) if self.metrics['archon_calls'] > 0 else 0
        }


class BorgLifeDemo:
    """
    Complete BorgLife Phase 1 demo execution engine.

    Runs end-to-end scenarios demonstrating the full workflow.
    """

    def __init__(self, jam_mode: str = "local", use_westend: bool = False):
        """
        Initialize demo environment.

        Args:
            jam_mode: JAM implementation mode ("local", "westend", "hybrid")
            use_westend: Whether to include Westend validation
        """
        self.jam_mode = jam_mode
        self.use_westend = use_westend
        self.jam: LocalJAMMock = None
        self.westend_adapter: WestendAdapter = None
        self.archon_adapter: ArchonServiceAdapter = None
        self.phenotype_builder: PhenotypeBuilder = None
        self.metrics = DemoMetrics()

    async def setup(self):
        """Setup demo environment."""
        # Initialize JAM
        if self.jam_mode == "local":
            self.jam = LocalJAMMock()
        elif self.jam_mode == "westend":
            # In real implementation, would need keypair
            self.westend_adapter = WestendAdapter(rpc_url="wss://westend-rpc.polkadot.io")
            self.jam = self.westend_adapter
        else:  # hybrid
            self.jam = LocalJAMMock()
            if self.use_westend:
                self.westend_adapter = WestendAdapter(rpc_url="wss://westend-rpc.polkadot.io")

        # Initialize Archon adapter
        config = ArchonConfig()
        self.archon_adapter = ArchonServiceAdapter(config)
        await self.archon_adapter.initialize()

        # Initialize phenotype builder
        self.phenotype_builder = PhenotypeBuilder(self.archon_adapter)

    async def teardown(self):
        """Clean up demo environment."""
        if self.archon_adapter:
            await self.archon_adapter.close()

    async def run_single_demo(self, borg_id: str, funding_amount: float = 0.1) -> Dict[str, Any]:
        """
        Run a single complete demo scenario.

        Returns:
            Demo execution results and metrics
        """
        demo_start = time.time()

        try:
            # 1. FUNDING: Fund borg with DOT
            await self.jam.update_wealth(
                borg_id=borg_id,
                amount=Decimal(str(funding_amount)),
                operation="revenue",
                description="Demo funding"
            )
            self.metrics.record_borg_creation()

            # 2. EXECUTION: Create borg from DNA
            dna = DNAParser.create_example_dna(borg_id)
            phenotype = await self.phenotype_builder.build(dna)

            # Execute sample task
            task = "Summarize the key evolution mechanisms in BorgLife"
            result = await phenotype.execute_task(task)
            self.metrics.record_task_execution()
            self.metrics.record_archon_call('error' not in result)

            execution_cost = Decimal(str(result.get('cost', 0)))

            # 3. ENCODING: Serialize DNA to YAML
            dna_yaml = DNAParser.to_yaml(dna)

            # 4. STORAGE: Store DNA hash
            dna_hash = dna.compute_hash()
            store_result = await self.jam.store_dna_hash(borg_id, dna_hash)
            assert store_result['success'], "DNA storage failed"

            # 5. DECODING: Retrieve and verify
            stored_hash = await self.jam.retrieve_dna_hash(borg_id)
            integrity_check = await self.jam.verify_dna_integrity(borg_id, dna_hash)
            self.metrics.record_dna_integrity_check(integrity_check)

            # Round-trip verification
            decoded_dna = DNAParser.from_yaml(dna_yaml)
            roundtrip_integrity = decoded_dna.compute_hash() == dna_hash

            # Deduct execution cost
            await self.jam.update_wealth(
                borg_id=borg_id,
                amount=execution_cost,
                operation="cost",
                description=f"Task execution: {task[:50]}..."
            )

            demo_time = time.time() - demo_start
            self.metrics.record_demo_success(demo_time, execution_cost)

            return {
                'success': True,
                'borg_id': borg_id,
                'execution_time': demo_time,
                'dna_integrity': integrity_check,
                'roundtrip_integrity': roundtrip_integrity,
                'cost': float(execution_cost),
                'task_result': result.get('result', 'No result'),
                'final_balance': float(await self.jam.get_wealth_balance(borg_id))
            }

        except Exception as e:
            demo_time = time.time() - demo_start
            self.metrics.record_demo_failure(demo_time)

            return {
                'success': False,
                'borg_id': borg_id,
                'execution_time': demo_time,
                'error': str(e)
            }

    async def run_multiple_demos(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Run multiple demo scenarios.

        Args:
            count: Number of demos to run

        Returns:
            List of demo results
        """
        results = []

        for i in range(count):
            borg_id = f"demo_borg_{i}_{int(time.time())}"
            result = await self.run_single_demo(borg_id)
            results.append(result)

            # Small delay between demos
            await asyncio.sleep(0.1)

        return results

    async def run_stress_test(self, concurrent_borgs: int = 10) -> Dict[str, Any]:
        """
        Run stress test with multiple concurrent borgs.

        Args:
            concurrent_borgs: Number of borgs to run concurrently

        Returns:
            Stress test results
        """
        start_time = time.time()

        # Create tasks for concurrent execution
        tasks = []
        for i in range(concurrent_borgs):
            borg_id = f"stress_borg_{i}_{int(time.time())}"
            tasks.append(self.run_single_demo(borg_id, funding_amount=0.05))

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()

        # Process results
        successful = 0
        failed = 0
        total_time = 0
        total_cost = Decimal('0')

        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif result['success']:
                successful += 1
                total_time += result['execution_time']
                total_cost += Decimal(str(result['cost']))
            else:
                failed += 1

        return {
            'concurrent_borgs': concurrent_borgs,
            'successful': successful,
            'failed': failed,
            'total_time': end_time - start_time,
            'avg_execution_time': total_time / successful if successful > 0 else 0,
            'total_cost': float(total_cost),
            'success_rate': successful / concurrent_borgs * 100
        }

    def save_results(self, results: List[Dict[str, Any]], filename: str = None):
        """Save demo results to file."""
        if filename is None:
            timestamp = int(time.time())
            filename = f"demo_results_{timestamp}.json"

        output = {
            'timestamp': time.time(),
            'jam_mode': self.jam_mode,
            'use_westend': self.use_westend,
            'metrics': self.metrics.get_summary(),
            'results': results
        }

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"Results saved to {filename}")

    def print_summary(self):
        """Print demo execution summary."""
        summary = self.metrics.get_summary()

        print("\n" + "="*60)
        print("BORGLIFE PHASE 1 DEMO SUMMARY")
        print("="*60)
        print(f"Total Runtime: {summary['total_runtime_seconds']:.2f} seconds")
        print(f"Demo Runs: {summary['demo_runs']}")
        print(f"Successful: {summary['successful_runs']}")
        print(f"Failed: {summary['failed_runs']}")
        print(f"Success Rate: {summary['success_rate_percent']:.1f}%")
        print(f"Avg Execution Time: {summary['avg_execution_time_seconds']:.2f}s")
        print(f"Total Cost: {summary['total_cost_dot']:.6f} DOT")
        print(f"DNA Integrity Rate: {summary['dna_integrity_rate_percent']:.1f}%")
        print(f"Borgs Created: {summary['borgs_created']}")
        print(f"Tasks Executed: {summary['tasks_executed']}")
        print(f"Archon Calls: {summary['archon_calls']}")
        print(f"Archon Errors: {summary['archon_errors']}")
        print(f"Archon Success Rate: {summary['archon_success_rate_percent']:.1f}%")
        print("="*60)


async def main():
    """Main demo execution."""
    import argparse

    parser = argparse.ArgumentParser(description="BorgLife Phase 1 Demo")
    parser.add_argument('--mode', choices=['local', 'westend', 'hybrid'], default='local')
    parser.add_argument('--count', type=int, default=5, help='Number of demo runs')
    parser.add_argument('--stress-test', type=int, help='Run stress test with N concurrent borgs')
    parser.add_argument('--westend', action='store_true', help='Include Westend validation')

    args = parser.parse_args()

    # Initialize demo
    demo = BorgLifeDemo(jam_mode=args.mode, use_westend=args.westend)
    await demo.setup()

    try:
        if args.stress_test:
            print(f"Running stress test with {args.stress_test} concurrent borgs...")
            results = await demo.run_stress_test(args.stress_test)
            print("Stress test results:")
            print(json.dumps(results, indent=2))
        else:
            print(f"Running {args.count} demo scenarios...")
            results = await demo.run_multiple_demos(args.count)

            # Save results
            demo.save_results(results)

            # Print summary
            demo.print_summary()

    finally:
        await demo.teardown()


if __name__ == "__main__":
    asyncio.run(main())