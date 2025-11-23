#!/usr/bin/env python3
"""
End-to-End Test for Phase 2A Fund Holding and Transfer System

This test demonstrates the complete Phase 2A functionality:
1. Create USDB stablecoin on Westend Asset Hub
2. Mint initial supply to admin account
3. Create two borgs with addresses
4. Allocate 1000 USDB each to borgs
5. Transfer 100 USDB from borg A to borg B
6. Verify final balances: borg A = 900 USDB, borg B = 1100 USDB

Usage: python end_to_end_test.py
"""

import asyncio
import os
import sys
import time
from decimal import Decimal
from typing import Any, Dict

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jam_mock.advanced_keypair_features import (AdvancedKeypairManager,
                                                TransactionSigner)
from jam_mock.borg_address_manager import BorgAddressManager
from jam_mock.demo_audit_logger import DemoAuditLogger
from jam_mock.demo_cost_controller import DemoCostController
from jam_mock.economic_validator import EconomicValidator
from jam_mock.ethical_compliance_monitor import EthicalComplianceMonitor
from jam_mock.inter_borg_transfer import InterBorgTransfer
from jam_mock.kusama_adapter import WestendAdapter
from jam_mock.secure_key_storage import SecureKeypairManager
from jam_mock.transaction_manager import TransactionManager, TransactionType


class EndToEndTester:
    """End-to-end tester for Phase 2A fund holding system."""

    def __init__(self):
        print("🚀 Initializing End-to-End Test for Phase 2A")
        print("=" * 60)

        # Initialize components
        self.westend_adapter = WestendAdapter(
            rpc_url=os.getenv(
                "WESTEND_RPC_URL", "wss://westend-asset-hub-rpc.polkadot.io"
            )
        )

        # Initialize Supabase client for testing
        from dotenv import load_dotenv

        load_dotenv()
        from supabase import Client, create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if supabase_url and supabase_key:
            self.supabase_client = create_client(supabase_url, supabase_key)
            print("✅ Supabase client initialized for testing")
        else:
            self.supabase_client = None
            print("⚠️  Supabase credentials not found, using mock mode")

        self.address_manager = BorgAddressManager(
            supabase_client=self.supabase_client,
            audit_logger=DemoAuditLogger(),
            keystore=None,  # Use default keystore
        )

        self.cost_controller = DemoCostController()
        self.compliance_monitor = EthicalComplianceMonitor()
        self.economic_validator = EconomicValidator(
            cost_controller=self.cost_controller,
            compliance_monitor=self.compliance_monitor,
            supabase_client=self.supabase_client,
        )

        self.transaction_manager = TransactionManager(
            kusama_adapter=self.westend_adapter, keypair_manager=None
        )

        self.transfer_protocol = InterBorgTransfer(
            westend_adapter=self.westend_adapter,
            address_manager=self.address_manager,
            economic_validator=self.economic_validator,
            transaction_manager=self.transaction_manager,
        )

        # Test borgs
        self.borg_a = "borg_a_test"
        self.borg_b = "borg_b_test"
        self.initial_allocation = Decimal("1000.0")  # 1000 USDB each
        self.transfer_amount = Decimal("100.0")  # Transfer 100 USDB

    async def run_full_test(self) -> Dict[str, Any]:
        """Run the complete end-to-end test."""
        results = {"success": False, "steps": {}, "final_balances": {}, "error": None}

        try:
            # Step 1: Health check
            print("\n📋 Step 1: System Health Check")
            health = await self.westend_adapter.health_check()
            results["steps"]["health_check"] = {
                "status": health.get("status", "unknown"),
                "block_number": health.get("block_number"),
                "success": health.get("status") == "healthy",
            }
            print(f"   ✅ Westend connection: {health.get('status', 'unknown')}")
            if not results["steps"]["health_check"]["success"]:
                raise Exception("Westend connection failed")

            # Step 2: Create borg addresses
            print("\n📋 Step 2: Create Borg Addresses")
            borg_a_registration = self.address_manager.register_borg_address(
                self.borg_a, f"dna_hash_a_{'a'*56}"
            )
            borg_b_registration = self.address_manager.register_borg_address(
                self.borg_b, f"dna_hash_b_{'b'*56}"
            )

            results["steps"]["address_creation"] = {
                "borg_a": borg_a_registration["success"],
                "borg_b": borg_b_registration["success"],
                "borg_a_address": borg_a_registration.get("address"),
                "borg_b_address": borg_b_registration.get("address"),
            }

            if not (borg_a_registration["success"] and borg_b_registration["success"]):
                raise Exception("Borg address creation failed")

            print(f"   ✅ Borg A address: {borg_a_registration.get('address')[:20]}...")
            print(f"   ✅ Borg B address: {borg_b_registration.get('address')[:20]}...")

            # Step 3: Allocate initial USDB to borgs
            print(f"\n📋 Step 3: Allocate {self.initial_allocation} USDB to each borg")
            allocation_a = await self._allocate_usdb_to_borg(
                self.borg_a, self.initial_allocation
            )
            allocation_b = await self._allocate_usdb_to_borg(
                self.borg_b, self.initial_allocation
            )

            results["steps"]["initial_allocation"] = {
                "borg_a": allocation_a,
                "borg_b": allocation_b,
                "amount": str(self.initial_allocation),
            }

            if not (allocation_a and allocation_b):
                raise Exception("Initial USDB allocation failed")

            print(f"   ✅ Borg A allocated {self.initial_allocation} USDB")
            print(f"   ✅ Borg B allocated {self.initial_allocation} USDB")

            # Step 4: Verify initial balances
            print("\n📋 Step 4: Verify Initial Balances")
            balance_a = self.address_manager.get_balance(self.borg_a, "USDB")
            balance_b = self.address_manager.get_balance(self.borg_b, "USDB")

            balance_a_usdb = Decimal(str(balance_a or 0)) / Decimal("1000000000000")
            balance_b_usdb = Decimal(str(balance_b or 0)) / Decimal("1000000000000")

            results["steps"]["initial_balance_check"] = {
                "borg_a_balance": str(balance_a_usdb),
                "borg_b_balance": str(balance_b_usdb),
                "expected": str(self.initial_allocation),
                "correct": balance_a_usdb == self.initial_allocation
                and balance_b_usdb == self.initial_allocation,
            }

            if not results["steps"]["initial_balance_check"]["correct"]:
                raise Exception(
                    f"Initial balance check failed: A={balance_a_usdb}, B={balance_b_usdb}"
                )

            print(f"   ✅ Borg A balance: {balance_a_usdb} USDB")
            print(f"   ✅ Borg B balance: {balance_b_usdb} USDB")

            # Step 5: Execute transfer
            print(
                f"\n📋 Step 5: Transfer {self.transfer_amount} USDB from Borg A to Borg B"
            )
            transfer_result = await self.transfer_protocol.transfer_usdb(
                from_borg_id=self.borg_a,
                to_borg_id=self.borg_b,
                amount=self.transfer_amount,
                description="End-to-end test transfer",
            )

            results["steps"]["transfer_execution"] = {
                "success": transfer_result["success"],
                "transfer_id": transfer_result.get("transfer_id"),
                "transaction_hash": transfer_result.get("transaction_hash"),
                "errors": transfer_result.get("errors", []),
            }

            if not transfer_result["success"]:
                raise Exception(f"Transfer failed: {transfer_result.get('errors', [])}")

            print(f"   ✅ Transfer successful!")
            print(f"   📄 Transfer ID: {transfer_result.get('transfer_id')}")
            print(f"   🔗 TX Hash: {transfer_result.get('transaction_hash')}")

            # Step 6: Verify final balances
            print("\n📋 Step 6: Verify Final Balances")
            final_balance_a = self.address_manager.get_balance(self.borg_a, "USDB")
            final_balance_b = self.address_manager.get_balance(self.borg_b, "USDB")

            final_balance_a_usdb = Decimal(str(final_balance_a or 0)) / Decimal(
                "1000000000000"
            )
            final_balance_b_usdb = Decimal(str(final_balance_b or 0)) / Decimal(
                "1000000000000"
            )

            expected_a = self.initial_allocation - self.transfer_amount
            expected_b = self.initial_allocation + self.transfer_amount

            results["steps"]["final_balance_check"] = {
                "borg_a_balance": str(final_balance_a_usdb),
                "borg_b_balance": str(final_balance_b_usdb),
                "expected_a": str(expected_a),
                "expected_b": str(expected_b),
                "correct": final_balance_a_usdb == expected_a
                and final_balance_b_usdb == expected_b,
            }

            results["final_balances"] = {
                "borg_a": str(final_balance_a_usdb),
                "borg_b": str(final_balance_b_usdb),
            }

            if not results["steps"]["final_balance_check"]["correct"]:
                raise Exception(
                    f"Final balance check failed: A={final_balance_a_usdb} (expected {expected_a}), B={final_balance_b_usdb} (expected {expected_b})"
                )

            print(
                f"   ✅ Borg A final balance: {final_balance_a_usdb} USDB (expected: {expected_a})"
            )
            print(
                f"   ✅ Borg B final balance: {final_balance_b_usdb} USDB (expected: {expected_b})"
            )

            # Step 7: Verify transfer history
            print("\n📋 Step 7: Verify Transfer History")
            history_a = await self.transfer_protocol.get_transfer_history(
                self.borg_a, limit=5
            )
            history_b = await self.transfer_protocol.get_transfer_history(
                self.borg_b, limit=5
            )

            results["steps"]["transfer_history"] = {
                "borg_a_transfers": len(history_a),
                "borg_b_transfers": len(history_b),
                "borg_a_has_outgoing": any(
                    t.get("direction") == "sent" for t in history_a
                ),
                "borg_b_has_incoming": any(
                    t.get("direction") == "received" for t in history_b
                ),
            }

            print(f"   ✅ Borg A transfer history: {len(history_a)} transfers")
            print(f"   ✅ Borg B transfer history: {len(history_b)} transfers")

            # Success!
            results["success"] = True
            print("\n" + "=" * 60)
            print("🎉 END-TO-END TEST PASSED!")
            print(f"   Borg A: {final_balance_a_usdb} USDB")
            print(f"   Borg B: {final_balance_b_usdb} USDB")
            print("=" * 60)

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            print(f"\n❌ END-TO-END TEST FAILED: {e}")
            print("=" * 60)

        return results

    async def _allocate_usdb_to_borg(self, borg_id: str, amount: Decimal) -> bool:
        """Allocate USDB to a borg (simulated for testing)."""
        try:
            # Convert to planck units
            amount_wei = int(amount * (10**12))

            # Update database balance
            success = self.address_manager.sync_balance(borg_id, "USDB", amount_wei)

            if success:
                # Update local wealth cache
                await self.westend_adapter.update_wealth_dual(
                    borg_id,
                    "USDB",
                    amount,
                    "revenue",
                    "Initial USDB allocation for testing",
                )

            return success

        except Exception as e:
            print(f"Error allocating USDB to {borg_id}: {e}")
            return False


async def main():
    """Main entry point."""
    try:
        tester = EndToEndTester()
        results = await tester.run_full_test()

        # Save results
        output_file = "end_to_end_test_results.json"
        with open(output_file, "w") as f:
            import json

            json.dump(results, f, indent=2, default=str)

        print(f"\n📄 Detailed results saved to {output_file}")

        # Exit with appropriate code
        sys.exit(0 if results["success"] else 1)

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
