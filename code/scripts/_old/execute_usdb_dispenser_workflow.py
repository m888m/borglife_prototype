#!/usr/bin/env python3
"""
Execute USDB Dispenser Workflow

Complete workflow for USDB dispenser operations:
1. Mint 1M USDB to dispenser address
2. Verify dispenser USDB balance
3. Transfer 100k USDB to borg 1
4. Verify transaction and balances
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.borg_address_manager import BorgAddressManager
from security.secure_dispenser import SecureDispenser


async def main():
    """Main workflow execution."""
    print("🚀 Starting USDB Dispenser Workflow")
    print("=" * 50)

    workflow_results = {
        "minting": None,
        "dispenser_balance": None,
        "borg_address": None,
        "transfer": None,
        "final_balances": None,
        "overall_success": False,
    }

    try:
        # Initialize dispenser
        dispenser = SecureDispenser()

        # Unlock dispenser session
        print("\n🔐 Unlocking dispenser session...")
        if not dispenser.unlock_for_session():
            print("❌ Failed to unlock dispenser")
            return workflow_results

        dispenser_address = dispenser.unlocked_keypair.ss58_address
        print(f"   Dispenser Address: {dispenser_address}")

        # Step 1: Mint 1M USDB to dispenser
        print("\n🏭 STEP 1: Minting 1,000,000 USDB to dispenser")
        print("-" * 45)

        mint_amount = 1000000.0  # 1M USDB
        mint_result = await dispenser.mint_usdb_tokens(mint_amount)

        if not mint_result["success"]:
            print(f"❌ Minting failed: {mint_result['error']}")
            return workflow_results

        workflow_results["minting"] = mint_result
        print("✅ Minting successful!")
        print(f"   Transaction Hash: {mint_result['transaction_hash']}")
        print(f"   Block Number: {mint_result['block_number']}")

        # Step 2: Verify dispenser balance
        print("\n🔍 STEP 2: Verifying dispenser balance")
        print("-" * 40)

        dispenser_balance = await dispenser.get_usdb_balance(dispenser_address)
        dispenser_balance_usdb = dispenser_balance / (10**12)

        workflow_results["dispenser_balance"] = {
            "address": dispenser_address,
            "balance_usdb": dispenser_balance_usdb,
            "balance_planck": dispenser_balance,
        }

        print(f"   Dispenser Balance: {dispenser_balance_usdb:,.0f} USDB")

        if dispenser_balance < int(mint_amount * (10**12)):
            print("❌ Insufficient dispenser balance after minting")
            return workflow_results

        # Step 3: Get borg 1 address
        print("\n🔑 STEP 3: Retrieving borg 1 address")
        print("-" * 35)

        address_manager = BorgAddressManager()
        borg_1_id = "borg_1"
        borg_1_address = address_manager.get_address(borg_1_id)

        if not borg_1_address:
            print(f"❌ Could not find address for borg {borg_1_id}")
            return workflow_results

        workflow_results["borg_address"] = {
            "borg_id": borg_1_id,
            "address": borg_1_address,
        }

        print(f"   Borg 1 Address: {borg_1_address}")

        # Check borg 1 initial balance
        initial_borg_balance = await dispenser.get_usdb_balance(borg_1_address)
        initial_borg_balance_usdb = initial_borg_balance / (10**12)
        print(f"   Initial Borg 1 Balance: {initial_borg_balance_usdb:,.0f} USDB")

        # Step 4: Transfer 100k USDB to borg 1
        print("\n💸 STEP 4: Transferring 100,000 USDB to borg 1")
        print("-" * 45)

        transfer_amount = 100000.0  # 100k USDB
        transfer_result = await dispenser.transfer_usdb_to_borg(
            borg_1_address, borg_1_id, transfer_amount
        )

        if not transfer_result["success"]:
            print(f"❌ Transfer failed: {transfer_result['error']}")
            return workflow_results

        workflow_results["transfer"] = transfer_result
        print("✅ Transfer successful!")
        print(f"   Transaction Hash: {transfer_result['transaction_hash']}")
        print(f"   Block Number: {transfer_result['block_number']}")

        # Step 5: Verify final balances
        print("\n🔍 STEP 5: Verifying final balances")
        print("-" * 35)

        final_dispenser_balance = await dispenser.get_usdb_balance(dispenser_address)
        final_dispenser_balance_usdb = final_dispenser_balance / (10**12)

        final_borg_balance = await dispenser.get_usdb_balance(borg_1_address)
        final_borg_balance_usdb = final_borg_balance / (10**12)

        workflow_results["final_balances"] = {
            "dispenser": {
                "address": dispenser_address,
                "balance_usdb": final_dispenser_balance_usdb,
                "balance_planck": final_dispenser_balance,
            },
            "borg_1": {
                "borg_id": borg_1_id,
                "address": borg_1_address,
                "balance_usdb": final_borg_balance_usdb,
                "balance_planck": final_borg_balance,
            },
        }

        print(f"   Final Dispenser Balance: {final_dispenser_balance_usdb:,.0f} USDB")
        print(f"   Final Borg 1 Balance: {final_borg_balance_usdb:,.0f} USDB")

        # Validate balance changes
        expected_dispenser_balance = dispenser_balance_usdb - transfer_amount
        expected_borg_balance = initial_borg_balance_usdb + transfer_amount

        dispenser_balance_ok = (
            abs(final_dispenser_balance_usdb - expected_dispenser_balance) < 0.01
        )
        borg_balance_ok = abs(final_borg_balance_usdb - expected_borg_balance) < 0.01

        if dispenser_balance_ok and borg_balance_ok:
            workflow_results["overall_success"] = True
            print("✅ All balance validations passed!")
        else:
            print("❌ Balance validation failed")
            print(f"   Expected dispenser: {expected_dispenser_balance:,.0f} USDB")
            print(f"   Actual dispenser: {final_dispenser_balance_usdb:,.0f} USDB")
            print(f"   Expected borg: {expected_borg_balance:,.0f} USDB")
            print(f"   Actual borg: {final_borg_balance_usdb:,.0f} USDB")

        return workflow_results

    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        workflow_results["error"] = str(e)
        return workflow_results

    finally:
        # Always lock the session
        dispenser.lock_session()


if __name__ == "__main__":
    results = asyncio.run(main())

    # Print final summary
    print("\n" + "=" * 50)
    print("WORKFLOW EXECUTION SUMMARY")
    print("=" * 50)

    if results["overall_success"]:
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
        print("\n📋 EXECUTION DETAILS:")

        if results["minting"]:
            print(f"   Minting TX: {results['minting']['transaction_hash']}")
            print(f"   Minting Block: {results['minting']['block_number']}")

        if results["transfer"]:
            print(f"   Transfer TX: {results['transfer']['transaction_hash']}")
            print(f"   Transfer Block: {results['transfer']['block_number']}")

        if results["final_balances"]:
            dispenser = results["final_balances"]["dispenser"]
            borg = results["final_balances"]["borg_1"]
            print(f"   Final Dispenser Balance: {dispenser['balance_usdb']:,.0f} USDB")
            print(f"   Final Borg 1 Balance: {borg['balance_usdb']:,.0f} USDB")

    else:
        print("❌ WORKFLOW FAILED!")
        if "error" in results:
            print(f"   Error: {results['error']}")

    # Exit with appropriate code
    success = results.get("overall_success", False)
    sys.exit(0 if success else 1)
