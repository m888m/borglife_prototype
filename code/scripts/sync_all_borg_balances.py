#!/usr/bin/env python3
"""
Sync All Borg Balances Script
Syncs actual WND balances from Westend blockchain for all borgs in Supabase.

This script demonstrates usage of the composable borg_balance_syncer module.
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Initialize Supabase client for the script
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.borglife")
    load_dotenv(dotenv_path=env_path)

    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")

    if supabase_url and supabase_key:
        supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized for balance sync")
    else:
        supabase_client = None
        print("⚠️  Supabase credentials not found - balance sync will fail")

except Exception as e:
    supabase_client = None
    print(f"⚠️  Failed to initialize Supabase client: {e}")

# Import composable functions from the module
from jam_mock.borg_balance_syncer import sync_all_borg_balances, sync_single_borg_balance


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync all borg balances from Westend blockchain")
    parser.add_argument("--batch-size", type=int, default=10,
                       help="Number of borgs to process in each batch")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be synced without making changes")
    parser.add_argument("--max-borgs", type=int,
                       help="Maximum number of borgs to process (for testing)")
    parser.add_argument("--borg-id", help="Sync balance for a specific borg only")

    args = parser.parse_args()

    if args.borg_id:
        # Sync single borg
        result = asyncio.run(sync_single_borg_balance(
            args.borg_id,
            supabase_client=supabase_client
        ))
    else:
        # Sync all borgs
        result = asyncio.run(sync_all_borg_balances(
            supabase_client=supabase_client,
            batch_size=args.batch_size,
            max_borgs=args.max_borgs,
            verbose=not args.dry_run  # Less verbose for dry runs
        ))

    if result["success"]:
        print("\n🎉 Balance synchronization completed successfully!")
        if args.borg_id:
            print(f"   Borg: {result['borg_id']}")
            print(f"   Address: {result['address']}")
            if 'balance_wnd' in result:
                print(f"   Balance: {result['balance_planck']} planck ({result['balance_wnd']:.6f} WND)")
        else:
            print(f"   Processed: {result['processed']}")
            print(f"   Successful: {result['successful_syncs']}")
        return 0
    else:
        print(f"\n❌ Balance synchronization failed: {result.get('error', 'Unknown error')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())