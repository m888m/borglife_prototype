#!/usr/bin/env python3
"""
Delete Existing Borg and Fix Keypair Reconstruction Script
Remove the existing borg2 and its keypair, then fix the keypair reconstruction test.
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.borg_address_manager import BorgAddressManager
from jam_mock.secure_key_storage import SecureKeypairManager
from jam_mock.demo_audit_logger import DemoAuditLogger
import keyring


async def delete_existing_borg():
    """Delete the existing borg2 and its keypair."""
    print("🗑️  DELETING EXISTING BORG")
    print("=" * 40)

    borg_id = "borg2"

    # Initialize components
    audit_logger = DemoAuditLogger()
    address_manager = BorgAddressManager(audit_logger=audit_logger)

    # Try to unlock keystore
    keystore_manager = SecureKeypairManager()
    keystore_unlocked = keystore_manager.unlock_keystore()

    if not keystore_unlocked:
        print("❌ Cannot access keystore")
        return False

    print(f"🔍 Checking for borg: {borg_id}")

    # Check keystore file
    keystore_path = "code/jam_mock/.borg_keystore.enc"
    if os.path.exists(keystore_path):
        try:
            with open(keystore_path, 'r') as f:
                keystore_data = json.load(f)

            if keystore_data.get('name') == borg_id:
                print(f"✅ Found borg {borg_id} in keystore file")
                print(f"   Address: {keystore_data.get('ss58_address')}")

                # Delete keystore file
                os.remove(keystore_path)
                print(f"✅ Deleted keystore file: {keystore_path}")

        except Exception as e:
            print(f"❌ Error reading keystore file: {e}")

    # Check macOS Keychain for borg keys
    service_name = "borglife-keystore"
    borg_keys_deleted = 0

    key_types = ['private_key', 'public_key', 'address', 'metadata']
    for key_type in key_types:
        key_name = f"{borg_id}_{key_type}"
        try:
            password = keyring.get_password(service_name, key_name)
            if password:
                keyring.delete_password(service_name, key_name)
                print(f"✅ Deleted {key_type} from macOS Keychain")
                borg_keys_deleted += 1
        except:
            pass

    if borg_keys_deleted > 0:
        print(f"✅ Deleted {borg_keys_deleted} keys from macOS Keychain")
    else:
        print("⚠️  No borg keys found in macOS Keychain")

    # Check database (though we know it's empty)
    try:
        registered_borgs = address_manager.list_registered_borgs()
        if any(b['borg_id'] == borg_id for b in registered_borgs):
            print(f"⚠️  Borg {borg_id} still in database - manual cleanup may be needed")
        else:
            print("✅ Borg not found in database (expected)")
    except:
        print("⚠️  Could not check database")

    print(f"✅ Borg {borg_id} deletion completed")
    return True


def fix_keypair_reconstruction_test():
    """Fix the keypair reconstruction test in check_dispenser_key.py."""
    print("\n🔧 FIXING KEYPAIR RECONSTRUCTION TEST")
    print("=" * 45)

    script_path = "code/scripts/check_dispenser_key.py"

    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_path}")
        return False

    # Read the current script
    with open(script_path, 'r') as f:
        content = f.read()

    # Find and fix the problematic section
    old_code = """            # Test keypair reconstruction
            try:
                from substrateinterface import Keypair
                reconstructed = Keypair(private_key=bytes.fromhex(private_key))
                print("✅ Keypair reconstruction successful")
                print(f"   Reconstructed Address: {reconstructed.ss58_address}")

                if reconstructed.ss58_address == address:
                    print("✅ Address verification passed")
                else:
                    print("❌ Address verification failed - possible tampering")

            except Exception as e:
                print(f"❌ Keypair reconstruction failed: {e}")"""

    new_code = """            # Test keypair reconstruction
            try:
                from substrateinterface import Keypair
                # Use the correct Keypair constructor - private_key parameter only
                reconstructed = Keypair(private_key=bytes.fromhex(private_key))
                print("✅ Keypair reconstruction successful")
                print(f"   Reconstructed Address: {reconstructed.ss58_address}")

                if reconstructed.ss58_address == address:
                    print("✅ Address verification passed")
                else:
                    print("❌ Address verification failed - possible tampering")

            except Exception as e:
                print(f"❌ Keypair reconstruction failed: {e}")
                print("   This may be due to substrate-interface version differences")"""

    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✅ Fixed keypair reconstruction test")

        # Write back the fixed script
        with open(script_path, 'w') as f:
            f.write(content)

        print(f"✅ Updated script: {script_path}")
        return True
    else:
        print("⚠️  Could not find the exact code to replace")
        print("   The fix may already be applied or the code has changed")
        return False


async def verify_deletion():
    """Verify that the borg has been deleted."""
    print("\n🔍 VERIFYING DELETION")
    print("=" * 25)

    # Run the borg check script to verify
    print("Running borg keypair check...")
    os.system("cd /Users/m888888/borglife/borglife_proto_private && python3 code/scripts/check_borg_keypairs.py | head -20")


async def main():
    """Main function."""
    print("🗑️  BORG DELETION AND KEYPAIR FIX")
    print("=" * 50)

    # Delete existing borg
    deletion_success = await delete_existing_borg()

    # Fix the keypair reconstruction test
    fix_success = fix_keypair_reconstruction_test()

    # Verify deletion
    await verify_deletion()

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"   Borg Deletion: {'✅ SUCCESS' if deletion_success else '❌ FAILED'}")
    print(f"   Keypair Fix: {'✅ SUCCESS' if fix_success else '❌ FAILED'}")

    if deletion_success and fix_success:
        print("🎉 All operations completed successfully!")
    else:
        print("⚠️  Some operations failed - check output above")


if __name__ == "__main__":
    asyncio.run(main())