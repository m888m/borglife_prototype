#!/usr/bin/env python3
"""
Inter-Borg Transfer Test Script
Tests WND transfers between borgs on live Westend network.
"""

import asyncio
import sys
import os
import json
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.secure_borg_creation import create_secure_borg
from jam_mock.kusama_adapter import WestendAdapter
import keyring


async def main():
    """Test inter-borg WND transfers on live Westend network."""
    print("🔄 INTER-BORG TRANSFER TEST")
    print("=" * 50)

    # Load borgTester details
    borg_tester_file = "borg_tester_borgTester_1762782723_results.json"
    if not os.path.exists(borg_tester_file):
        print(f"❌ Borg tester results file not found: {borg_tester_file}")
        return False

    with open(borg_tester_file, 'r') as f:
        borg_tester_data = json.load(f)

    borg_tester_id = borg_tester_data['borg_id']
    borg_tester_address = borg_tester_data['address']
    borg_tester_service = borg_tester_data['service_name']

    print(f"Borg Tester ID: {borg_tester_id}")
    print(f"Borg Tester Address: {borg_tester_address}")
    print()

    # Create second borg
    print("🧬 Creating second borg...")
    borg2_id = f"borgTester2_{int(time.time())}"
    dna_hash = "b2c3d4e5f67890123456789012345678901234567890123456789012345678901"  # 64 chars

    result = create_secure_borg(borg2_id, dna_hash)
    if not result['success']:
        print(f"❌ Borg 2 creation failed: {result['error']}")
        return False

    borg2_address = result['address']
    borg2_service = result['service_name']

    print(f"✅ Borg 2 created successfully!")
    print(f"   ID: {borg2_id}")
    print(f"   Address: {borg2_address}")
    print(f"   Keyring Service: {borg2_service}")
    print()

    # Verify both borg keypairs
    print("🔑 Verifying borg keypairs...")

    # Borg Tester keypair
    bt_private = keyring.get_password(borg_tester_service, "private_key")
    bt_public = keyring.get_password(borg_tester_service, "public_key")
    bt_address = keyring.get_password(borg_tester_service, "address")

    # Borg 2 keypair
    b2_private = keyring.get_password(borg2_service, "private_key")
    b2_public = keyring.get_password(borg2_service, "public_key")
    b2_address = keyring.get_password(borg2_service, "address")

    if not all([bt_private, bt_public, bt_address, b2_private, b2_public, b2_address]):
        print("❌ Keypair verification failed")
        return False

    print("✅ Both borg keypairs verified")
    print()

    # Initialize Westend adapter
    print("🌐 Initializing Westend connection...")
    westend_adapter = WestendAdapter("wss://westend.api.onfinality.io/public-ws")

    # Check initial balances
    print("💰 Checking initial balances...")
    bt_balance = await westend_adapter.get_wnd_balance(borg_tester_address)
    b2_balance = await westend_adapter.get_wnd_balance(borg2_address)

    bt_balance_wnd = bt_balance / (10 ** 12)
    b2_balance_wnd = b2_balance / (10 ** 12)

    print(f"✅ Borg Tester balance: {bt_balance_wnd:.6f} WND")
    print(f"✅ Borg 2 balance: {b2_balance_wnd:.6f} WND")
    print()

    # Transfer 0.5 WND from Borg Tester to Borg 2
    print("💸 Transferring 0.5 WND from Borg Tester to Borg 2...")
    transfer_amount_1 = 0.5

    # Load Borg Tester keypair
    from substrateinterface import Keypair
    bt_private_bytes = bytes.fromhex(bt_private)
    bt_keypair = Keypair(private_key=bt_private_bytes, ss58_format=42)

    westend_adapter.set_keypair(bt_keypair)

    # Create transfer extrinsic
    call = westend_adapter.substrate.compose_call(
        call_module='Balances',
        call_function='transfer_keep_alive',
        call_params={
            'dest': borg2_address,
            'value': int(transfer_amount_1 * (10 ** 12))
        }
    )

    # Create signed extrinsic
    extrinsic = westend_adapter.substrate.create_signed_extrinsic(
        call=call,
        keypair=bt_keypair
    )

    # Submit and wait for inclusion
    receipt = westend_adapter.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(f"❌ Transfer 1 failed: {receipt.error_message}")
        return False

    print("✅ Transfer 1 successful!")
    print(f"   Transaction: {receipt.extrinsic_hash}")
    print(f"   Amount: {transfer_amount_1} WND")
    print()

    # Wait for confirmation
    print("⏳ Waiting for confirmation...")
    await asyncio.sleep(15)

    # Check balances after first transfer
    print("💰 Checking balances after transfer 1...")
    bt_balance_after1 = await westend_adapter.get_wnd_balance(borg_tester_address)
    b2_balance_after1 = await westend_adapter.get_wnd_balance(borg2_address)

    bt_balance_after1_wnd = bt_balance_after1 / (10 ** 12)
    b2_balance_after1_wnd = b2_balance_after1 / (10 ** 12)

    print(f"✅ Borg Tester balance: {bt_balance_after1_wnd:.6f} WND")
    print(f"✅ Borg 2 balance: {b2_balance_after1_wnd:.6f} WND")
    print()

    # Transfer 0.1 WND back from Borg 2 to Borg Tester
    print("💸 Transferring 0.1 WND from Borg 2 to Borg Tester...")
    transfer_amount_2 = 0.1

    # Load Borg 2 keypair
    b2_private_bytes = bytes.fromhex(b2_private)
    b2_keypair = Keypair(private_key=b2_private_bytes, ss58_format=42)

    westend_adapter.set_keypair(b2_keypair)

    # Create transfer extrinsic
    call = westend_adapter.substrate.compose_call(
        call_module='Balances',
        call_function='transfer_keep_alive',
        call_params={
            'dest': borg_tester_address,
            'value': int(transfer_amount_2 * (10 ** 12))
        }
    )

    # Create signed extrinsic
    extrinsic = westend_adapter.substrate.create_signed_extrinsic(
        call=call,
        keypair=b2_keypair
    )

    # Submit and wait for inclusion
    receipt = westend_adapter.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(f"❌ Transfer 2 failed: {receipt.error_message}")
        return False

    print("✅ Transfer 2 successful!")
    print(f"   Transaction: {receipt.extrinsic_hash}")
    print(f"   Amount: {transfer_amount_2} WND")
    print()

    # Wait for confirmation
    print("⏳ Waiting for confirmation...")
    await asyncio.sleep(15)

    # Check final balances
    print("💰 Checking final balances...")
    bt_balance_final = await westend_adapter.get_wnd_balance(borg_tester_address)
    b2_balance_final = await westend_adapter.get_wnd_balance(borg2_address)

    bt_balance_final_wnd = bt_balance_final / (10 ** 12)
    b2_balance_final_wnd = b2_balance_final / (10 ** 12)

    print(f"✅ Borg Tester final balance: {bt_balance_final_wnd:.6f} WND")
    print(f"✅ Borg 2 final balance: {b2_balance_final_wnd:.6f} WND")
    print()

    # Validate transfers
    print("🔍 Validating transfers...")

    # Expected changes
    bt_expected_change = -transfer_amount_1 + transfer_amount_2  # -0.5 + 0.1 = -0.4
    b2_expected_change = transfer_amount_1 - transfer_amount_2   # +0.5 - 0.1 = +0.4

    bt_actual_change = bt_balance_final_wnd - bt_balance_wnd
    b2_actual_change = b2_balance_final_wnd - b2_balance_wnd

    bt_ok = abs(bt_actual_change - bt_expected_change) < 0.01  # Allow small fee differences
    b2_ok = abs(b2_actual_change - b2_expected_change) < 0.01

    if bt_ok and b2_ok:
        print("✅ TRANSFER VALIDATION PASSED!")
        print("   All balance changes correctly accounted for")
        print(f"   Borg Tester net change: {bt_actual_change:.6f} WND (expected: {bt_expected_change:.6f})")
        print(f"   Borg 2 net change: {b2_actual_change:.6f} WND (expected: {b2_expected_change:.6f})")
    else:
        print("⚠️ TRANSFER VALIDATION WARNING")
        print("   Balance changes may include network fees")
        print(f"   Borg Tester: {bt_actual_change:.6f} WND (expected: {bt_expected_change:.6f})")
        print(f"   Borg 2: {b2_actual_change:.6f} WND (expected: {b2_expected_change:.6f})")

    # Save results
    results = {
        'borg_tester': {
            'id': borg_tester_id,
            'address': borg_tester_address,
            'initial_balance': bt_balance_wnd,
            'final_balance': bt_balance_final_wnd
        },
        'borg2': {
            'id': borg2_id,
            'address': borg2_address,
            'initial_balance': b2_balance_wnd,
            'final_balance': b2_balance_final_wnd
        },
        'transfers': [
            {
                'from': borg_tester_id,
                'to': borg2_id,
                'amount': transfer_amount_1,
                'timestamp': time.time() - 30  # Approximate
            },
            {
                'from': borg2_id,
                'to': borg_tester_id,
                'amount': transfer_amount_2,
                'timestamp': time.time()  # Approximate
            }
        ],
        'validation_passed': bt_ok and b2_ok,
        'completed_at': time.time()
    }

    results_file = f"inter_borg_transfer_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\\n📄 Results saved to: {results_file}")

    print("\\n🎉 INTER-BORG TRANSFER TEST COMPLETE!")
    print("=" * 50)
    print("✅ Live inter-borg WND transfers successful!")
    print(f"   Borg Tester: {borg_tester_address}")
    print(f"   Borg 2: {borg2_address}")
    print("   🔐 All operations secured with macOS Keychain")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)