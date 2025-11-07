#!/usr/bin/env python3
"""
Economic Scenarios Testing for Phase 2A

Tests various economic interactions between borgs using the fund holding system.
"""

import os
import sys
import asyncio
from typing import Dict, Any, List
from decimal import Decimal
import json

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.usdb_distribution import USDBDistributor
from jam_mock.inter_borg_transfer import InterBorgTransfer
from jam_mock.economic_validator import EconomicValidator
from jam_mock.ethical_compliance_monitor import EthicalComplianceMonitor
from jam_mock.demo_cost_controller import DemoCostController
from jam_mock.demo_audit_logger import DemoAuditLogger

class EconomicScenariosTester:
    """Tests economic scenarios with borg fund holding and transfers."""

    def __init__(self):
        self.distributor = USDBDistributor()
        self.transfer_protocol = self.distributor.transfer_protocol
        self.economic_validator = self.distributor.economic_validator

    async def run_scenario_equal_distribution(self) -> Dict[str, Any]:
        """Test equal wealth distribution scenario."""
        print("🎭 Running Equal Distribution Scenario")
        print("-" * 40)

        # Setup equal distribution
        borg_ids = ['alice', 'bob', 'charlie', 'diana']
        await self.distributor.distribute_to_test_borgs(borg_ids)

        # Test transfers
        transfers = [
            ('alice', 'bob', Decimal('10.0')),
            ('charlie', 'diana', Decimal('15.0')),
            ('bob', 'charlie', Decimal('5.0'))
        ]

        results = await self._execute_transfers(transfers, "Equal Distribution Transfers")

        # Analyze final distribution
        analysis = await self.economic_validator.validate_balance_distribution(borg_ids)

        return {
            'scenario': 'equal_distribution',
            'setup': {'borgs': borg_ids, 'initial_amount': '100.0'},
            'transfers': results,
            'final_analysis': analysis
        }

    async def run_scenario_wealth_concentration(self) -> Dict[str, Any]:
        """Test wealth concentration and redistribution."""
        print("🎭 Running Wealth Concentration Scenario")
        print("-" * 40)

        # Setup concentrated wealth
        rich_borgs = ['rich_borg_1', 'rich_borg_2']
        poor_borgs = ['poor_borg_1', 'poor_borg_2', 'poor_borg_3']

        await self.distributor.distribute_to_test_borgs(rich_borgs)

        # Give poor borgs minimal amounts
        for borg_id in poor_borgs:
            await self.distributor._simulate_distribution(borg_id, Decimal('5.0'))

        # Test redistribution transfers
        transfers = [
            ('rich_borg_1', 'poor_borg_1', Decimal('20.0')),
            ('rich_borg_2', 'poor_borg_2', Decimal('15.0')),
            ('rich_borg_1', 'poor_borg_3', Decimal('10.0'))
        ]

        results = await self._execute_transfers(transfers, "Wealth Redistribution")

        # Analyze wealth distribution
        all_borgs = rich_borgs + poor_borgs
        analysis = await self.economic_validator.validate_balance_distribution(all_borgs)

        return {
            'scenario': 'wealth_concentration',
            'setup': {
                'rich_borgs': rich_borgs,
                'poor_borgs': poor_borgs,
                'rich_initial': '100.0',
                'poor_initial': '5.0'
            },
            'transfers': results,
            'final_analysis': analysis
        }

    async def run_scenario_trading_simulation(self) -> Dict[str, Any]:
        """Test simulated trading between borgs."""
        print("🎭 Running Trading Simulation Scenario")
        print("-" * 40)

        # Setup trading borgs
        borg_ids = ['trader_a', 'trader_b', 'market_maker']
        await self.distributor.distribute_to_test_borgs(borg_ids)

        # Simulate trading activity
        trades = [
            ('trader_a', 'trader_b', Decimal('25.0'), 'Asset trade'),
            ('market_maker', 'trader_a', Decimal('30.0'), 'Market making'),
            ('trader_b', 'market_maker', Decimal('20.0'), 'Settlement'),
            ('trader_a', 'market_maker', Decimal('15.0'), 'Profit taking')
        ]

        results = []
        for from_borg, to_borg, amount, description in trades:
            result = await self.transfer_protocol.transfer_usdb(
                from_borg, to_borg, amount, description
            )
            results.append({
                'from': from_borg,
                'to': to_borg,
                'amount': str(amount),
                'description': description,
                'success': result['success'],
                'error': result.get('errors', []) if not result['success'] else []
            })

        # Analyze trading results
        analysis = await self.economic_validator.validate_balance_distribution(borg_ids)

        return {
            'scenario': 'trading_simulation',
            'setup': {'borgs': borg_ids, 'initial_amount': '100.0'},
            'trades': results,
            'final_analysis': analysis
        }

    async def run_scenario_error_handling(self) -> Dict[str, Any]:
        """Test error handling and edge cases."""
        print("🎭 Running Error Handling Scenario")
        print("-" * 40)

        borg_ids = ['error_test_borg']
        await self.distributor.distribute_to_test_borgs(borg_ids)

        # Test various error conditions
        error_tests = [
            # Insufficient balance
            ('error_test_borg', 'nonexistent', Decimal('200.0'), 'Insufficient balance'),
            # Invalid borg
            ('error_test_borg', 'invalid_borg', Decimal('10.0'), 'Invalid recipient'),
            # Zero amount
            ('error_test_borg', 'error_test_borg', Decimal('0'), 'Zero amount'),
            # Negative amount
            ('error_test_borg', 'error_test_borg', Decimal('-10.0'), 'Negative amount')
        ]

        results = []
        for from_borg, to_borg, amount, test_type in error_tests:
            try:
                result = await self.transfer_protocol.transfer_usdb(
                    from_borg, to_borg, amount, f'Error test: {test_type}'
                )
                results.append({
                    'test_type': test_type,
                    'success': result['success'],
                    'error': result.get('errors', [])
                })
            except Exception as e:
                results.append({
                    'test_type': test_type,
                    'success': False,
                    'error': [str(e)]
                })

        return {
            'scenario': 'error_handling',
            'tests': results
        }

    async def _execute_transfers(self, transfers: List[tuple], description: str) -> List[Dict[str, Any]]:
        """Execute a list of transfers."""
        print(f"📋 Executing {description}")
        results = []

        for from_borg, to_borg, amount in transfers:
            result = await self.transfer_protocol.transfer_usdb(
                from_borg, to_borg, amount, f'{description}: {from_borg} -> {to_borg}'
            )
            results.append({
                'from': from_borg,
                'to': to_borg,
                'amount': str(amount),
                'success': result['success'],
                'error': result.get('errors', []) if not result['success'] else []
            })

        successful = sum(1 for r in results if r['success'])
        print(f"   ✅ {successful}/{len(results)} transfers successful")

        return results

    async def run_all_scenarios(self) -> Dict[str, Any]:
        """Run all economic scenarios."""
        print("🚀 Running All Economic Scenarios")
        print("=" * 50)

        scenarios = [
            ('equal_distribution', self.run_scenario_equal_distribution),
            ('wealth_concentration', self.run_scenario_wealth_concentration),
            ('trading_simulation', self.run_scenario_trading_simulation),
            ('error_handling', self.run_scenario_error_handling)
        ]

        results = {}
        for scenario_name, scenario_func in scenarios:
            try:
                print(f"\n🎭 Starting scenario: {scenario_name}")
                result = await scenario_func()
                results[scenario_name] = result
                print(f"✅ Scenario {scenario_name} completed")
            except Exception as e:
                print(f"❌ Scenario {scenario_name} failed: {e}")
                results[scenario_name] = {'error': str(e)}

        # Overall summary
        summary = {
            'total_scenarios': len(scenarios),
            'completed_scenarios': len([r for r in results.values() if 'error' not in r]),
            'failed_scenarios': len([r for r in results.values() if 'error' in r]),
            'scenarios': list(results.keys())
        }

        results['summary'] = summary

        print("\n" + "=" * 50)
        print("🎉 All Scenarios Complete!")
        print(f"   Completed: {summary['completed_scenarios']}")
        print(f"   Failed: {summary['failed_scenarios']}")

        return results

async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_economic_scenarios.py <command>")
        print("Commands:")
        print("  all          - Run all scenarios")
        print("  equal        - Run equal distribution scenario")
        print("  concentration - Run wealth concentration scenario")
        print("  trading      - Run trading simulation scenario")
        print("  errors       - Run error handling tests")
        sys.exit(1)

    command = sys.argv[1]

    try:
        tester = EconomicScenariosTester()

        if command == 'all':
            result = await tester.run_all_scenarios()
        elif command == 'equal':
            result = await tester.run_scenario_equal_distribution()
        elif command == 'concentration':
            result = await tester.run_scenario_wealth_concentration()
        elif command == 'trading':
            result = await tester.run_scenario_trading_simulation()
        elif command == 'errors':
            result = await tester.run_scenario_error_handling()
        else:
            print(f"❌ Unknown command: {command}")
            sys.exit(1)

        # Save results to file
        output_file = f'economic_scenarios_{command}_results.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        print(f"\n📄 Results saved to {output_file}")
        print(json.dumps(result, indent=2, default=str))

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())