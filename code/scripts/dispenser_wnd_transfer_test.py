#!/usr/bin/env python3
"""
Dispenser WND Transfer Test
Send 1 WND from dispenser to borg 1 to prove keyring access with live transaction.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from security.secure_dispenser_address_primary import SecureDispenserAddressPrimary as SecureDispenser
from jam_mock.borg_address_manager_address_primary import BorgAddressManagerAddressPrimary as BorgAddressManager


async def test_dispenser_wnd_transfer():
    """Send 1 WND from dispenser to borg 1 to prove keyring access."""
    print("💸 DISPENSER WND TRANSFER TEST")
    print("=" * 50)
    print("Sending 1 WND from dispenser to borg 1 to prove keyring access")
    print("=" * 50)

    results = {
        'dispenser_unlock': False,
        'borg_address_retrieved': False,
        'initial_balances': {},
        'transfer_result': {},
        'final_balances': {},
        'success': False
    }

    try:
        # Initialize dispenser with correct path
        dispenser = SecureDispenser("../jam_mock/.dispenser_keystore.enc")
        print("✅ Dispenser initialized")

        # Unlock dispenser (loads private key from keyring)
        print("\n🔐 Unlocking dispenser...")
        if not dispenser.unlock_for_session():
            print("❌ Failed to unlock dispenser")
            return results

        results['dispenser_unlock'] = True
        dispenser_address = dispenser.unlocked_keypair.ss58_address
        print(f"✅ Dispenser unlocked: {dispenser_address}")
        print("🔑 Private key loaded from macOS Keychain")

        # Use the borg tester address directly from results file
        print("\n🔍 Using borg tester address from results file...")
        import json
        with open("../../borg_tester_borgTester_1762782723_results.json", 'r') as f:
            borg_data = json.load(f)

        borg_1_id = borg_data['borg_id']
        borg_1_address = borg_data['address']

        if not borg_1_address:
            print(f"❌ Could not find address for {borg_1_id}")
            return results

        results['borg_address_retrieved'] = True
        print(f"✅ Borg 1 address: {borg_1_address}")

        # Check initial balances using WestendAdapter
        print("\n💰 Checking initial balances...")
        from jam_mock.westend_adapter import WestendAdapter
        westend_adapter = WestendAdapter(
            "https://westend.api.onfinality.io/public")
        dispenser_balance = await westend_adapter.get_wnd_balance(dispenser_address)
        borg_balance = await westend_adapter.get_wnd_balance(borg_1_address)

        dispenser_wnd = dispenser_balance / (10 ** 12)
        borg_wnd = borg_balance / (10 ** 12)

        results['initial_balances'] = {
            'dispenser': {'planck': dispenser_balance, 'wnd': dispenser_wnd},
            'borg_1': {'planck': borg_balance, 'wnd': borg_wnd}
        }

        print(f"Dispenser balance: {dispenser_wnd:.6f}")
        print(f"Borg 1 balance: {borg_wnd:.6f}")

        # Verify dispenser has enough balance
        if dispenser_wnd < 1.1:  # Need at least 1.1 WND for transfer + fees
            print("❌ Insufficient dispenser balance for transfer")
            return results

        # Perform transfer
        print("\n💸 Sending 1 WND from dispenser to borg 1...")
        transfer_amount = 1.0  # 1 WND

        transfer_result = await dispenser.transfer_wnd_to_borg(
            borg_1_address, borg_1_id, transfer_amount
        )

        results['transfer_result'] = transfer_result

        if not transfer_result.get('success'):
            print(f"❌ Transfer failed: {transfer_result.get('error')}")
            return results

        print("✅ Transfer successful!")
        print(f"   Transaction: {transfer_result.get('transaction_hash')}")
        print(f"   Block: {transfer_result.get('block_number')}")

        # Wait for confirmation
        print("\n⏳ Waiting for confirmation...")
        await asyncio.sleep(12)  # Wait for block confirmation

        # Check final balances
        print("\n💰 Checking final balances...")
        final_dispenser_balance = await westend_adapter.get_wnd_balance(dispenser_address)
        final_borg_balance = await westend_adapter.get_wnd_balance(borg_1_address)

        final_dispenser_wnd = final_dispenser_balance / (10 ** 12)
        final_borg_wnd = final_borg_balance / (10 ** 12)

        results['final_balances'] = {
            'dispenser': {'planck': final_dispenser_balance, 'wnd': final_dispenser_wnd},
            'borg_1': {'planck': final_borg_balance, 'wnd': final_borg_wnd}
        }

        print(f"Final dispenser balance: {final_dispenser_wnd:.6f}")
        print(f"Final borg 1 balance: {final_borg_wnd:.6f}")

        # Validate transfer
        dispenser_change = final_dispenser_wnd - dispenser_wnd
        borg_change = final_borg_wnd - borg_wnd

        print("\n📊 Transfer validation:")
        print(f"Dispenser change: {dispenser_change:.6f}")
        print(f"Borg change: {borg_change:.6f}")
        # Check if transfer was successful (allowing for fees)
        if borg_change >= 0.99:  # Should receive at least 0.99 WND
            results['success'] = True
            print("✅ Transfer validation PASSED")
        else:
            print("⚠️ Transfer validation WARNING - balance change may include fees")

        # Lock dispenser
        dispenser.lock_session()
        print("\n🔒 Dispenser session locked")

        return results

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        results['error'] = str(e)
        return results


async def main():
    """Main function."""
    results = await test_dispenser_wnd_transfer()

    # Save results
    timestamp = int(datetime.now().timestamp())
    results_file = f"dispenser_wnd_transfer_results_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Results saved to: {results_file}")

    # Print summary
    print("\n" + "=" * 50)
    if results['success']:
        print("🎉 DISPENSER WND TRANSFER TEST PASSED!")
        print("✅ Private key access from macOS Keychain verified")
        print("✅ Live blockchain transaction successful")
        print("✅ Dispenser can send WND transfers")
        if 'transfer_result' in results and results['transfer_result'].get('transaction_hash'):
            tx_hash = results['transfer_result']['transaction_hash']
            print(f"🔗 Transaction: {tx_hash}")
            print(f"🌐 View on Westend Explorer: https://westend.subscan.io/extrinsic/{tx_hash}")
    else:
        print("❌ DISPENSER WND TRANSFER TEST FAILED!")
        if 'error' in results:
            print(f"   Error: {results['error']}")

    return results['success']


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)