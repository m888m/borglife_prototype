#!/usr/bin/env python3
"""
Borg-to-Borg WND Transfer Test
Test secure WND transfers between borgs using live Westend network.
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.kusama_adapter import WestendAdapter
from jam_mock.borg_address_manager_address_primary import BorgAddressManagerAddressPrimary as BorgAddressManager
from jam_mock.demo_audit_logger import DemoAuditLogger
import keyring
from substrateinterface import Keypair


def find_keypair_by_address(target_address: str) -> Optional[Keypair]:
    """
    Search macOS Keychain for a keypair that matches the target address.

    Args:
        target_address: The SS58 address to find

    Returns:
        Keypair if found, None otherwise
    """
    try:
        # Common borg service names to check
        service_names = [
            "borglife-dispenser",  # Check dispenser first since borg 1 uses dispenser address
            "borglife-borg_1",
            "borglife-borg-2",
            "borglife-borgTester"
        ]

        print(f"   🔍 Searching for address: {target_address}")

        for service_name in service_names:
            try:
                print(f"   Checking service: {service_name}")
                private_key_hex = keyring.get_password(service_name, "private_key")
                public_key_hex = keyring.get_password(service_name, "public_key")
                address = keyring.get_password(service_name, "address")

                print(f"     Address in keyring: {address}")
                print(f"     Target address: {target_address}")
                print(f"     Match: {address == target_address}")
                print(f"     Private key present: {private_key_hex is not None}")
                print(f"     Public key present: {public_key_hex is not None}")

                if private_key_hex and public_key_hex and address == target_address:
                    print(f"     ✅ Found matching keypair data, reconstructing...")
                    try:
                        # Found matching address, reconstruct keypair
                        private_key = bytes.fromhex(private_key_hex)
                        keypair = Keypair(private_key=private_key)

                        # Verify it matches
                        reconstructed_address = keypair.ss58_address
                        print(f"     Reconstructed address: {reconstructed_address}")
                        if reconstructed_address == target_address:
                            print(f"   🎉 Successfully found and verified keypair for address {target_address}")
                            return keypair
                        else:
                            print(f"     ❌ Address mismatch: expected {target_address}, got {reconstructed_address}")
                    except Exception as e:
                        print(f"     ❌ Keypair reconstruction failed: {e}")
                else:
                    print(f"     ❌ Missing keypair components (private_key: {private_key_hex is not None}, public_key: {public_key_hex is not None})")

            except Exception as e:
                print(f"     Error checking service {service_name}: {e}")
                continue

        print(f"   ❌ No keypair found in keyring for address {target_address}")
        return None

    except Exception as e:
        print(f"   Error searching keyring for address {target_address}: {e}")
        return None


async def main():
    """Main transfer test function."""
    print("🔄 BORG-TO-BORG WND TRANSFER TEST")
    print("=" * 50)

    # Test configuration - Using specific Westend addresses
    from_address = "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD"  # borg 1
    to_address = "5FFME3vBJ6XpJDZ9qJcbgY2KPYvTCEzMSPU1tj6VNWNb5NRA"    # borg 2
    transfer_amount_wnd = 0.5

    # Map addresses to borg IDs for keyring lookup
    # Note: borg 1 uses the dispenser keypair
    from_borg_id = "dispenser"  # Use dispenser service for borg 1
    to_borg_id = "borg_2"

    results = {
        'test_start_time': datetime.utcnow().isoformat(),
        'from_borg_id': from_borg_id,
        'to_borg_id': to_borg_id,
        'transfer_amount_wnd': transfer_amount_wnd,
        'initial_balances': {},
        'final_balances': {},
        'transfer_result': None,
        'success': False,
        'error': None
    }

    try:
        # Initialize components
        print("\n🔧 Initializing transfer components...")

        # Westend adapter for blockchain operations
        westend_adapter = WestendAdapter("https://westend.api.onfinality.io/public-ws")

        # Address manager for borg keypair access
        address_manager = BorgAddressManager()

        # Economic validator dependencies
        cost_controller = None  # Simplified for test
        compliance_monitor = None  # Simplified for test
        economic_validator = EconomicValidator(cost_controller, compliance_monitor)

        # Transaction manager dependencies
        keypair_manager = None  # Simplified for test
        transaction_manager = TransactionManager(westend_adapter, keypair_manager)

        # Audit logger
        audit_logger = DemoAuditLogger()

        # Inter-borg transfer handler
        transfer_handler = InterBorgTransfer(
            westend_adapter=westend_adapter,
            address_manager=address_manager,
            economic_validator=economic_validator,
            transaction_manager=transaction_manager,
            audit_logger=audit_logger
        )

        print("✅ Components initialized")

        # Use specified addresses directly
        print("\n🔍 Using specified Westend addresses...")
        print(f"   {from_borg_id}: {from_address}")
        print(f"   {to_borg_id}: {to_address}")

        # Check keypairs - try to find by borg ID first, then by address
        print("\n🔑 Checking keypair access...")
        from_keypair = address_manager.get_borg_keypair(from_borg_id)

        # If not found by borg ID, try to find by address in keyring
        if not from_keypair:
            print(f"   Keypair not found for borg ID {from_borg_id}, searching by address...")
            from_keypair = find_keypair_by_address(from_address)

        if not from_keypair:
            raise Exception(f"No keypair found in macOS Keychain for borg {from_borg_id} (address: {from_address})")

        if from_keypair.ss58_address != from_address:
            raise Exception(f"Keypair address mismatch for borg {from_borg_id}: expected {from_address}, got {from_keypair.ss58_address}")

        print(f"   {from_borg_id} keypair: ✅ Available")
        print(f"   Address match: ✅ Verified")

        # Check initial balances
        print("\n💰 Checking initial balances...")
        from_balance = await westend_adapter.get_wnd_balance(from_address)
        to_balance = await westend_adapter.get_wnd_balance(to_address)

        from_balance_wnd = from_balance / (10 ** 12)
        to_balance_wnd = to_balance / (10 ** 12)

        results['initial_balances'] = {
            from_borg_id: {'address': from_address, 'balance_wnd': from_balance_wnd, 'balance_planck': from_balance},
            to_borg_id: {'address': to_address, 'balance_wnd': to_balance_wnd, 'balance_planck': to_balance}
        }

        print(".6f")
        print(".6f")
        # Validate transfer is possible
        if from_balance_wnd < transfer_amount_wnd:
            raise Exception(f"Insufficient balance: {from_balance_wnd} < {transfer_amount_wnd}")
        # Execute transfer directly using WestendAdapter
        print(f"\n💸 Executing WND transfer: {from_borg_id} -> {to_borg_id} ({transfer_amount_wnd} WND)...")

        # Convert amount to planck units
        amount_planck = int(transfer_amount_wnd * (10 ** 12))  # WND has 12 decimals

        # Set the sender's keypair for signing
        westend_adapter.set_keypair(from_keypair)

        # Execute the transfer
        transfer_tx = await westend_adapter.transfer_wnd(
            from_address, to_address, amount_planck
        )

        transfer_result = {
            'success': transfer_tx.get('success', False),
            'transaction_hash': transfer_tx.get('transaction_hash'),
            'block_number': transfer_tx.get('block_number'),
            'from_address': from_address,
            'to_address': to_address,
            'amount': str(transfer_amount_wnd),
            'from_borg_id': from_borg_id,
            'to_borg_id': to_borg_id,
            'errors': [transfer_tx.get('error', 'Unknown error')] if not transfer_tx.get('success') else [],
            'warnings': []
        }

        results['transfer_result'] = transfer_result

        if not transfer_result['success']:
            raise Exception(f"Transfer failed: {transfer_result['errors']}")

        print("✅ Transfer completed!")
        print(f"   Transaction: {transfer_result['transaction_hash']}")
        print(f"   Block: {transfer_result.get('block_number', 'Pending')}")

        # Wait for confirmation (brief delay)
        print("\n⏳ Waiting for confirmation...")
        await asyncio.sleep(3)

        # Check final balances
        print("\n💰 Checking final balances...")
        final_from_balance = await westend_adapter.get_wnd_balance(from_address)
        final_to_balance = await westend_adapter.get_wnd_balance(to_address)

        final_from_balance_wnd = final_from_balance / (10 ** 12)
        final_to_balance_wnd = final_to_balance / (10 ** 12)

        results['final_balances'] = {
            from_borg_id: {'address': from_address, 'balance_wnd': final_from_balance_wnd, 'balance_planck': final_from_balance},
            to_borg_id: {'address': to_address, 'balance_wnd': final_to_balance_wnd, 'balance_planck': final_to_balance}
        }

        print(".6f")
        print(".6f")
        # Validate balance changes
        expected_from_balance = from_balance_wnd - transfer_amount_wnd
        expected_to_balance = to_balance_wnd + transfer_amount_wnd

        from_balance_ok = abs(final_from_balance_wnd - expected_from_balance) < 0.000001
        to_balance_ok = abs(final_to_balance_wnd - expected_to_balance) < 0.000001

        if from_balance_ok and to_balance_ok:
            results['success'] = True
            print("✅ Balance validation PASSED")
        else:
            print("❌ Balance validation FAILED")
            print(".6f")
            print(".6f")
            print(".6f")
            print(".6f")
    except Exception as e:
        results['error'] = str(e)
        print(f"❌ Test failed: {e}")

    # Save results
    results['test_end_time'] = datetime.utcnow().isoformat()
    results_file = f"borg_to_borg_transfer_results_{int(datetime.utcnow().timestamp())}.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Results saved to: {results_file}")

    # Final summary
    print("\n" + "=" * 50)
    if results['success']:
        print("🎉 BORG-TO-BORG TRANSFER TEST PASSED!")
        print("✅ Keypair access from macOS Keychain verified")
        print("✅ Live blockchain WND transfer successful")
        print("✅ Balance validation confirmed")
        print(f"🔗 Transaction: {results['transfer_result']['transaction_hash']}")
        print("🌐 View on Westend Explorer: https://westend.subscan.io/extrinsic/" + results['transfer_result']['transaction_hash'])
    else:
        print("❌ BORG-TO-BORG TRANSFER TEST FAILED!")
        if 'error' in results:
            print(f"   Error: {results['error']}")

    print("=" * 50)

    return results


if __name__ == "__main__":
    asyncio.run(main())