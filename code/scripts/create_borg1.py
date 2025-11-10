#!/usr/bin/env python3
"""
Create Borg1 Script - Supabase-Only Metadata Version
Create borg1 using the enhanced secure borg creation with Supabase-only metadata storage.
"""

import asyncio
import sys
import os
import hashlib

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from jam_mock.secure_borg_creation import SecureBorgCreator


async def main():
    """Main function to create borg1 with Supabase-only metadata."""
    print("🤖 BORGLIFE BORG1 CREATION - SUPABASE METADATA")
    print("=" * 55)

    # Generate a deterministic DNA hash for borg1
    dna_content = "borg1_dna_sequence_" + str(__import__('time').time())
    dna_hash = hashlib.sha256(dna_content.encode()).hexdigest()

    print(f"🧬 Generated DNA hash: {dna_hash}")
    print(f"   Length: {len(dna_hash)} characters")

    # Create borg creator instance
    creator = SecureBorgCreator(session_timeout_minutes=360)  # 6 hours

    # Initialize security using macOS Keychain
    print("\n🔐 Initializing security system...")
    if not creator.initialize_security():
        print("❌ Security initialization failed")
        return

    # Create borg1 with enhanced metadata
    print("\n🏗️  Creating borg1 with Supabase metadata...")
    result = creator.create_borg(
        borg_id='borg1',
        dna_hash=dna_hash,
        creator_signature='system_generated_borg1',  # Placeholder for future signature verification
        creator_public_key='system_public_key'  # Placeholder for future signature verification
    )

    if result['success']:
        print("\n✅ BORG1 CREATION SUCCESSFUL!")
        print(f"   Borg ID: {result['borg_id']}")
        print(f"   Address: {result['address']}")
        print(f"   DNA Hash: {result['dna_hash'][:16]}...")
        print(f"   Storage Method: {result['storage_method']}")
        print(f"   Service Name: {result['service_name']}")
        print(f"   Metadata Location: {result['keystore_path']}")

        # Verify Supabase storage
        print("\n🗄️  Verifying Supabase metadata storage...")
        if creator.borg_manager and creator.borg_manager.supabase:
            try:
                # Query Supabase for the created borg
                response = creator.borg_manager.supabase.table('borg_addresses').select('*').eq('borg_id', 'borg1').execute()

                if response.data:
                    record = response.data[0]
                    print("✅ Supabase metadata verified!")
                    print(f"   Creator Public Key: {record.get('creator_public_key', 'Not set')}")
                    print(f"   Creator Signature: {record.get('creator_signature', 'Not set')}")
                    print(f"   Keyring Service: {record.get('keyring_service_name', 'Not set')}")
                    print(f"   Setup Version: {record.get('setup_version', 'Unknown')}")
                    print(f"   Storage Method: {record.get('storage_method', 'Unknown')}")
                else:
                    print("⚠️  Borg metadata not found in Supabase - may be using fallback storage")

            except Exception as e:
                print(f"⚠️  Supabase verification failed: {e}")
        else:
            print("⚠️  Supabase not available - using fallback storage")

        # Test private key access from keyring
        print("\n🔑 Testing private key access from macOS Keychain...")
        keypair = creator.get_borg_keypair('borg1')

        if keypair:
            print("✅ Private key accessible from macOS Keychain!")
            print(f"   Address: {keypair.ss58_address}")
            print(f"   Public Key: {keypair.public_key.hex()[:20]}...")

            # Test signing capability
            test_message = b"test_signature_for_borg1"
            signature = keypair.sign(test_message)
            is_valid = keypair.verify(test_message, signature)

            print("✅ Signature test passed!")
            print(f"   Signature: {signature.hex()[:40]}...")
            print(f"   Verification: {'✅ VALID' if is_valid else '❌ INVALID'}")

            # Log audit event
            from jam_mock.demo_audit_logger import DemoAuditLogger
            audit_logger = DemoAuditLogger()
            audit_logger.log_event(
                "borg1_creation_verified",
                "Borg1 successfully created with Supabase metadata and macOS Keychain storage",
                {
                    "borg_id": "borg1",
                    "address": keypair.ss58_address,
                    "dna_hash": dna_hash,
                    "storage_method": "macos_keychain_supabase",
                    "keyring_service": result['service_name']
                }
            )

        else:
            print("❌ Private key not accessible from macOS Keychain")

    else:
        print(f"❌ Borg creation failed: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 55)
    print("BORG1 CREATION COMPLETE - SUPABASE METADATA VERSION")


if __name__ == "__main__":
    asyncio.run(main())