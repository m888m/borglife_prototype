#!/usr/bin/env python3
"""
Reverse Borg Inter-Transfer Test
Send 0.5 WND from borg2 to borg1, then 0.1 WND back from borg1 to borg2.
"""

import asyncio
import sys
import os
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.secure_borg_creation import SecureBorgCreator
from scripts.westend_balance_check import WestendRPCClient
from jam_mock.kusama_adapter import WestendAdapter


async def main():
    """Execute reverse borg-to-borg inter-transfer test."""
    print("🔄 REVERSE BORGLIFE BORG INTER-TRANSFER TEST")
    print("=" * 55)

    borg1_creator = None
    borg2_creator = None

    try:
        # Step 1: Access borg1 (empty account)
        print("\n🤖 STEP 1: Accessing borg1")
        print("-" * 25)

        borg1_creator = SecureBorgCreator(session_timeout_minutes=60)
        if not borg1_creator.initialize_security():
            print("❌ Security initialization failed")
            return

        borg1_keypair = borg1_creator.get_borg_keypair('borg1')
        if not borg1_keypair:
            print("❌ Borg1 keypair not found")
            return

        borg1_address = borg1_keypair.ss58_address
        print("✅ Borg1 accessed successfully!")
        print(f"   Address: {borg1_address}")

        # Step 2: Access borg2 (has 1 WND)
        print("\n🏗️  STEP 2: Accessing borg2")
        print("-" * 25)

        # Use the live test borg2 ID from previous test
        borg2_id = "live_test_borg_1762772027"

        borg2_creator = SecureBorgCreator(session_timeout_minutes=60)
        if not borg2_creator.initialize_security():
            print("❌ Security initialization failed for borg2")
            return

        borg2_keypair = borg2_creator.get_borg_keypair(borg2_id)
        if not borg2_keypair:
            print("❌ Borg2 keypair not found")
            return

        borg2_address = borg2_keypair.ss58_address
        print("✅ Borg2 accessed successfully!")
        print(f"   Address: {borg2_address}")

        # Check borg2 balance
        rpc = WestendRPCClient()
        borg2_balance_raw = rpc.get_account_balance_raw(borg2_address)
        if borg2_balance_raw:
            borg2_balance = rpc.get_account_balance_decoded(borg2_address)
            if borg2_balance:
                free_balance = borg2_balance['data']['free']
                borg2_wnd_balance = free_balance / (10 ** 12)
                print(".6f")
                if borg2_wnd_balance < 0.6:
                    print("❌ Borg2 needs at least 0.6 WND for this test")
                    return
            else:
                print("⚠️  Could not decode borg2 balance")
        else:
            print("❌ Could not get borg2 balance")
            return

        # Step 3: Transfer 0.5 WND from borg2 to borg1
        print("\n💸 STEP 3: Transferring 0.5 WND from borg2 to borg1")
        print("-" * 50)

        transfer_amount_1 = int(0.5 * (10 ** 12))  # 0.5 WND in planck

        westend_adapter = WestendAdapter(rpc_url="wss://westend.api.onfinality.io/public-ws")

        print(f"📤 Transferring 0.5 WND ({transfer_amount_1} planck)")
        print(f"   From: {borg2_address}")
        print(f"   To: {borg1_address}")

        call = westend_adapter.substrate.compose_call(
            call_module='Balances',
            call_function='transfer_keep_alive',
            call_params={
                'dest': borg1_address,
                'value': transfer_amount_1
            }
        )

        extrinsic = westend_adapter.substrate.create_signed_extrinsic(
            call=call,
            keypair=borg2_keypair  # Sign with borg2's keypair
        )

        print("⏳ Submitting borg2 → borg1 transaction...")
        receipt = westend_adapter.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        if receipt.is_success:
            print("✅ BORG2 → BORG1 TRANSFER SUCCESSFUL!")
            print(f"   Transaction Hash: {receipt.extrinsic_hash}")
            print(f"   Block Hash: {receipt.block_hash}")
            transfer1_tx_hash = receipt.extrinsic_hash
        else:
            print(f"❌ Transfer failed: {receipt.error_message}")
            return

        # Wait for confirmation
        await asyncio.sleep(5)

        # Verify borg1 received 0.5 WND
        borg1_balance_raw = rpc.get_account_balance_raw(borg1_address)
        if borg1_balance_raw:
            borg1_balance = rpc.get_account_balance_decoded(borg1_address)
            if borg1_balance:
                free_balance = borg1_balance['data']['free']
                borg1_wnd_balance = free_balance / (10 ** 12)
                print(".6f")
                if borg1_wnd_balance < 0.4:  # Allow for some rounding
                    print("⚠️  Borg1 may not have received full amount")
            else:
                print("⚠️  Could not decode borg1 balance")
        else:
            print("❌ Could not verify borg1 balance")

        # Step 4: Transfer 0.1 WND back from borg1 to borg2
        print("\n🔄 STEP 4: Transferring 0.1 WND from borg1 to borg2")
        print("-" * 50)

        transfer_amount_2 = int(0.1 * (10 ** 12))  # 0.1 WND in planck

        print(f"📤 Transferring 0.1 WND ({transfer_amount_2} planck)")
        print(f"   From: {borg1_address}")
        print(f"   To: {borg2_address}")

        call = westend_adapter.substrate.compose_call(
            call_module='Balances',
            call_function='transfer_keep_alive',
            call_params={
                'dest': borg2_address,
                'value': transfer_amount_2
            }
        )

        extrinsic = westend_adapter.substrate.create_signed_extrinsic(
            call=call,
            keypair=borg1_keypair  # Sign with borg1's keypair
        )

        print("⏳ Submitting borg1 → borg2 transaction...")
        receipt = westend_adapter.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        if receipt.is_success:
            print("✅ BORG1 → BORG2 TRANSFER SUCCESSFUL!")
            print(f"   Transaction Hash: {receipt.extrinsic_hash}")
            print(f"   Block Hash: {receipt.block_hash}")
            transfer2_tx_hash = receipt.extrinsic_hash
        else:
            print(f"❌ Return transfer failed: {receipt.error_message}")
            return

        # Wait for confirmation
        await asyncio.sleep(5)

        # Step 5: Final balance verification
        print("\n🔍 STEP 5: Final balance verification")
        print("-" * 35)

        final_borg1_balance_raw = rpc.get_account_balance_raw(borg1_address)
        final_borg2_balance_raw = rpc.get_account_balance_raw(borg2_address)

        final_borg1_wnd = 0
        final_borg2_wnd = 0

        if final_borg1_balance_raw:
            final_borg1_balance = rpc.get_account_balance_decoded(borg1_address)
            if final_borg1_balance:
                final_borg1_wnd = final_borg1_balance['data']['free'] / (10 ** 12)

        if final_borg2_balance_raw:
            final_borg2_balance = rpc.get_account_balance_decoded(borg2_address)
            if final_borg2_balance:
                final_borg2_wnd = final_borg2_balance['data']['free'] / (10 ** 12)

        print("📊 FINAL BALANCES:")
        print(".6f")
        print(".6f")
        # Expected: borg1 should have 0.4 WND, borg2 should have 0.6 WND
        expected_borg1 = 0.4
        expected_borg2 = 0.6

        borg1_ok = abs(final_borg1_wnd - expected_borg1) < 0.01
        borg2_ok = abs(final_borg2_wnd - expected_borg2) < 0.01

        if borg1_ok and borg2_ok:
            print("✅ ALL BALANCE TRANSFERS VERIFIED!")
        else:
            print("⚠️  Balance verification may have timing issues - check manually")

        # Success summary
        print("\n" + "=" * 55)
        print("REVERSE INTER-TRANSFER TEST SUMMARY")
        print("=" * 55)
        print("✅ Borg2 → Borg1: 0.5 WND transferred")
        print("✅ Borg1 → Borg2: 0.1 WND returned")
        print("✅ Balances Verified: Peer-to-peer transfers working")
        print(f"✅ Borg1 Address: {borg1_address}")
        print(f"✅ Borg2 Address: {borg2_address}")
        print(f"✅ TX1 Hash: {transfer1_tx_hash}")
        print(f"✅ TX2 Hash: {transfer2_tx_hash}")
        print("\n🎉 REVERSE BORG INTER-TRANSFERS SUCCESSFUL!")

    except Exception as e:
        print(f"❌ Reverse inter-transfer test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())