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

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.inter_borg_transfer import InterBorgTransfer
from jam_mock.kusama_adapter import WestendAdapter
from jam_mock.borg_address_manager import BorgAddressManager
from jam_mock.economic_validator import EconomicValidator
from jam_mock.transaction_manager import TransactionManager
from jam_mock.demo_audit_logger import DemoAuditLogger


async def main():
    """Main transfer test function."""
    print("🔄 BORG-TO-BORG WND TRANSFER TEST")
    print("=" * 50)

    # Test configuration
    from_borg_id = "borgTester"  # borg 1 - has WND from dispenser transfer
    to_borg_id = "borg_2"
    transfer_amount_wnd = 0.5

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

        # Check borg addresses
        print("\n🔍 Checking borg addresses...")
        from_address = address_manager.get_borg_address(from_borg_id)
        to_address = address_manager.get_borg_address(to_borg_id)

        if not from_address:
            raise Exception(f"No address found for borg {from_borg_id}")
        if not to_address:
            raise Exception(f"No address found for borg {to_borg_id}")

        print(f"   {from_borg_id}: {from_address}")
        print(f"   {to_borg_id}: {to_address}")

        # Check keypairs
        print("\n🔑 Checking keypair access...")
        from_keypair = address_manager.get_borg_keypair(from_borg_id)
        if not from_keypair:
            raise Exception(f"No keypair found in macOS Keychain for borg {from_borg_id}")

        print(f"   {from_borg_id} keypair: ✅ Available")
        print(f"   Address match: {from_keypair.ss58_address == from_address}")

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
        # Execute transfer
        print(f"\n💸 Executing WND transfer: {from_borg_id} -> {to_borg_id} ({transfer_amount_wnd} WND)...")

        transfer_result = await transfer_handler.transfer_wnd_between_borgs(
            from_borg_id=from_borg_id,
            to_borg_id=to_borg_id,
            amount_wnd=transfer_amount_wnd,
            description="Test transfer between borgs"
        )

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