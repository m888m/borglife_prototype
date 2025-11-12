#!/usr/bin/env python3
"""
Borg to Dispenser WND Transfer Test
Send 2 WND from a specific borg to dispenser address on live Westend network.
"""

import asyncio
import sys
import os
import json
from datetime import datetime
import keyring
from substrateinterface import Keypair

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.kusama_adapter import WestendAdapter


async def main():
    """Main transfer function."""
    print("🔄 BORG TO DISPENSER WND TRANSFER TEST")
    print("=" * 60)

    # Configuration
    borg_address = "5EeeSsZAzVzZjTnLA9yCV8pwsuQvbHDfYPZX5YcmitVFFA2c"
    dispenser_address = "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD"
    transfer_amount_wnd = 2.0
    service_name = "borglife-borg-borgTest1_1762870300"

    results = {
        'test_start_time': datetime.utcnow().isoformat(),
        'borg_address': borg_address,
        'dispenser_address': dispenser_address,
        'transfer_amount_wnd': transfer_amount_wnd,
        'service_name': service_name,
        'keypair_access': False,
        'balance_check': {},
        'transfer_result': {},
        'success': False,
        'error': None
    }

    try:
        print(f"🎯 Transferring {transfer_amount_wnd} WND from borg to dispenser")
        print(f"   From: {borg_address}")
        print(f"   To: {dispenser_address}")
        print(f"   Service: {service_name}")

        # Step 1: Retrieve keypair from macOS Keychain
        print("\n🔑 Step 1: Retrieving keypair from macOS Keychain...")

        private_key_hex = keyring.get_password(service_name, "private_key")
        public_key_hex = keyring.get_password(service_name, "public_key")
        stored_address = keyring.get_password(service_name, "address")

        if not private_key_hex:
            raise Exception(f"Private key not found in keyring for service {service_name}")

        if not public_key_hex:
            raise Exception(f"Public key not found in keyring for service {service_name}")

        if not stored_address:
            raise Exception(f"Address not found in keyring for service {service_name}")

        if stored_address != borg_address:
            raise Exception(f"Address mismatch: expected {borg_address}, got {stored_address}")

        print("✅ Keypair components retrieved from keyring")
        print(f"   Private key length: {len(private_key_hex)} chars")
        print(f"   Private key: {private_key_hex}")
        print(f"   Public key: {public_key_hex}")
        print(f"   Address: {stored_address}")

        # Step 2: Reconstruct keypair
        print("\n🔧 Step 2: Reconstructing keypair...")
        try:
            print(f"   Converting private key hex to bytes...")
            private_key_bytes = bytes.fromhex(private_key_hex)
            print(f"   Private key length: {len(private_key_bytes)} bytes")

            print(f"   Creating Keypair object...")
            keypair = Keypair(private_key=private_key_bytes, ss58_format=42)  # Westend format
            print(f"   Keypair created. SS58 address: {keypair.ss58_address}")

            # Verify reconstruction
            print(f"   Verifying address match...")
            if keypair.ss58_address != borg_address:
                print(f"   Expected: {borg_address}")
                print(f"   Got: {keypair.ss58_address}")
                raise Exception(f"Keypair reconstruction failed: address mismatch")

            print(f"   Verifying public key match...")
            reconstructed_pubkey = keypair.public_key.hex()
            if reconstructed_pubkey != public_key_hex:
                print(f"   Expected pubkey: {public_key_hex}")
                print(f"   Got pubkey: {reconstructed_pubkey}")
                raise Exception(f"Keypair reconstruction failed: public key mismatch")

            print("✅ Keypair reconstructed and verified")
            results['keypair_access'] = True

        except Exception as e:
            print(f"   Error details: {e}")
            raise Exception(f"Keypair reconstruction failed: {e}")

        # Step 3: Check balance
        print("\n💰 Step 3: Checking borg balance...")
        westend_adapter = WestendAdapter("https://westend.api.onfinality.io/public-ws")

        balance = await westend_adapter.get_wnd_balance(borg_address)
        if balance is None:
            print("⚠️  Balance query returned None, assuming sufficient balance")
            balance = 1000000000000  # Assume 1 WND for testing
        else:
            balance_wnd = balance / (10 ** 12)
            print(".6f")

        results['balance_check'] = {
            'balance_planck': balance,
            'balance_wnd': balance / (10 ** 12) if balance else None
        }

        # Step 4: Validate sufficient balance
        required_planck = int(transfer_amount_wnd * (10 ** 12))
        if balance < required_planck:
            raise Exception(f"Insufficient balance: {balance} < {required_planck} planck")

        print("✅ Sufficient balance confirmed")

        # Step 5: Execute transfer
        print(f"\n💸 Step 4: Executing transfer of {transfer_amount_wnd} WND...")

        westend_adapter.set_keypair(keypair)

        transfer_result = await westend_adapter.transfer_wnd(
            borg_address, dispenser_address, required_planck
        )

        results['transfer_result'] = transfer_result

        if not transfer_result.get('success'):
            error_msg = transfer_result.get('error', 'Unknown transfer error')
            raise Exception(f"Transfer failed: {error_msg}")

        print("✅ Transfer completed successfully!")
        print(f"   Transaction Hash: {transfer_result.get('transaction_hash')}")
        print(f"   Block Number: {transfer_result.get('block_number')}")

        results['success'] = True

        # Step 6: Verify final balance (optional)
        print("\n🔍 Step 5: Verifying transfer...")
        try:
            final_balance = await westend_adapter.get_wnd_balance(borg_address)
            if final_balance is not None:
                final_balance_wnd = final_balance / (10 ** 12)
                expected_balance = (balance - required_planck) / (10 ** 12)
                print(".6f")
                print(".6f")

                if abs(final_balance_wnd - expected_balance) < 0.0001:
                    print("✅ Balance verification PASSED")
                else:
                    print("⚠️  Balance verification WARNING - may include fees")
        except Exception as e:
            print(f"⚠️  Balance verification failed: {e}")

    except Exception as e:
        results['error'] = str(e)
        print(f"❌ Transfer failed: {e}")

    # Save results
    results['test_end_time'] = datetime.utcnow().isoformat()
    timestamp = int(datetime.utcnow().timestamp())
    results_file = f"borg_to_dispenser_transfer_results_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Results saved to: {results_file}")

    # Final report
    print("\n" + "=" * 60)
    if results['success']:
        print("🎉 BORG TO DISPENSER TRANSFER SUCCESSFUL!")
        print("✅ Keypair unlocked from macOS Keychain")
        print("✅ Live Westend transaction signed and submitted")
        print("✅ Transfer completed successfully")

        tx_hash = results['transfer_result'].get('transaction_hash')
        if tx_hash:
            print(f"🔗 Transaction: {tx_hash}")
            print(f"🌐 View on Westend Explorer: https://westend.subscan.io/extrinsic/{tx_hash}")

        print(f"📊 Amount: {transfer_amount_wnd} WND")
        print(f"📍 From: {borg_address}")
        print(f"📍 To: {dispenser_address}")

    else:
        print("❌ BORG TO DISPENSER TRANSFER FAILED!")
        if 'error' in results:
            print(f"   Error: {results['error']}")

    print("=" * 60)

    return results['success']


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)