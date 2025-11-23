#!/usr/bin/env python3
"""
Check macOS Keychain contents for BorgLife keypairs - Address-Based Compatible.
Checks both old borg_id-based and new address-based keyring services.
"""

import os
import sys
from typing import Any, Dict

import keyring

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.borg_address_manager_address_primary import \
    BorgAddressManagerAddressPrimary


def list_keyring_entries():
    """List all keyring entries related to BorgLife with address-based compatibility."""
    print("🔍 Checking macOS Keychain for BorgLife entries...")
    print("   📍 Supports both old borg_id and new address-based services")

    # Service names to check - both old and new patterns
    service_names = [
        # Old borg_id-based services
        "borglife-borg_1",
        "borglife-borg-2",
        "borglife-dispenser",
        "borglife-borgTester",
        # New address-based services (add known addresses)
        "borglife-address-5EeeSsZAzVzZjTnLA9yCV8pwsuQvbHDfYPZX5YcmitVFFA2c",  # borgTest1
        "borglife-address-5FFME3vBJ6XpJDZ9qJcbgY2KPYvTCEzMSPU1tj6VNWNb5NRA",  # borgTest2
    ]

    # Try to discover additional services from database
    try:
        manager = BorgAddressManagerAddressPrimary()
        registered_borgs = manager.list_registered_borgs()

        for borg in registered_borgs:
            address = borg.get("substrate_address")
            if address:
                service_name = f"borglife-address-{address}"
                if service_name not in service_names:
                    service_names.append(service_name)
                    print(f"   🔍 Added service from database: {service_name}")
    except Exception as e:
        print(f"   ⚠️  Could not load services from database: {e}")

    found_entries = []
    old_format_entries = []
    new_format_entries = []

    for service in service_names:
        print(f"\n🔑 Checking service: {service}")
        try:
            private_key = keyring.get_password(service, "private_key")
            public_key = keyring.get_password(service, "public_key")
            address = keyring.get_password(service, "address")
            borg_id = keyring.get_password(service, "borg_id")  # New field

            has_data = private_key or public_key or address

            if has_data:
                entry = {
                    "service": service,
                    "private_key": private_key[:20] + "..." if private_key else None,
                    "public_key": public_key[:20] + "..." if public_key else None,
                    "address": address,
                    "borg_id": borg_id,
                    "format": (
                        "address-based"
                        if service.startswith("borglife-address-")
                        else "borg_id-based"
                    ),
                }
                found_entries.append(entry)

                if entry["format"] == "address-based":
                    new_format_entries.append(entry)
                else:
                    old_format_entries.append(entry)

                print("  ✅ Found entry:")
                print(f"    Format: {entry['format']}")
                print(f"    Address: {address}")
                if borg_id:
                    print(f"    Borg ID: {borg_id}")
                print(f"    Private Key: {entry['private_key']}")
                print(f"    Public Key: {entry['public_key']}")
            else:
                print("  ❌ No entries found")

        except Exception as e:
            print(f"  ❌ Error checking service: {e}")

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total entries found: {len(found_entries)}")
    print(f"   Address-based format: {len(new_format_entries)}")
    print(f"   Borg ID-based format: {len(old_format_entries)}")

    if old_format_entries:
        print(
            f"\n⚠️  Found {len(old_format_entries)} entries using old borg_id-based format"
        )
        print("   Consider migrating to address-based format for better security")

    if new_format_entries:
        print(
            f"\n✅ Found {len(new_format_entries)} entries using new address-based format"
        )
        print("   Address-based storage provides better blockchain alignment")

    return found_entries


def validate_keypair_integrity(service_name: str) -> bool:
    """Validate keypair integrity for a specific service."""
    print(f"\n🔍 Validating keypair integrity for: {service_name}")

    try:
        import sys

        sys.path.append("code")
        from jam_mock.borg_address_manager_robust import \
            BorgAddressManagerRobust

        manager = BorgAddressManagerRobust()

        # Extract identifier from service name
        if service_name.startswith("borglife-address-"):
            identifier = service_name.replace("borglife-address-", "")
        elif service_name.startswith("borglife-borg-"):
            identifier = service_name.replace("borglife-borg-", "")
        else:
            identifier = service_name.replace("borglife-", "")

        # Use robust validation
        validation = manager.validate_keypair_access(identifier)

        if validation["accessible"]:
            print("  ✅ Keypair accessible and valid")
            print(f"    Service: {validation['service_name']}")
            return True
        else:
            print("  ❌ Keypair validation failed")
            print(f"    Error: {validation['error']}")
            print(f"    Code: {validation['error_code']}")
            return False

    except Exception as e:
        print(f"  ❌ Validation error: {e}")
        return False


def validate_dispenser_key_for_live_transactions():
    """Validate dispenser key access for live Westend transactions."""
    print("\n🔐 Validating Dispenser Key for Live Transactions")
    print("=" * 60)

    dispenser_service = "borglife-dispenser"

    try:
        # Check if dispenser key exists
        private_key = keyring.get_password(dispenser_service, "private_key")
        public_key = keyring.get_password(dispenser_service, "public_key")
        address = keyring.get_password(dispenser_service, "address")

        if not all([private_key, public_key, address]):
            print("❌ Dispenser key not found in keyring")
            print("   Required components missing:")
            print(f"   - Private key: {'✅' if private_key else '❌'}")
            print(f"   - Public key: {'✅' if public_key else '❌'}")
            print(f"   - Address: {'✅' if address else '❌'}")
            print("\n📋 To create dispenser key:")
            print("   1. Run dispenser setup script")
            print(
                "   2. Or manually create with: python -c \"from substrateinterface import Keypair; kp = Keypair.create_from_seed('your_seed'); print(f'Address: {kp.ss58_address}')\""
            )
            return False

        # Validate address format (Westend)
        if not address.startswith("5"):
            print(f"❌ Invalid address format: {address}")
            print("   Westend addresses should start with '5'")
            return False

        print("✅ Dispenser key components found:")
        print(f"   Address: {address}")
        print(f"   Public key: {public_key[:20]}...")

        # Test keypair reconstruction
        try:
            from substrateinterface import Keypair

            keypair = Keypair(private_key=bytes.fromhex(private_key), ss58_format=42)

            # Verify reconstruction
            if keypair.ss58_address != address:
                print(
                    f"❌ Address mismatch: expected {address}, got {keypair.ss58_address}"
                )
                return False

            if keypair.public_key.hex() != public_key:
                print("❌ Public key mismatch during reconstruction")
                return False

            print("✅ Keypair reconstruction successful")
            print("✅ Address and public key validation passed")

            # Test signing capability (dummy transaction)
            test_message = b"test_message_for_signing"
            signature = keypair.sign(test_message)
            is_valid = keypair.verify(test_message, signature)

            if is_valid:
                print("✅ Signing capability verified")
            else:
                print("❌ Signing verification failed")
                return False

            print("✅ Dispenser key is ready for live transactions")
            print(f"   Westend Address: {address}")
            print("   Can sign and submit transactions to Westend Asset Hub")
            return True

        except Exception as e:
            print(f"❌ Keypair reconstruction failed: {e}")
            return False

    except Exception as e:
        print(f"❌ Dispenser key validation error: {e}")
        return False


def check_westend_balance(address: str) -> Dict[str, Any]:
    """Check WND balance for a Westend address."""
    print(f"\n💰 Checking WND balance for: {address}")
    print("=" * 60)

    try:
        from substrateinterface import SubstrateInterface

        # Connect to Westend
        substrate = SubstrateInterface(url="wss://westend-rpc.polkadot.io")

        # Query account info
        account_info = substrate.query(
            module="System", storage_function="Account", params=[address]
        )

        if account_info.value:
            # Balance is in planck units (10^-12 WND)
            free_balance = account_info.value.get("data", {}).get("free", 0)
            reserved_balance = account_info.value.get("data", {}).get("reserved", 0)
            total_balance = free_balance + reserved_balance

            # Convert to WND (12 decimals)
            free_wnd = free_balance / (10**12)
            reserved_wnd = reserved_balance / (10**12)
            total_wnd = total_balance / (10**12)

            result = {
                "address": address,
                "free_balance_planck": free_balance,
                "reserved_balance_planck": reserved_balance,
                "total_balance_planck": total_balance,
                "free_balance_wnd": free_wnd,
                "reserved_balance_wnd": reserved_wnd,
                "total_balance_wnd": total_wnd,
            }

            print("✅ Balance query successful:")
            print(f"   Free Balance: {free_wnd:.6f} WND ({free_balance:,} planck)")
            print(
                f"   Reserved Balance: {reserved_wnd:.6f} WND ({reserved_balance:,} planck)"
            )
            print(f"   Total Balance: {total_wnd:.6f} WND ({total_balance:,} planck)")

            return result
        else:
            print("❌ No account data found")
            return {"error": "No account data found"}

    except Exception as e:
        print(f"❌ Balance check failed: {e}")
        return {"error": str(e)}


def main():
    """Main function with enhanced validation."""
    entries = list_keyring_entries()

    # Validate dispenser key for live transactions
    dispenser_valid = validate_dispenser_key_for_live_transactions()

    # Check dispenser WND balance if key is valid
    if dispenser_valid:
        dispenser_address = "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD"
        balance_result = check_westend_balance(dispenser_address)
        if "error" in balance_result:
            print(f"❌ Balance check failed: {balance_result['error']}")
        else:
            print("✅ Dispenser balance check completed")

    if entries:
        print("\n🔧 Keypair Integrity Validation:")
        for entry in entries:
            validate_keypair_integrity(entry["service"])
    else:
        print("\n❌ No keyring entries found for BorgLife")

    print("\n📋 Recommendations:")
    print("   • Use address-based services for new borgs")
    print("   • Run migration script to update old services")
    print("   • Regularly validate keypair integrity")

    if dispenser_valid:
        print("   ✅ Dispenser key ready for live transactions")
    else:
        print("   ❌ Dispenser key needs setup for live transactions")


if __name__ == "__main__":
    main()
