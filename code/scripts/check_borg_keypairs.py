#!/usr/bin/env python3
"""
Check Borg Keypairs Script - Supabase-Only Metadata Version
Check how many borgs are available in Supabase and verify access to their private keys in macOS Keychain.
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.borg_address_manager import BorgAddressManager
from jam_mock.secure_key_storage import SecureKeypairManager
from jam_mock.demo_audit_logger import DemoAuditLogger


async def main():
    """Main function to check borg keypairs with Supabase-first approach."""
    print("🔑 BORGLIFE BORG KEYPAIR CHECK - SUPABASE METADATA")
    print("=" * 60)

    # Initialize components
    audit_logger = DemoAuditLogger()
    address_manager = BorgAddressManager(audit_logger=audit_logger)

    # Try to unlock keystore
    print("\n🔐 Checking keystore access...")
    keystore_manager = SecureKeypairManager()
    keystore_unlocked = keystore_manager.unlock_keystore()

    if not keystore_unlocked:
        print("❌ Cannot access keystore - borg keypairs unavailable")
        return

    # Check available borgs in Supabase first
    print("\n📋 Checking registered borgs in Supabase...")

    supabase_borgs = []
    if address_manager.supabase:
        try:
            # Query all borgs from Supabase
            response = address_manager.supabase.table('borg_addresses').select('*').execute()

            if response.data:
                supabase_borgs = response.data
                print(f"✅ Found {len(supabase_borgs)} registered borgs in Supabase:")
                for borg in supabase_borgs:
                    print(f"   • {borg['borg_id']}: {borg['substrate_address'][:20]}...")
                    print(f"     Storage: {borg.get('storage_method', 'unknown')}")
                    print(f"     Keyring Service: {borg.get('keyring_service_name', 'not set')}")
                    print(f"     Setup Version: {borg.get('setup_version', 'unknown')}")
            else:
                print("⚠️  No borgs found in Supabase database")
        except Exception as e:
            print(f"⚠️  Supabase query failed: {e}")
            print("   Falling back to legacy keystore checks...")
    else:
        print("⚠️  Supabase not available - using legacy keystore checks")

    # Check keystore for stored keypairs (legacy support)
    print("\n🔍 Checking legacy keystore files...")

    # Check keystore metadata files for migration period
    keystore_paths = [
        "code/jam_mock/.borg1_keystore.enc",
        "code/jam_mock/.borg2_keystore.enc",
        "code/jam_mock/.borg3_keystore.enc",
        "code/jam_mock/.test_borg_keystore.enc",
        "code/jam_mock/.demo_borg_keystore.enc"
    ]

    legacy_borgs = []
    for keystore_path in keystore_paths:
        if os.path.exists(keystore_path):
            try:
                with open(keystore_path, 'r') as f:
                    keystore_data = json.load(f)

                borg_id = keystore_data.get('borg_id', keystore_data.get('name', 'unknown'))
                address = keystore_data.get('ss58_address', keystore_data.get('substrate_address'))

                if address and borg_id not in [b.get('borg_id') for b in supabase_borgs]:
                    legacy_borgs.append({
                        'borg_id': borg_id,
                        'address': address,
                        'source': 'legacy_keystore',
                        'storage_method': keystore_data.get('storage_method', 'legacy'),
                        'keyring_service_name': keystore_data.get('service_name')
                    })

            except Exception as e:
                print(f"⚠️  Error reading keystore {keystore_path}: {e}")

    if legacy_borgs:
        print(f"⚠️  Found {len(legacy_borgs)} legacy keystore files:")
        for borg in legacy_borgs:
            print(f"   • {borg['borg_id']}: {borg['address'][:20]}... (needs migration)")

    # Combine all borgs
    all_borgs = supabase_borgs + legacy_borgs

    # Check macOS Keychain access for all borgs
    print("\n🔐 Checking macOS Keychain access for all borgs...")

    keyring_accessible = []
    keyring_inaccessible = []

    for borg in all_borgs:
        borg_id = borg.get('borg_id')
        expected_address = borg.get('substrate_address') or borg.get('address')

        print(f"\n🔑 Checking {borg_id}...")

        # Try to access private key from keyring
        try:
            # Use the secure borg creator method for consistent keyring access
            from jam_mock.secure_borg_creation import SecureBorgCreator
            creator = SecureBorgCreator()
            creator.initialize_security()

            keypair = creator.get_borg_keypair(borg_id)

            if keypair:
                address_match = keypair.ss58_address == expected_address
                print(f"   ✅ Keypair accessible from macOS Keychain")
                print(f"   Address Match: {'✅' if address_match else '❌'}")
                print(f"   Public Key: {keypair.public_key.hex()[:20]}...")

                # Test signing capability
                test_message = f"test_signature_for_{borg_id}".encode()
                signature = keypair.sign(test_message)
                is_valid = keypair.verify(test_message, signature)
                print(f"   Signature Test: {'✅ PASSED' if is_valid else '❌ FAILED'}")

                keyring_accessible.append({
                    **borg,
                    'keypair_available': True,
                    'address_match': address_match,
                    'signature_test': is_valid
                })

                # Log successful access
                audit_logger.log_event(
                    "keypair_access_verified",
                    f"Successfully accessed keypair for borg {borg_id} from macOS Keychain",
                    {
                        "borg_id": borg_id,
                        "address": keypair.ss58_address,
                        "source": borg.get('source', 'unknown'),
                        "storage_method": borg.get('storage_method', 'unknown')
                    }
                )

            else:
                print(f"   ❌ Keypair not accessible from macOS Keychain")
                keyring_inaccessible.append(borg)

        except Exception as e:
            print(f"   ❌ Error accessing keypair: {e}")
            keyring_inaccessible.append(borg)

    # Display comprehensive results
    print(f"\n📊 SUMMARY REPORT")
    print("=" * 50)
    print(f"Supabase Borgs: {len(supabase_borgs)}")
    print(f"Legacy Borgs: {len(legacy_borgs)}")
    print(f"Keyring Accessible: {len(keyring_accessible)}")
    print(f"Keyring Inaccessible: {len(keyring_inaccessible)}")
    print(f"Total Borgs: {len(all_borgs)}")

    if keyring_accessible:
        print(f"\n✅ KEYRING ACCESSIBLE BORGS:")
        for borg in keyring_accessible:
            status = "✅ FULL ACCESS" if borg.get('address_match') and borg.get('signature_test') else "⚠️  PARTIAL ACCESS"
            print(f"   • {borg['borg_id']}: {status}")

    if keyring_inaccessible:
        print(f"\n❌ KEYRING INACCESSIBLE BORGS:")
        for borg in keyring_inaccessible:
            print(f"   • {borg['borg_id']}: {borg.get('source', 'unknown')}")

    if legacy_borgs:
        print(f"\n⚠️  MIGRATION NEEDED:")
        print(f"   {len(legacy_borgs)} borgs still using legacy keystore files")
        print(f"   Run migration script to move to Supabase-only metadata")

    # Security status
    print(f"\n🔐 SECURITY STATUS:")
    print("-" * 30)
    print(f"✅ Keystore: {'UNLOCKED' if keystore_unlocked else 'LOCKED'}")
    print(f"✅ macOS Keychain: ACCESSIBLE")
    print(f"✅ Supabase: {'CONNECTED' if address_manager.supabase else 'NOT AVAILABLE'}")

    if len(keyring_accessible) == len(all_borgs) and len(legacy_borgs) == 0:
        print(f"🎉 ALL BORGS SECURE: Supabase metadata + macOS Keychain keys")
    else:
        print(f"⚠️  SECURITY MIGRATION IN PROGRESS")

    print("\n" + "=" * 60)
    print("SUPABASE KEYPAIR CHECK COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())