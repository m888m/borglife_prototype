#!/usr/bin/env python3
"""
Check macOS Keychain contents for BorgLife keypairs - Address-Based Compatible.
Checks both old borg_id-based and new address-based keyring services.
"""

import keyring
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.borg_address_manager_address_primary import BorgAddressManagerAddressPrimary


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
            address = borg.get('substrate_address')
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
                    'service': service,
                    'private_key': private_key[:20] + "..." if private_key else None,
                    'public_key': public_key[:20] + "..." if public_key else None,
                    'address': address,
                    'borg_id': borg_id,
                    'format': 'address-based' if service.startswith('borglife-address-') else 'borg_id-based'
                }
                found_entries.append(entry)

                if entry['format'] == 'address-based':
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
        print(f"\n⚠️  Found {len(old_format_entries)} entries using old borg_id-based format")
        print("   Consider migrating to address-based format for better security")

    if new_format_entries:
        print(f"\n✅ Found {len(new_format_entries)} entries using new address-based format")
        print("   Address-based storage provides better blockchain alignment")

    return found_entries
            
            
def validate_keypair_integrity(service_name: str) -> bool:
    """Validate keypair integrity for a specific service."""
    print(f"\n🔍 Validating keypair integrity for: {service_name}")

    try:
        import sys
        sys.path.append('code')
        from jam_mock.borg_address_manager_robust import BorgAddressManagerRobust

        manager = BorgAddressManagerRobust()

        # Extract identifier from service name
        if service_name.startswith('borglife-address-'):
            identifier = service_name.replace('borglife-address-', '')
        elif service_name.startswith('borglife-borg-'):
            identifier = service_name.replace('borglife-borg-', '')
        else:
            identifier = service_name.replace('borglife-', '')

        # Use robust validation
        validation = manager.validate_keypair_access(identifier)

        if validation['accessible']:
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


def main():
    """Main function with enhanced validation."""
    entries = list_keyring_entries()

    if entries:
        print("\n🔧 Keypair Integrity Validation:")
        for entry in entries:
            validate_keypair_integrity(entry['service'])
    else:
        print("\n❌ No keyring entries found for BorgLife")

    print("\n📋 Recommendations:")
    print("   • Use address-based services for new borgs")
    print("   • Run migration script to update old services")
    print("   • Regularly validate keypair integrity")


if __name__ == "__main__":
    main()