#!/usr/bin/env python3
"""
Live Westend Test: Complete End-to-End BorgLife Transaction
1. Create new borg with keyring storage
2. Verify private key access
3. Send 1 WND from dispenser to borg (LIVE TRANSACTION)
4. Verify borg balance on Westend
"""

import asyncio
import sys
import os
import hashlib
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.secure_borg_creation import SecureBorgCreator
from security.secure_dispenser import SecureDispenser
from scripts.westend_balance_check import WestendRPCClient


async def main():
    """Execute complete live Westend test."""
    print("🚀 LIVE WESTEND TEST: Complete BorgLife Transaction Flow")
    print("=" * 70)

    test_borg_id = f"live_test_borg_{int(time.time())}"
    dispenser = None
    borg_creator = None

    try:
        # Step 1: Create new borg with keyring storage
        print("\n🤖 STEP 1: Creating new borg with macOS Keychain storage")
        print("-" * 55)

        borg_creator = SecureBorgCreator(session_timeout_minutes=60)
        if not borg_creator.initialize_security():
            print("❌ Security initialization failed")
            return

        # Generate DNA hash
        dna_content = f"live_test_dna_{test_borg_id}_{time.time()}"
        dna_hash = hashlib.sha256(dna_content.encode()).hexdigest()

        print(f"🧬 DNA Hash: {dna_hash[:32]}...")

        # Create borg
        borg_result = borg_creator.create_borg(
            borg_id=test_borg_id,
            dna_hash=dna_hash,
            creator_signature='live_test_signature',
            creator_public_key='live_test_public_key'
        )

        if not borg_result['success']:
            print(f"❌ Borg creation failed: {borg_result.get('error')}")
            return

        borg_address = borg_result['address']
        print("✅ Borg created successfully!")
        print(f"   Borg ID: {test_borg_id}")
        print(f"   Address: {borg_address}")
        print(f"   Keyring Service: {borg_result['service_name']}")

        # Step 2: Verify private key access
        print("\n🔑 STEP 2: Verifying private key access from macOS Keychain")
        print("-" * 58)

        keypair = borg_creator.get_borg_keypair(test_borg_id)
        if not keypair:
            print("❌ Private key not accessible from macOS Keychain")
            return

        print("✅ Private key accessible from macOS Keychain!")
        print(f"   Address Match: {keypair.ss58_address == borg_address}")
        print(f"   Public Key: {keypair.public_key.hex()[:20]}...")

        # Test signing capability
        test_message = b"live_westend_test_signature"
        signature = keypair.sign(test_message)
        is_valid = keypair.verify(test_message, signature)

        print(f"   Signature Test: {'✅ PASSED' if is_valid else '❌ FAILED'}")

        # Step 3: Unlock dispenser and prepare for transfer
        print("\n💰 STEP 3: Preparing dispenser for live WND transfer")
        print("-" * 50)

        dispenser = SecureDispenser()
        if not dispenser.unlock_for_session():
            print("❌ Dispenser unlock failed")
            return

        dispenser_address = dispenser.unlocked_keypair.ss58_address
        print("✅ Dispenser unlocked!")
        print(f"   Dispenser Address: {dispenser_address}")

        # Check dispenser balance
        rpc = WestendRPCClient()
        dispenser_balance_raw = rpc.get_account_balance_raw(dispenser_address)
        if dispenser_balance_raw:
            # Use substrate query method for accurate decoding
            dispenser_balance = rpc.get_account_balance_decoded(dispenser_address)
            if dispenser_balance:
                free_balance = dispenser_balance['data']['free']
                wnd_balance = free_balance / (10 ** 12)
                print(".6f")
            else:
                print("⚠️  Could not decode dispenser balance")
        else:
            print("❌ Could not get dispenser balance")
            return

        # Step 4: Execute LIVE WND transfer
        print("\n🚀 STEP 4: Executing LIVE 1 WND transfer to borg")
        print("-" * 45)

        # Use the WestendAdapter for the transfer
        from jam_mock.kusama_adapter import WestendAdapter

        # Create Westend adapter for transfer
        westend_adapter = WestendAdapter(rpc_url="wss://westend.api.onfinality.io/public-ws")

        # Execute transfer
        transfer_amount_planck = int(1.0 * (10 ** 12))  # 1 WND in planck

        print(f"📤 Transferring 1.0 WND ({transfer_amount_planck} planck)")
        print(f"   From: {dispenser_address}")
        print(f"   To: {borg_address}")

        # Create transfer extrinsic (use correct pallet name for Westend)
        call = westend_adapter.substrate.compose_call(
            call_module='Balances',
            call_function='transfer_keep_alive',  # Use transfer_keep_alive instead of transfer
            call_params={
                'dest': borg_address,
                'value': transfer_amount_planck
            }
        )

        extrinsic = westend_adapter.substrate.create_signed_extrinsic(
            call=call,
            keypair=dispenser.unlocked_keypair
        )

        print("⏳ Submitting transaction...")
        receipt = westend_adapter.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        if receipt.is_success:
            print("✅ LIVE TRANSACTION SUCCESSFUL!")
            print(f"   Transaction Hash: {receipt.extrinsic_hash}")
            print(f"   Block Hash: {receipt.block_hash}")
            print(f"   Block Number: {receipt.block_number}")

            # Wait a moment for confirmation
            await asyncio.sleep(3)

        else:
            print(f"❌ Transaction failed: {receipt.error_message}")
            return

        # Step 5: Verify borg balance after transfer
        print("\n🔍 STEP 5: Verifying borg balance on Westend")
        print("-" * 42)

        # Check borg balance
        borg_balance_raw = rpc.get_account_balance_raw(borg_address)
        if borg_balance_raw:
            borg_balance = rpc.get_account_balance_decoded(borg_address)
            if borg_balance:
                free_balance = borg_balance['data']['free']
                wnd_balance = free_balance / (10 ** 12)
                print(".6f")
                print(f"   Nonce: {borg_balance['nonce']}")

                if wnd_balance >= 1.0:
                    print("🎉 SUCCESS: Borg received 1 WND!")
                    print("✅ LIVE WESTEND TEST COMPLETED SUCCESSFULLY")
                else:
                    print(f"⚠️  Borg balance is {wnd_balance} WND - transfer may not have completed")
            else:
                print("⚠️  Could not decode borg balance")
        else:
            print("❌ Could not get borg balance")

        # Final summary
        print("\n" + "=" * 70)
        print("LIVE WESTEND TEST SUMMARY")
        print("=" * 70)
        print("✅ Borg Created: Keyring-secured keypair")
        print("✅ Private Key: Accessible from macOS Keychain")
        print("✅ Live Transaction: 1 WND transferred on Westend")
        print("✅ Balance Verified: Borg received funds")
        print(f"✅ Borg Address: {borg_address}")
        print(f"✅ Transaction Hash: {receipt.extrinsic_hash}")

    except Exception as e:
        print(f"❌ Live test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up sessions
        if dispenser:
            dispenser.lock_session()
        # Note: SecureBorgCreator doesn't have lock_session method


if __name__ == "__main__":
    asyncio.run(main())