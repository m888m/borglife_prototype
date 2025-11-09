#!/usr/bin/env python3
"""
Verify USDB Balances Script

Verifies USDB balances on Westend Asset Hub for dispenser and borg addresses.
Includes transaction hash verification and on-chain confirmation.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from security.secure_dispenser import SecureDispenser


async def verify_usdb_balance(address: str, label: str, dispenser: SecureDispenser) -> dict:
    """Verify USDB balance for a specific address."""
    print(f"\n🔍 Checking {label} balance...")

    try:
        balance_planck = await dispenser.get_usdb_balance(address)
        balance_usdb = balance_planck / (10 ** 12)

        print(f"   Address: {address}")
        print(f"   Balance: {balance_usdb:,.0f} USDB ({balance_planck:,} planck)")

        return {
            'address': address,
            'label': label,
            'balance_usdb': balance_usdb,
            'balance_planck': balance_planck,
            'success': True
        }

    except Exception as e:
        print(f"   Error: {e}")
        return {
            'address': address,
            'label': label,
            'error': str(e),
            'success': False
        }


async def verify_transaction_on_chain(tx_hash: str, dispenser: SecureDispenser) -> dict:
    """Verify transaction on-chain and get confirmation details."""
    print(f"\n🔗 Verifying transaction on-chain...")
    print(f"   Transaction Hash: {tx_hash}")

    try:
        # Get transaction details from Asset Hub
        tx_details = await dispenser.asset_hub_adapter.get_transaction_by_hash(tx_hash)

        if tx_details:
            print(f"   Block Number: {tx_details.get('block_number', 'N/A')}")
            print(f"   Block Hash: {tx_details.get('block_hash', 'N/A')}")
            print(f"   Success: {tx_details.get('success', False)}")

            if tx_details.get('borg_data'):
                borg_data = tx_details['borg_data']
                print(f"   Borg Data: {borg_data}")

            return {
                'transaction_hash': tx_hash,
                'block_number': tx_details.get('block_number'),
                'block_hash': tx_details.get('block_hash'),
                'success': tx_details.get('success', False),
                'borg_data': tx_details.get('borg_data'),
                'verified': True
            }
        else:
            print("   Transaction not found on-chain")
            return {
                'transaction_hash': tx_hash,
                'verified': False,
                'error': 'Transaction not found'
            }

    except Exception as e:
        print(f"   Error verifying transaction: {e}")
        return {
            'transaction_hash': tx_hash,
            'verified': False,
            'error': str(e)
        }


async def main():
    """Main execution function."""
    print("🔍 Starting USDB Balance Verification")
    print("=" * 50)

    verification_results = {
        'balances': [],
        'transactions': [],
        'overall_success': False
    }

    try:
        # Initialize dispenser
        dispenser = SecureDispenser()

        # Unlock dispenser session (read-only operation)
        print("\n🔐 Unlocking dispenser session...")
        if not dispenser.unlock_for_session():
            print("❌ Failed to unlock dispenser")
            return verification_results

        dispenser_address = dispenser.unlocked_keypair.ss58_address
        print(f"   Dispenser Address: {dispenser_address}")

        # Verify dispenser balance
        dispenser_balance = await verify_usdb_balance(
            dispenser_address, "Dispenser", dispenser
        )
        verification_results['balances'].append(dispenser_balance)

        # Get borg 1 address from secure storage
        print("\n🔑 Retrieving borg 1 address from secure storage...")

        # Import borg address manager to get borg addresses
        from jam_mock.borg_address_manager import BorgAddressManager
        address_manager = BorgAddressManager()

        borg_1_id = "borg_1"  # Standard borg ID
        borg_1_address = address_manager.get_address(borg_1_id)

        if not borg_1_address:
            print(f"❌ Could not find address for borg {borg_1_id}")
            return verification_results

        print(f"   Borg 1 Address: {borg_1_address}")

        # Verify borg 1 balance
        borg_balance = await verify_usdb_balance(
            borg_1_address, f"Borg {borg_1_id}", dispenser
        )
        verification_results['balances'].append(borg_balance)

        # Check if we have transaction hashes to verify (from command line args or recent operations)
        if len(sys.argv) > 1:
            tx_hash = sys.argv[1]
            print(f"\n📋 Verifying provided transaction hash: {tx_hash}")
            tx_verification = await verify_transaction_on_chain(tx_hash, dispenser)
            verification_results['transactions'].append(tx_verification)

        # Summary
        print("\n📊 VERIFICATION SUMMARY")
        print("=" * 30)

        successful_balances = sum(1 for b in verification_results['balances'] if b['success'])
        total_balances = len(verification_results['balances'])

        print(f"Balance Checks: {successful_balances}/{total_balances} successful")

        successful_txs = sum(1 for t in verification_results['transactions'] if t.get('verified', False))
        total_txs = len(verification_results['transactions'])

        if total_txs > 0:
            print(f"Transaction Verifications: {successful_txs}/{total_txs} successful")

        verification_results['overall_success'] = (successful_balances == total_balances and
                                                 (total_txs == 0 or successful_txs == total_txs))

        if verification_results['overall_success']:
            print("✅ All verifications successful!")
        else:
            print("⚠️  Some verifications failed - check details above")

        return verification_results

    except Exception as e:
        print(f"❌ Script execution failed: {e}")
        verification_results['error'] = str(e)
        return verification_results

    finally:
        # Always lock the session
        dispenser.lock_session()


if __name__ == "__main__":
    results = asyncio.run(main())

    # Exit with appropriate code
    success = results.get('overall_success', False)
    sys.exit(0 if success else 1)