#!/usr/bin/env python3
"""
USDB Distribution Script for Phase 2A

Distributes USDB tokens to borgs for testing economic scenarios.
Handles automated distribution, balance tracking, and testing setup.
"""

import asyncio
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import keyring
from dotenv import load_dotenv
from supabase import create_client
from jam_mock.borg_address_manager import BorgAddressManager
from jam_mock.demo_audit_logger import DemoAuditLogger
from jam_mock.demo_cost_controller import DemoCostController
from jam_mock.economic_validator import EconomicValidator
from jam_mock.ethical_compliance_monitor import EthicalComplianceMonitor
from jam_mock.inter_borg_transfer import InterBorgTransfer
from jam_mock.transaction_manager import TransactionManager
from jam_mock.westend_adapter import USDB, WestendAdapter
from scripts.usdb_distribution import USDBDistributor


class USDBDistributor:
    """Distributes USDB tokens to borgs for testing."""

    def __init__(self):
        # Initialize components
        self.westend_adapter = WestendAdapter(
            rpc_url=os.getenv(
                "WESTEND_RPC_URL", "wss://westend-asset-hub-rpc.polkadot.io"
            )
        )
        logger_name = "borglife"
        load_dotenv(env_file=f".env.{logger_name}")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        print(f"Supabase URL: {supabase_url}")
        print(f"Supabase Key: {supabase_key}")

        # Initialize with mock Supabase client (would be real in production)
        self.supabase_client = create_client(
            supabase_url,
            supabase_key,
        )

        print(f"Supabase client: {self.supabase_client}")

        self.address_manager = BorgAddressManager(
            supabase_client=self.supabase_client, audit_logger=DemoAuditLogger()
        )

        self.cost_controller = DemoCostController()
        self.compliance_monitor = EthicalComplianceMonitor()
        self.economic_validator = EconomicValidator(
            cost_controller=self.cost_controller,
            compliance_monitor=self.compliance_monitor,
            supabase_client=self.supabase_client,
        )

        self.transaction_manager = TransactionManager(
            kusama_adapter=self.westend_adapter,
            keypair_manager=None,  # Would need proper keypair manager
        )

        self.transfer_protocol = InterBorgTransfer(
            westend_adapter=self.westend_adapter,
            address_manager=self.address_manager,
            economic_validator=self.economic_validator,
            transaction_manager=self.transaction_manager,
        )

        # Distribution configuration
        self.distribution_amount = Decimal("100.0")  # 100 USDB per borg
        self.max_borgs = 10  # Maximum borgs to fund

    async def distribute_to_test_borgs(self, borg_ids: List[str]) -> Dict[str, Any]:
        """
        Distribute USDB to test borgs using live blockchain transfers.

        Args:
            borg_ids: List of borg IDs to fund

        Returns:
            Distribution results
        """
        results = {
            "total_borgs": len(borg_ids),
            "successful_distributions": 0,
            "failed_distributions": 0,
            "total_distributed": Decimal("0"),
            "distribution_details": [],
        }

        print(f"🚀 Starting LIVE USDB distribution to {len(borg_ids)} borgs")
        print(f"   Amount per borg: {self.distribution_amount} USDB")
        print("=" * 60)

        # Get asset ID from config
        asset_id = self._get_usdb_asset_id()
        if not asset_id:
            return {
                "error": "USDB asset ID not found in configuration. Run create_usdb_asset.py first."
            }

        print(f"   Using USDB Asset ID: {asset_id}")

        # Limit to max_borgs
        borg_ids = borg_ids[: self.max_borgs]

        for i, borg_id in enumerate(borg_ids):
            print(f"\n📋 Distributing to borg {borg_id} ({i+1}/{len(borg_ids)})")

            # Get borg address
            borg_address = self.address_manager.get_borg_address(borg_id)
            if not borg_address:
                print(f"❌ Borg {borg_id} not registered")
                results["failed_distributions"] += 1
                results["distribution_details"].append(
                    {
                        "borg_id": borg_id,
                        "success": False,
                        "error": "Borg not registered",
                    }
                )
                continue

            # Convert amount to planck units
            amount_planck = int(self.distribution_amount * (10**12))

            # Perform live transfer from dispenser
            try:
                transfer_result = await self.westend_adapter.transfer_usdb(
                    from_address=self._get_dispenser_address(),
                    to_address=borg_address,
                    amount=amount_planck,
                    asset_id=asset_id,
                )

                if transfer_result.get("success"):
                    results["successful_distributions"] += 1
                    results["total_distributed"] += self.distribution_amount
                    print(
                        f"✅ Successfully distributed {self.distribution_amount} USDB to {borg_id}"
                    )
                    print(
                        f"   Transaction: {transfer_result.get('transaction_hash', 'N/A')}"
                    )
                else:
                    results["failed_distributions"] += 1
                    print(
                        f"❌ Failed to distribute to {borg_id}: {transfer_result.get('error', 'Unknown error')}"
                    )

                results["distribution_details"].append(
                    {
                        "borg_id": borg_id,
                        "success": transfer_result.get("success", False),
                        "amount": str(self.distribution_amount),
                        "address": borg_address,
                        "transaction_hash": transfer_result.get("transaction_hash"),
                        "error": transfer_result.get("error"),
                    }
                )

            except Exception as e:
                results["failed_distributions"] += 1
                print(f"❌ Transfer error for {borg_id}: {e}")
                results["distribution_details"].append(
                    {"borg_id": borg_id, "success": False, "error": str(e)}
                )

        print("\n" + "=" * 60)
        print("🎉 Distribution Complete!")
        print(f"   Successful: {results['successful_distributions']}")
        print(f"   Failed: {results['failed_distributions']}")
        print(f"   Total Distributed: {results['total_distributed']} USDB")

        return results

    def _get_usdb_asset_id(self) -> Optional[int]:
        """Get USDB asset ID from configuration."""
        try:
            config_path = Path(os.path.dirname(__file__)).parent / ".borglife_config"
            if config_path.exists():
                with open(config_path, "r") as f:
                    for line in f:
                        if line.startswith("USDB_ASSET_ID="):
                            return int(line.split("=", 1)[1].strip())
        except Exception as e:
            print(f"Error reading asset ID: {e}")
        return None

    def _get_dispenser_address(self) -> str:
        """Get dispenser address from keyring."""
        try:
            dispenser_address = keyring.get_password("borglife-dispenser", "address")
            if dispenser_address:
                return dispenser_address
            else:
                raise ValueError("Dispenser address not found in keyring")
        except Exception as e:
            print(f"Error retrieving dispenser address: {e}")
            raise ValueError(
                "Cannot retrieve dispenser address from keyring. Run check_keyring.py to validate dispenser key setup."
            )

    async def setup_economic_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        Set up specific economic test scenarios.

        Args:
            scenario_name: Name of the test scenario

        Returns:
            Scenario setup results
        """
        scenarios = {
            "equal_distribution": self._setup_equal_distribution,
            "wealth_concentration": self._setup_wealth_concentration,
            "trading_pairs": self._setup_trading_pairs,
        }

        if scenario_name not in scenarios:
            return {"error": f"Unknown scenario: {scenario_name}"}

        print(f"🎭 Setting up economic scenario: {scenario_name}")
        return await scenarios[scenario_name]()

    async def _setup_equal_distribution(self) -> Dict[str, Any]:
        """Set up equal wealth distribution scenario."""
        borg_ids = [f"equal_borg_{i}" for i in range(5)]
        return await self.distribute_to_test_borgs(borg_ids)

    async def _setup_wealth_concentration(self) -> Dict[str, Any]:
        """Set up wealth concentration scenario."""
        borg_ids = [
            "rich_borg_1",
            "rich_borg_2",
            "poor_borg_1",
            "poor_borg_2",
            "poor_borg_3",
        ]

        # Distribute different amounts
        results = await self.distribute_to_test_borgs(
            borg_ids[:2]
        )  # Rich borgs get full amount

        # Poor borgs get minimal amounts
        for borg_id in borg_ids[2:]:
            await self._simulate_distribution(borg_id, Decimal("10.0"))  # Only 10 USDB

        return results

    async def _setup_trading_pairs(self) -> Dict[str, Any]:
        """Set up trading pairs scenario."""
        borg_ids = ["trader_a", "trader_b", "market_maker"]
        return await self.distribute_to_test_borgs(borg_ids)

    async def get_distribution_status(self) -> Dict[str, Any]:
        """Get current distribution status."""
        try:
            registered_borgs = self.address_manager.list_registered_borgs()

            status = {
                "total_registered_borgs": len(registered_borgs),
                "borgs_with_usdb": 0,
                "total_usdb_distributed": Decimal("0"),
                "distribution_summary": [],
            }

            for borg in registered_borgs:
                borg_id = borg["borg_id"]
                usdb_balance = self.address_manager.get_balance(borg_id, "USDB") or 0

                if usdb_balance > 0:
                    status["borgs_with_usdb"] += 1
                    usdb_tokens = Decimal(str(usdb_balance)) / Decimal("1000000000000")
                    status["total_usdb_distributed"] += usdb_tokens

                    status["distribution_summary"].append(
                        {
                            "borg_id": borg_id,
                            "usdb_balance": str(usdb_tokens),
                            "address": borg["substrate_address"],
                        }
                    )

            status["total_usdb_distributed"] = str(status["total_usdb_distributed"])
            return status

        except Exception as e:
            return {"error": str(e)}

    async def run_distribution_test(self) -> Dict[str, Any]:
        """Run a complete distribution test cycle."""
        print("🧪 Running USDB Distribution Test")
        print("=" * 50)

        # Test borg IDs
        test_borgs = ["test_borg_1", "test_borg_2", "test_borg_3"]

        # Distribute
        distribution_result = await self.distribute_to_test_borgs(test_borgs)

        # Verify
        status = await self.get_distribution_status()

        # Test transfers between borgs
        transfer_results = []
        if distribution_result["successful_distributions"] >= 2:
            # Try a test transfer
            transfer_result = await self.transfer_protocol.transfer_usdb(
                "test_borg_1", "test_borg_2", Decimal("10.0"), "Test transfer"
            )
            transfer_results.append(transfer_result)

        return {
            "distribution": distribution_result,
            "status": status,
            "transfers": transfer_results,
            "test_passed": distribution_result["successful_distributions"] > 0,
        }


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python usdb_distribution.py <command> [args...]")
        print("Commands:")
        print("  distribute <borg_id1> <borg_id2> ...  - Distribute to specific borgs")
        print("  scenario <scenario_name>            - Setup economic scenario")
        print("  status                               - Show distribution status")
        print("  test                                 - Run distribution test")
        sys.exit(1)

    command = sys.argv[1]

    try:
        distributor = USDBDistributor()

        if command == "distribute":
            borg_ids = sys.argv[2:] if len(sys.argv) > 2 else []
            if not borg_ids:
                print("❌ No borg IDs provided")
                sys.exit(1)

            result = await distributor.distribute_to_test_borgs(borg_ids)
            print(json.dumps(result, indent=2, default=str))

        elif command == "scenario":
            if len(sys.argv) < 3:
                print("❌ Scenario name required")
                sys.exit(1)

            scenario_name = sys.argv[2]
            result = await distributor.setup_economic_test_scenario(scenario_name)
            print(json.dumps(result, indent=2, default=str))

        elif command == "status":
            result = await distributor.get_distribution_status()
            print(json.dumps(result, indent=2, default=str))

        elif command == "test":
            result = await distributor.run_distribution_test()
            print(json.dumps(result, indent=2, default=str))

        else:
            print(f"❌ Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
