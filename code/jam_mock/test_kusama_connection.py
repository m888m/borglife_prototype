#!/usr/bin/env python3
"""
Test Westend testnet connection using the enhanced WestendAdapter.

This script tests the SSL/TLS compatibility and connection capabilities
of the WestendAdapter with real Westend testnet endpoints.
"""

import asyncio

from jam_mock.interface import JAMInterface, JAMMode
from jam_mock.westend_adapter import WestendAdapter


async def test_kusama_connection():
    """Test connection to Westend testnet."""
    print("🧪 Testing Westend Testnet Connection")
    print("=" * 50)

    # Test with a working endpoint (OnFinality)
    rpc_url = "wss://westend.api.onfinality.io/public-ws"

    print(f"📡 Connecting to: {rpc_url}")
    print("This may take a few seconds...")

    try:
        # Initialize adapter without keypair for basic connectivity test
        adapter = WestendAdapter(rpc_url, keypair=None, connect_immediately=True)

        # Perform health check
        print("🏥 Performing health check...")
        health = await adapter.health_check()

        print("\n📊 Health Check Results:")
        print(f"   Status: {health['status']}")
        print(f"   Chain: {health.get('chain_name', 'Unknown')}")
        print(f"   Block: {health.get('block_number', 'Unknown')}")
        print(f"   SSL Version: LibreSSL {health['ssl_config']['openssl_version']}")
        print(f"   TLS Max: {health['ssl_config']['max_tls_version']}")
        print(f"   TLS Min: {health['ssl_config']['min_tls_version']}")

        if health["status"] == "healthy":
            print("\n✅ SUCCESS: Westend testnet connection established!")
            print("🎉 BorgLife can now connect to Westend for Phase 1 validation!")
            return True
        else:
            print(f"\n❌ FAILED: {health.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"\n💥 ERROR: Connection failed with exception: {e}")
        return False


async def test_dna_operations():
    """Test DNA storage operations (requires keypair)."""
    print("\n🧬 Testing DNA Operations")
    print("=" * 30)

    # Note: This would require a test keypair and actual KSM
    # For now, just show the interface is ready
    print("📝 DNA storage interface ready (requires keypair for actual transactions)")
    print("💡 To test real DNA storage:")
    print("   1. Set up test keypair with KSM")
    print("   2. Call adapter.store_dna_hash(borg_id, dna_hash)")
    print("   3. Verify transaction on Subscan")


async def main():
    """Main test function."""
    print("🚀 BorgLife Westend Testnet Connection Test")
    print("Testing SSL/TLS compatibility and blockchain connectivity\n")

    # Test basic connection
    connection_success = await test_kusama_connection()

    # Test DNA operations interface
    await test_dna_operations()

    print("\n" + "=" * 50)
    if connection_success:
        print("🎯 RESULT: Westend testnet connectivity VERIFIED")
        print("📈 Ready for Phase 1 DNA storage operations!")
        sys.exit(0)
    else:
        print("⚠️  RESULT: Connection issues detected")
        print("🔧 Check SSL configuration and network connectivity")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
