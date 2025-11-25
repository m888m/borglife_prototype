#!/usr/bin/env python3
"""
Check Supabase Borgs Script
Connects to Supabase and checks the contents of the borg_addresses table.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load Supabase credentials
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.borglife")
    load_dotenv(dotenv_path=env_path)

    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")

    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
    else:
        print("❌ Missing Supabase credentials")
        sys.exit(1)

except Exception as e:
    print(f"❌ Failed to connect to Supabase: {e}")
    sys.exit(1)


def check_borg_addresses():
    """Check all records in borg_addresses table."""
    print("\n🔍 Checking borg_addresses table...")

    try:
        result = supabase.table("borg_addresses").select("*").execute()
        borgs = result.data

        print(f"📊 Found {len(borgs)} borg(s) in database")

        if borgs:
            print("\n📋 Borg Details:")
            for i, borg in enumerate(borgs, 1):
                print(f"\n{i}. Borg ID: {borg.get('borg_id', 'N/A')}")
                print(f"   Address: {borg.get('substrate_address', 'N/A')}")
                print(f"   DNA Hash: {borg.get('dna_hash', 'N/A')[:16]}..." if borg.get('dna_hash') else "   DNA Hash: N/A")
                print(f"   Created: {borg.get('created_at', 'N/A')}")
                print(f"   Anchoring Status: {borg.get('anchoring_status', 'N/A')}")
        else:
            print("   No borgs found in the table")

        return borgs

    except Exception as e:
        print(f"❌ Failed to query borg_addresses: {e}")
        return []


def check_borg_balances():
    """Check all records in borg_balances table."""
    print("\n💰 Checking borg_balances table...")

    try:
        result = supabase.table("borg_balances").select("*").execute()
        balances = result.data

        print(f"📊 Found {len(balances)} balance record(s)")

        if balances:
            print("\n📋 Balance Details:")
            for i, balance in enumerate(balances, 1):
                address = balance.get('substrate_address', 'N/A')
                currency = balance.get('currency', 'N/A')
                amount = balance.get('balance_wei', 0)
                print(f"\n{i}. Address: {address[:16]}...")
                print(f"   Currency: {currency}")
                print(f"   Balance: {amount} wei/planck")
                if currency == "WND":
                    print(f"   Balance: {amount / (10**12):.6f} WND")
                print(f"   Last Updated: {balance.get('last_updated', 'N/A')}")
        else:
            print("   No balance records found")

        return balances

    except Exception as e:
        print(f"❌ Failed to query borg_balances: {e}")
        return []


def main():
    """Main function."""
    print("🔌 Supabase Borg Database Check")
    print("=" * 50)

    borgs = check_borg_addresses()
    balances = check_borg_balances()

    print("\n" + "=" * 50)
    print("📈 Summary:")
    print(f"   Borg Addresses: {len(borgs)}")
    print(f"   Balance Records: {len(balances)}")

    if borgs:
        print("✅ Borgs exist in database - ready for balance sync!")
    else:
        print("ℹ️  No borgs in database yet - create some first")


if __name__ == "__main__":
    main()