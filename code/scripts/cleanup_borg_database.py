#!/usr/bin/env python3
"""
Cleanup Borg Database Script
Ensure borg database is accessible and clean up borg2 entries.
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


async def check_database_access():
    """Check if database is accessible and working."""
    print("🔍 CHECKING DATABASE ACCESS")
    print("=" * 35)

    try:
        # Try to initialize borg manager
        audit_logger = DemoAuditLogger()
        borg_manager = BorgAddressManager(audit_logger=audit_logger)

        # Try to list borgs
        borgs = borg_manager.list_registered_borgs()

        if borgs:
            print(f"✅ Database accessible - found {len(borgs)} registered borgs:")
            for borg in borgs:
                print(f"   • {borg['borg_id']}: {borg['substrate_address'][:20]}...")
        else:
            print("✅ Database accessible - no borgs registered (expected)")

        return True

    except Exception as e:
        print(f"❌ Database access failed: {e}")
        print("   This may be due to Supabase connection issues")
        return False


def cleanup_borg2_keystore():
    """Clean up borg2 keystore file."""
    print("\n🧹 CLEANING UP BORG2 KEYSTORE")
    print("=" * 30)

    keystore_path = "code/jam_mock/.borg_keystore.enc"

    if os.path.exists(keystore_path):
        try:
            # Read current data
            with open(keystore_path, 'r') as f:
                data = json.load(f)

            if data.get('name') == 'borg2':
                # Remove the file
                os.remove(keystore_path)
                print(f"✅ Deleted keystore file: {keystore_path}")
                return True
            else:
                print(f"⚠️  Keystore file exists but contains: {data.get('name', 'unknown')}")
                return False

        except Exception as e:
            print(f"❌ Error reading keystore file: {e}")
            return False
    else:
        print("ℹ️  No borg2 keystore file found")
        return True


def cleanup_borg2_keyring():
    """Clean up borg2 entries from macOS Keychain."""
    print("\n🔐 CLEANING UP BORG2 KEYRING ENTRIES")
    print("=" * 35)

    service_name = "borglife-keystore"
    borg_id = "borg2"
    cleaned_keys = 0

    key_types = ['private_key', 'public_key', 'address', 'metadata']
    for key_type in key_types:
        key_name = f"{borg_id}_{key_type}"
        try:
            password = keyring.get_password(service_name, key_name)
            if password:
                keyring.delete_password(service_name, key_name)
                print(f"✅ Deleted {key_type} from macOS Keychain")
                cleaned_keys += 1
        except:
            pass

    if cleaned_keys > 0:
        print(f"✅ Cleaned {cleaned_keys} keys from macOS Keychain")
    else:
        print("ℹ️  No borg2 keys found in macOS Keychain")

    return True


async def cleanup_borg2_database():
    """Clean up borg2 from database if it exists."""
    print("\n🗃️  CLEANING UP BORG2 DATABASE ENTRIES")
    print("=" * 35)

    try:
        audit_logger = DemoAuditLogger()
        borg_manager = BorgAddressManager(audit_logger=audit_logger)

        # Check if borg2 exists in database
        address = borg_manager.get_borg_address('borg2')
        if address:
            print(f"⚠️  borg2 found in database with address: {address}")
            print("   Manual database cleanup may be required")
            print("   (Supabase direct access needed for deletion)")
        else:
            print("✅ No borg2 entries found in database")

        return True

    except Exception as e:
        print(f"❌ Database cleanup check failed: {e}")
        return False


async def verify_cleanup():
    """Verify that cleanup was successful."""
    print("\n🔍 VERIFYING CLEANUP")
    print("=" * 20)

    # Run borg check script to verify
    print("Running final borg keypair check...")
    os.system("cd /Users/m888888/borglife/borglife_proto_private && python3 code/scripts/check_borg_keypairs.py | grep -A 10 'SUMMARY'")


async def main():
    """Main cleanup function."""
    print("🧹 BORGLIFE BORG DATABASE CLEANUP")
    print("=" * 40)

    # Step 1: Check database access
    db_access = await check_database_access()

    # Step 2: Clean up keystore
    keystore_clean = cleanup_borg2_keystore()

    # Step 3: Clean up keyring
    keyring_clean = cleanup_borg2_keyring()

    # Step 4: Check database for borg2
    db_clean = await cleanup_borg2_database()

    # Step 5: Verify cleanup
    await verify_cleanup()

    print("\n" + "=" * 40)
    print("CLEANUP SUMMARY:")
    print(f"   Database Access: {'✅ OK' if db_access else '❌ FAILED'}")
    print(f"   Keystore Cleanup: {'✅ OK' if keystore_clean else '❌ FAILED'}")
    print(f"   Keyring Cleanup: {'✅ OK' if keyring_clean else '❌ FAILED'}")
    print(f"   Database Check: {'✅ OK' if db_clean else '❌ FAILED'}")

    success_count = sum([db_access, keystore_clean, keyring_clean, db_clean])
    if success_count == 4:
        print("🎉 All cleanup operations completed successfully!")
    else:
        print(f"⚠️  {4 - success_count} cleanup operations had issues")


if __name__ == "__main__":
    asyncio.run(main())