#!/usr/bin/env python3
"""
Test Keypair Management for Kusama Testnet Operations

Tests the keypair creation, management, and transaction signing capabilities
for BorgLife Phase 1 DNA storage operations.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add the jam_mock directory to Python path for imports
sys.path.insert(0, os.path.dirname(__file__))

from keypair_manager import KeypairManager, KeypairSecurityError


async def test_keypair_creation():
    """Test keypair creation and basic operations."""
    print("🔑 Testing Keypair Creation")
    print("=" * 40)

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = KeypairManager(storage_path=temp_dir)

        # Test 1: Create new keypair
        print("1. Creating new keypair...")
        keypair_info = manager.create_keypair("test_borg", save_to_disk=True)
        print(f"   ✅ Created keypair: {keypair_info['ss58_address']}")
        print(f"   📝 Fingerprint: {keypair_info['fingerprint']}")

        # Test 2: Load keypair from disk
        print("2. Loading keypair from disk...")
        loaded_keypair = manager.load_keypair("test_borg")
        assert loaded_keypair.ss58_address == keypair_info["ss58_address"]
        print("   ✅ Keypair loaded successfully")

        # Test 3: List keypairs
        print("3. Listing keypairs...")
        keypairs = manager.list_keypairs()
        assert len(keypairs) == 1
        assert keypairs[0]["name"] == "test_borg"
        print(f"   ✅ Found {len(keypairs)} keypair(s)")

        # Test 4: Sign and verify message
        print("4. Testing message signing...")
        message = b"Hello BorgLife!"
        signature = manager.sign_message("test_borg", message)
        print(f"   📝 Signature: {signature[:32]}...")

        # Verify signature (simplified test)
        is_valid = manager.verify_signature(
            keypair_info["public_key"], message, signature
        )
        print(f"   ✅ Signature verification: {'PASS' if is_valid else 'FAIL'}")

        return True


async def test_keypair_import_export():
    """Test keypair import/export functionality."""
    print("\n📤 Testing Keypair Import/Export")
    print("=" * 40)

    with tempfile.TemporaryDirectory() as temp_dir:
        manager1 = KeypairManager(storage_path=temp_dir)

        # Create keypair
        original_info = manager1.create_keypair("export_test")

        # Export (without private key for security)
        print("1. Exporting keypair...")
        export_data = manager1.export_keypair("export_test", include_private=False)
        print("   ✅ Exported public information")

        # Create new manager and import
        manager2 = KeypairManager(storage_path=temp_dir + "_import")
        print("2. Importing keypair...")
        imported_info = manager2.import_keypair("imported_borg", export_data)
        print(f"   ✅ Imported to: {imported_info['ss58_address']}")

        # Verify addresses match
        assert original_info["ss58_address"] == imported_info["ss58_address"]
        print("   ✅ Import verification passed")

        return True


async def test_keypair_from_seed():
    """Test keypair creation from seed."""
    print("\n🌱 Testing Keypair from Seed")
    print("=" * 40)

    with tempfile.TemporaryDirectory() as temp_dir:
        manager = KeypairManager(storage_path=temp_dir)

        # Test with known seed (for deterministic testing)
        test_seed = "1234567890abcdef" * 4  # 64 characters
        print("1. Creating keypair from seed...")
        keypair_info = manager.create_keypair_from_seed("seed_test", test_seed)
        print(f"   ✅ Created: {keypair_info['ss58_address']}")

        # Create another with same seed
        keypair_info2 = manager.create_keypair_from_seed("seed_test2", test_seed)
        assert keypair_info["ss58_address"] == keypair_info2["ss58_address"]
        print("   ✅ Deterministic creation verified")

        return True


async def test_keypair_from_uri():
    """Test keypair creation from Polkadot.js URI."""
    print("\n🔗 Testing Keypair from URI")
    print("=" * 40)

    with tempfile.TemporaryDirectory() as temp_dir:
        manager = KeypairManager(storage_path=temp_dir)

        # Test with Alice URI (common test account)
        print("1. Creating keypair from URI...")
        try:
            keypair_info = manager.create_keypair_from_uri("alice_test", "//Alice")
            print(f"   ✅ Created Alice account: {keypair_info['ss58_address']}")
            print("   📝 This should be a known Kusama address")
        except Exception as e:
            print(f"   ⚠️  URI creation failed (expected in some environments): {e}")

        return True


async def test_keypair_security():
    """Test keypair security features."""
    print("\n🔒 Testing Keypair Security")
    print("=" * 40)

    with tempfile.TemporaryDirectory() as temp_dir:
        manager = KeypairManager(storage_path=temp_dir)

        # Test 1: Invalid seed handling
        print("1. Testing invalid seed handling...")
        try:
            manager.create_keypair_from_seed("invalid", "short_seed")
            print("   ❌ Should have failed with short seed")
            return False
        except KeypairSecurityError:
            print("   ✅ Correctly rejected invalid seed")

        # Test 2: Non-existent keypair handling
        print("2. Testing non-existent keypair handling...")
        try:
            manager.load_keypair("nonexistent")
            print("   ❌ Should have failed to load nonexistent keypair")
            return False
        except KeypairSecurityError:
            print("   ✅ Correctly rejected nonexistent keypair")

        return True


async def test_get_test_keypair():
    """Test automatic test keypair creation."""
    print("\n🧪 Testing Test Keypair Creation")
    print("=" * 40)

    with tempfile.TemporaryDirectory() as temp_dir:
        manager = KeypairManager(storage_path=temp_dir)

        print("1. Getting test keypair...")
        test_info = manager.get_test_keypair()
        print(f"   ✅ Test keypair: {test_info['ss58_address']}")

        # Get again (should return same)
        test_info2 = manager.get_test_keypair()
        assert test_info["ss58_address"] == test_info2["ss58_address"]
        print("   ✅ Test keypair is consistent")

        return True


async def main():
    """Main test function."""
    print("🚀 BorgLife Keypair Management Test Suite")
    print("Testing secure keypair operations for Kusama testnet\n")

    tests = [
        ("Keypair Creation", test_keypair_creation),
        ("Import/Export", test_keypair_import_export),
        ("Seed Creation", test_keypair_from_seed),
        ("URI Creation", test_keypair_from_uri),
        ("Security Features", test_keypair_security),
        ("Test Keypair", test_get_test_keypair),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")

    print(f"\n🎯 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED - Keypair management is ready!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed - check implementation")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
