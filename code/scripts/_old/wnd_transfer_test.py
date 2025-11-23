#!/usr/bin/env python3
"""
WND Transfer Test Script
Tests live WND transfer from dispenser to borg tester address.
"""

import asyncio
import json
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.borg_address_manager import BorgAddressManager
from jam_mock.kusama_adapter import WestendAdapter
from security.secure_dispenser import SecureDispenser


async def main():
    """Test WND transfer from dispenser to borg tester."""
    print("💸 WND TRANSFER TEST")
    print("=" * 40)

    # Load borg tester details
    results_file = "borg_tester_borgTester_1762782723_results.json"
    if not os.path.exists(results_file):
        print(f"❌ Borg tester results file not found: {results_file}")
        return False

    with open(results_file, "r") as f:
        borg_data = json.load(f)

    borg_id = borg_data["borg_id"]
    borg_address = borg_data["address"]
    service_name = borg_data["service_name"]

    print(f"Borg ID: {borg_id}")
    print(f"Borg Address: {borg_address}")
    print(f"Service Name: {service_name}")
    print()

    # Verify borg keypair access
    print("🔑 Verifying borg keypair access...")
    import keyring

    private_key = keyring.get_password(service_name, "private_key")
    public_key = keyring.get_password(service_name, "public_key")
    stored_address = keyring.get_password(service_name, "address")

    if not all([private_key, public_key, stored_address]):
        print("❌ Borg keypair not accessible")
        return False

    if stored_address != borg_address:
        print("❌ Address mismatch in borg keyring")
        return False

    print("✅ Borg keypair verified")
    print(f"   Private key: {private_key[:32]}...")
    print(f"   Public key: {public_key[:32]}...")
    print(f"   Address: {stored_address}")
    print()

    # Initialize dispenser
    print("🔐 Initializing dispenser...")
    dispenser = SecureDispenser()
    if not dispenser.unlock_for_session():
        print("❌ Failed to unlock dispenser")
        return False

    dispenser_address = dispenser.unlocked_keypair.ss58_address
    print(f"✅ Dispenser unlocked: {dispenser_address}")
    print()

    # Check dispenser balance
    print("💰 Checking dispenser balance...")
    from jam_mock.kusama_adapter import WestendAdapter

    westend_adapter = WestendAdapter("wss://westend-rpc.polkadot.io")

    try:
        dispenser_balance = await westend_adapter.get_wnd_balance(dispenser_address)
        dispenser_balance_wnd = dispenser_balance / (10**12)
        print(
            f"✅ Dispenser balance: {dispenser_balance_wnd:.6f} WND ({dispenser_balance} planck)"
        )
    except Exception as e:
        print(f"❌ Failed to check dispenser balance: {e}")
        return False

    if dispenser_balance < 1 * (10**12):  # Less than 1 WND
        print("❌ Insufficient dispenser balance (< 1 WND)")
        return False
    print()

    # Check borg initial balance
    print("🔍 Checking borg initial balance...")
    try:
        borg_balance = await westend_adapter.get_wnd_balance(borg_address)
        borg_balance_wnd = borg_balance / (10**12)
        print(
            f"✅ Borg initial balance: {borg_balance_wnd:.6f} WND ({borg_balance} planck)"
        )
    except Exception as e:
        print(f"❌ Failed to check borg balance: {e}")
        return False
    print()

    # Perform transfer
    transfer_amount = 1.0  # 1 WND
    print(f"💸 Transferring {transfer_amount} WND from dispenser to borg...")

    try:
        # Use the WestendAdapter to perform the transfer
        westend_adapter.set_keypair(dispenser.unlocked_keypair)

        # Create balances.transfer extrinsic
        call = westend_adapter.substrate.compose_call(
            call_module="Balances",
            call_function="transfer_keep_alive",
            call_params={
                "dest": borg_address,
                "value": int(transfer_amount * (10**12)),  # Convert to planck
            },
        )

        # Create signed extrinsic
        extrinsic = westend_adapter.substrate.create_signed_extrinsic(
            call=call, keypair=dispenser.unlocked_keypair
        )

        # Submit and wait for inclusion
        receipt = westend_adapter.substrate.submit_extrinsic(
            extrinsic, wait_for_inclusion=True
        )

        if receipt.is_success:
            print("✅ Transfer successful!")
            print(f"   Transaction Hash: {receipt.extrinsic_hash}")
            print(f"   Block: {receipt.block_number}")
            print(f"   Amount: {transfer_amount} WND")
            transfer_result = {
                "success": True,
                "transaction_hash": receipt.extrinsic_hash,
                "block_number": receipt.block_number,
            }
        else:
            print(f"❌ Transfer failed: {receipt.error_message}")
            return False

    except Exception as e:
        print(f"❌ Transfer error: {e}")
        return False

    # Wait for confirmation
    print("⏳ Waiting for transaction confirmation...")
    await asyncio.sleep(10)  # Wait 10 seconds for confirmation

    # Check final balances
    print("🔍 Checking final balances...")
    try:
        final_dispenser_balance = await westend_adapter.get_wnd_balance(
            dispenser_address
        )
        final_dispenser_balance_wnd = final_dispenser_balance / (10**12)

        final_borg_balance = await westend_adapter.get_wnd_balance(borg_address)
        final_borg_balance_wnd = final_borg_balance / (10**12)

        print(f"✅ Final dispenser balance: {final_dispenser_balance_wnd:.6f} WND")
        print(f"✅ Final borg balance: {final_borg_balance_wnd:.6f} WND")
        print()

        # Validate transfer
        dispenser_decrease = dispenser_balance - final_dispenser_balance
        borg_increase = final_borg_balance - borg_balance

        expected_transfer = int(transfer_amount * (10**12))

        dispenser_ok = (
            abs(dispenser_decrease - expected_transfer) <= 1000000
        )  # Allow small fee difference
        borg_ok = abs(borg_increase - expected_transfer) <= 1000000

        if dispenser_ok and borg_ok:
            print("✅ TRANSFER VALIDATION PASSED!")
            print("   Balances correctly updated")
            print(f"   Dispenser decrease: {dispenser_decrease / (10 ** 12):.6f} WND")
            print(f"   Borg increase: {borg_increase / (10 ** 12):.6f} WND")
        else:
            print("⚠️ TRANSFER VALIDATION WARNING")
            print("   Balance changes don't match expected transfer")
            print(f"   Expected: {expected_transfer / (10 ** 12):.6f} WND")
            print(f"   Dispenser change: {dispenser_decrease / (10 ** 12):.6f} WND")
            print(f"   Borg change: {borg_increase / (10 ** 12):.6f} WND")

    except Exception as e:
        print(f"❌ Failed to check final balances: {e}")
        return False

    # Lock dispenser
    dispenser.lock_session()
    print("\\n🔒 Dispenser session locked")

    print("\\n🎉 WND TRANSFER TEST COMPLETE!")
    print("=" * 40)
    print("✅ Live WND transfer successful!")
    print(f"   From: {dispenser_address}")
    print(f"   To: {borg_address}")
    print(f"   Amount: {transfer_amount} WND")
    print("   🔐 All operations secured with macOS Keychain")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
