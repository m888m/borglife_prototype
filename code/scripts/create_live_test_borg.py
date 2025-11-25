#!/usr/bin/env python3
"""
Create Live Test Borg - Production Workflow Verification
Creates a new borg using the unified BorgCreator with full security pipeline.
"""

import time
from typing import Dict, Any

# Add code/ directory to path
import os
import sys
code_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, code_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(code_dir, ".env.borglife"))

from supabase import create_client

# Load Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")
supabase_client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

from jam_mock.borg_creator import BorgCreator

def main() -> None:
    """Main creation workflow using BorgCreator."""
    # Generate unique identifiers
    timestamp = int(time.time())
    borg_id = f"live_test_borg_{timestamp}"
    dna_content = f"live_test_dna_{timestamp}"

    print(f"🚀 Creating live test borg")
    print(f"   Borg ID: {borg_id}")
    print(f"   DNA Content: {dna_content}")
    print(f"   Supabase: {'✅' if supabase_client else '❌ Offline'}")

    if not supabase_client:
        print("⚠️  No Supabase - will skip database storage")
        return

    # Create BorgCreator instance
    creator = BorgCreator(supabase_client=supabase_client)

    # Create borg with full pipeline
    result: Dict[str, Any] = creator.create_borg(
        borg_id=borg_id,
        dna_content=dna_content
    )

    print("\n📋 Creation Result:")
    for key, value in result.items():
        print(f"   {key}: {value}")

    if result.get("success"):
        address = result["address"]
        print(f"\n✅ Borg created successfully!")
        print(f"   Address (PK): {address}")
        print(f"   Storage: {result.get('storage_method', 'unknown')}")

        # Additional verification
        borg_info = creator.get_borg_info(address)
        if borg_info:
            print("✅ Supabase metadata confirmed:")
            print(f"   PK=address: {borg_info['substrate_address']}")
            print(f"   borg_id: {borg_info['borg_id']}")
            print(f"   dna_hash: {borg_info['dna_hash'][:16]}...")
        else:
            print("❌ Supabase metadata not found!")
    else:
        print("❌ Borg creation FAILED!")
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    main()