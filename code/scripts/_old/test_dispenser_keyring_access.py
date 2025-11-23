#!/usr/bin/env python3
"""
Test Dispenser Keyring Access
Safely verify that dispenser private key can be accessed from macOS Keychain.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from security.secure_dispenser import SecureDispenser


def test_dispenser_keyring_access():
    """Test dispenser keypair access from macOS Keychain."""
    print("🔑 TESTING DISPENSER KEYRING ACCESS")
    print("=" * 50)

    try:
        # Initialize dispenser
        dispenser = SecureDispenser()
        print("✅ Dispenser initialized")

        # Check keystore exists
        if not dispenser._ensure_keystore():
            print("❌ Keystore not found")
            return False

        print("✅ Keystore file exists")

        # Attempt to unlock dispenser (loads keypair from keyring)
        if not dispenser.unlock_for_session():
            print("❌ Failed to unlock dispenser - keyring access failed")
            return False

        print("✅ Dispenser unlocked successfully")
        print("✅ Keypair loaded from macOS Keychain")

        # Verify keypair integrity
        if not dispenser.unlocked_keypair:
            print("❌ No keypair loaded")
            return False

        # Get address (safe to display)
        address = dispenser.unlocked_keypair.ss58_address
        print(f"✅ Dispenser Address: {address}")

        # Verify address matches keystore metadata
        import json

        with open(dispenser.keystore_path, "r") as f:
            keystore_data = json.load(f)

        stored_address = keystore_data.get("ss58_address")
        if address != stored_address:
            print(f"❌ Address mismatch: {address} != {stored_address}")
            return False

        print("✅ Address matches keystore metadata")

        # Test keypair functionality (signing capability)
        from substrateinterface import Keypair

        test_message = b"test_message_for_signing"
        signature = dispenser.unlocked_keypair.sign(test_message)

        if not signature:
            print("❌ Keypair signing failed")
            return False

        print("✅ Keypair signing capability verified")

        # Verify signature
        is_valid = dispenser.unlocked_keypair.verify(test_message, signature)
        if not is_valid:
            print("❌ Signature verification failed")
            return False

        print("✅ Signature verification successful")

        # Lock dispenser
        dispenser.lock_session()
        print("✅ Dispenser session locked")

        print("\n" + "=" * 50)
        print("🎉 DISPENSER KEYRING ACCESS TEST PASSED!")
        print("✅ Private key securely stored in macOS Keychain")
        print("✅ Keypair can be loaded and used for signing")
        print("✅ Address integrity verified")
        print("✅ Session management working correctly")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = test_dispenser_keyring_access()
    sys.exit(0 if success else 1)
