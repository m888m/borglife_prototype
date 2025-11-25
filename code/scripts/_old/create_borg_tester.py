#!/usr/bin/env python3
"""
Create Borg Tester Script
Creates a new borg tester with keypair stored in keyring and database entry.
"""

import asyncio
import json
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import keyring
from jam_mock.borg_address_manager import BorgAddressManager
from jam_mock.secure_borg_creation import create_secure_borg
from substrateinterface import Keypair


async def main():
    """Create a new borg tester with keyring storage."""
    print("🧬 CREATING BORG TESTER")
    print("=" * 40)

    # Generate unique borg ID
    borg_id = f"borgTester_{int(time.time())}"
    print(f"Borg ID: {borg_id}")

    # Generate test DNA hash
    dna_hash = "a1b2c3d4e5f67890123456789012345678901234567890123456789012345678"

    try:
        # Create borg with keyring storage
        print("\\n🔐 Creating borg with keyring storage...")
        result = create_secure_borg(borg_id, dna_hash)

        if not result["success"]:
            print(f"❌ Borg creation failed: {result['error']}")
            return False

        borg_address = result["address"]
        print(f"✅ Borg created successfully!")
        print(f"   Address: {borg_address}")
        print(f"   Keypair stored in macOS Keychain")

        # Verify keypair access
        print("\\n🔍 Verifying keypair access...")

        service_name = f"borglife-borg-{borg_id}"
        private_key = keyring.get_password(service_name, "private_key")
        public_key = keyring.get_password(service_name, "public_key")
        stored_address = keyring.get_password(service_name, "address")

        if not all([private_key, public_key, stored_address]):
            print("❌ Keypair verification failed - missing keys")
            return False

        if stored_address != borg_address:
            print("❌ Address mismatch in keyring")
            return False

        print("✅ Keypair verification passed")
        print(f"   Private key: {private_key[:32]}...")
        print(f"   Public key: {public_key[:32]}...")
        print(f"   Address: {stored_address}")

        # Test keypair reconstruction
        print("\\n🔧 Testing keypair reconstruction...")
        try:
            private_key_bytes = bytes.fromhex(private_key)
            reconstructed_keypair = Keypair(
                private_key=private_key_bytes, ss58_format=42
            )

            if reconstructed_keypair.ss58_address != borg_address:
                print("❌ Keypair reconstruction failed - address mismatch")
                return False

            # Test signing
            test_message = b"Hello BorgTester"
            signature = reconstructed_keypair.sign(test_message)
            is_valid = reconstructed_keypair.verify(test_message, signature)

            if not is_valid:
                print("❌ Signature verification failed")
                return False

            print("✅ Keypair reconstruction and signing test passed")

        except Exception as e:
            print(f"❌ Keypair reconstruction failed: {e}")
            return False

        # Add to address manager
        print("\\n📋 Adding to address manager...")
        from jam_mock.borg_address_manager import BorgAddressManager

        address_manager = BorgAddressManager()
        address_manager.register_borg_address(borg_id, dna_hash)
        print("✅ Added to address manager")

        # Save results
        results = {
            "borg_id": borg_id,
            "address": borg_address,
            "service_name": service_name,
            "created_at": time.time(),
            "keyring_verified": True,
            "address_manager_added": True,
        }

        results_file = f"borg_tester_{borg_id}_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\\n📄 Results saved to: {results_file}")

        print("\\n🎉 BORG TESTER CREATION COMPLETE!")
        print("=" * 40)
        print(f"Borg ID: {borg_id}")
        print(f"Address: {borg_address}")
        print(f"Keyring Service: {service_name}")
        print("\\n✅ Ready for WND transfer testing")

        return True

    except Exception as e:
        print(f"❌ Borg tester creation failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
