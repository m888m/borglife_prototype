#!/usr/bin/env python3
"""
Example: How to use composable borg balance sync functions in other Python files.

This script demonstrates different ways to import and use the borg_balance_syncer module.
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Initialize Supabase client (same as other scripts)
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.borglife")
    load_dotenv(dotenv_path=env_path)

    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")

    if supabase_url and supabase_key:
        supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized")
    else:
        supabase_client = None
        print("⚠️  Supabase credentials not found")

except Exception as e:
    supabase_client = None
    print(f"⚠️  Failed to initialize Supabase client: {e}")


async def example_1_convenience_functions():
    """Example 1: Using convenience functions (easiest way)."""
    print("\n" + "="*60)
    print("📖 Example 1: Convenience Functions")
    print("="*60)

    from jam_mock.borg_balance_syncer import sync_all_borg_balances, sync_single_borg_balance

    # Sync all borgs with custom settings
    print("🔄 Syncing all borg balances (max 2 for demo)...")
    result = await sync_all_borg_balances(
        supabase_client=supabase_client,
        batch_size=5,
        max_borgs=2,  # Limit for demo
        verbose=True
    )

    if result["success"]:
        print(f"✅ Synced {result['successful_syncs']} borgs successfully")
    else:
        print(f"❌ Sync failed: {result.get('error')}")

    # Sync single borg
    print("\n🔄 Syncing single borg...")
    single_result = await sync_single_borg_balance(
        "borg_1763999381",  # Use one of the borg IDs from our database
        supabase_client=supabase_client,
        verbose=True
    )

    if single_result["success"]:
        print(f"✅ Single borg sync: {single_result['balance_wnd']:.6f} WND")
    else:
        print(f"❌ Single borg sync failed: {single_result.get('error')}")


async def example_2_class_based():
    """Example 2: Using the BorgBalanceSyncer class for more control."""
    print("\n" + "="*60)
    print("📖 Example 2: BorgBalanceSyncer Class")
    print("="*60)

    from jam_mock.borg_balance_syncer import BorgBalanceSyncer

    # Create syncer instance with custom configuration
    syncer = BorgBalanceSyncer(supabase_client=supabase_client)

    # Initialize Westend adapter (optional, done automatically if needed)
    westend_ok = await syncer.initialize_westend_adapter()
    print(f"🔌 Westend adapter initialized: {westend_ok}")

    # Sync all borgs using the class method
    print("🔄 Syncing all borgs using class method...")
    result = await syncer.sync_all_borg_balances(
        batch_size=3,
        max_borgs=1,  # Just one for demo
        verbose=True
    )

    print(f"📊 Result: {result['successful_syncs']} successful, {result['failed_syncs']} failed")

    # Get balance summary for a specific borg
    print("\n💰 Getting balance summary...")
    summary = await syncer.get_borg_balance_summary("borg_1763999381")
    if summary["success"]:
        balances = summary["balances"]
        print(f"💰 WND: {balances['WND']}, USDB: {balances['USDB']}")
    else:
        print(f"❌ Failed to get summary: {summary.get('error')}")


async def example_3_integration_pattern():
    """Example 3: How to integrate into other systems (like scheduled tasks)."""
    print("\n" + "="*60)
    print("📖 Example 3: Integration Pattern (for cron jobs, APIs, etc.)")
    print("="*60)

    from jam_mock.borg_balance_syncer import BorgBalanceSyncer

    # This is how you might use it in a web API endpoint or scheduled task
    async def balance_sync_endpoint():
        """Example API endpoint function."""
        try:
            syncer = BorgBalanceSyncer(supabase_client=supabase_client)

            # Perform sync without verbose output (suitable for logs)
            result = await syncer.sync_all_borg_balances(verbose=False)

            if result["success"]:
                return {
                    "status": "success",
                    "synced_borgs": result["successful_syncs"],
                    "message": f"Successfully synced {result['successful_syncs']} borg balances"
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Unknown sync error"),
                    "details": result
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Sync failed: {str(e)}"
            }

    # Call the endpoint function
    print("🔄 Calling balance sync endpoint...")
    endpoint_result = await balance_sync_endpoint()
    print(f"📊 Endpoint result: {endpoint_result}")


async def main():
    """Run all examples."""
    print("🚀 Borg Balance Syncer - Usage Examples")
    print("Demonstrating composable functions for other Python files")

    if not supabase_client:
        print("❌ Cannot run examples without Supabase client")
        return

    await example_1_convenience_functions()
    await example_2_class_based()
    await example_3_integration_pattern()

    print("\n" + "="*60)
    print("✅ All examples completed!")
    print("📚 The borg_balance_syncer module is now available for import in any Python file")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())