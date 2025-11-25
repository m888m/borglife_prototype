#!/usr/bin/env python3
"""
Store Borg Metadata in Supabase
Store metadata for a newly created borg in Supabase tables.
Usage: python store_borg_metadata.py <borg_id> <address> <dna_hash>
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.borglife"))

def main():
    parser = argparse.ArgumentParser(description="Store borg metadata in Supabase")
    parser.add_argument("borg_id", help="Unique borg identifier")
    parser.add_argument("address", help="Westend substrate address")
    parser.add_argument("dna_hash", help="Borg's DNA hash (64-character hex)")

    args = parser.parse_args()

    borg_id = args.borg_id
    address = args.address
    dna_hash = args.dna_hash

    print("📊 Storing borg metadata in Supabase...")
    print(f"   Borg ID: {borg_id}")
    print(f"   Address: {address}")
    print(f"   DNA Hash: {dna_hash}")

    # Load Supabase credentials
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("❌ Missing Supabase credentials in .env.borglife")
        return False

    supabase: Client = create_client(url, key)

    try:
        # Prepare address record
        address_record = {
            "substrate_address": address,
            "borg_id": borg_id,
            "dna_hash": dna_hash,
            "keypair_encrypted": "stored_in_keyring",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_sync": datetime.now(timezone.utc).isoformat(),
        }

        print(f"Storing address record for {borg_id}...")

        # Insert address record
        result = supabase.table("borg_addresses").upsert(
            address_record,
            on_conflict="substrate_address"
        ).execute()

        print("✅ Address record stored successfully")

        # Initialize balance records
        for currency in ["WND", "USDB"]:
            balance_record = {
                "substrate_address": address,
                "currency": currency,
                "balance_wei": 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            supabase.table("borg_balances").upsert(
                balance_record,
                on_conflict="substrate_address,currency"
            ).execute()

            print(f"✅ Balance record initialized for {currency}")

        print("✅ All metadata stored successfully!")

        return True

    except Exception as e:
        print(f"❌ Failed to store metadata: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)