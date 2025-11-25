#!/usr/bin/env python3
"""
Live Westend Dispenser-Borg Test
Dynamically loads borg address from Supabase and performs live WND transfer test.
Usage: python live_dispenser_borg_test.py --borg-index 0 --amount 1.5
"""

import argparse
import asyncio
from datetime import datetime
import os
import sys
import keyring
from decimal import Decimal
from dotenv import load_dotenv
from supabase import create_client, Client
from substrateinterface import Keypair
from jam_mock.westend_adapter import WestendAdapter
# from jam_mock.transaction_logger import TransactionLogger  # Commented out for now

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.borglife"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def get_borg_address_from_supabase(supabase: Client, borg_index: int) -> str:
    """Get borg address from Supabase by index (0-based, ordered by creation time)."""
    try:
        result = supabase.table("borg_addresses").select("substrate_address").order("created_at", desc=True).execute()
        if result.data and len(result.data) > borg_index:
            return result.data[borg_index]["substrate_address"]
        else:
            raise ValueError(f"No borg found at index {borg_index}")
    except Exception as e:
        raise ValueError(f"Failed to get borg address from Supabase: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Live Westend dispenser-borg transfer test")
    parser.add_argument("--borg-index", type=int, default=0, help="Index of borg to use (0-based, ordered by creation time)")
    parser.add_argument("--amount", type=float, default=1.0, help="Amount of WND to transfer (default: 1.0)")
    args = parser.parse_args()

    print(f"🚀 Starting live Westend dispenser-borg test (borg index: {args.borg_index}, amount: {args.amount} WND)...")

    # Load Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("❌ Missing Supabase credentials")
        return False

    supabase: Client = create_client(url, key)

    # Step 1: Load dispenser keypair from keyring
    dispenser_service = "borglife-dispenser"
    dispenser_username = "private_key"
    encrypted_priv_d = keyring.get_password(dispenser_service, dispenser_username)
    if not encrypted_priv_d:
        print(f"❌ Failed to access dispenser private key from keyring")
        print(f"   Service: {dispenser_service}")
        print(f"   Username: {dispenser_username}")
        return False

    dispenser_kp = Keypair.create_from_private_key(bytes.fromhex(encrypted_priv_d), ss58_format=42)
    print(f"✅ Dispenser loaded: {dispenser_kp.ss58_address}")
    if dispenser_kp.ss58_address != "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD":
        print("⚠️  Dispenser address mismatch!")

    # Step 2: Dynamically load borg address from Supabase
    try:
        borg_addr = get_borg_address_from_supabase(supabase, args.borg_index)
        print(f"✅ Borg address loaded from Supabase: {borg_addr}")
    except ValueError as e:
        print(f"❌ {e}")
        return False

    # Step 3: Load borg keypair from keyring using address-based service
    borg_service_name = f"borglife-address-{borg_addr}"
    encrypted_priv_b = keyring.get_password(borg_service_name, "private_key")
    if encrypted_priv_b:
        borg_kp = Keypair.create_from_private_key(bytes.fromhex(encrypted_priv_b), ss58_format=42)
        print(f"✅ Borg keypair loaded: {borg_kp.ss58_address}")
        if borg_kp.ss58_address != borg_addr:
            print("⚠️  Borg address mismatch in keyring!")
    else:
        print(f"⚠️  Borg keypair not found in keyring (service: {borg_service_name})")
        print("   Transfer will proceed without borg keypair (address only needed)")

    # Step 4: Establish live Westend connection
    print("\n🔌 Connecting to Westend...")
    adapter = WestendAdapter(rpc_url="wss://westend-rpc.polkadot.io")
    health = await adapter.health_check()
    print("Westend health:", health)
    if health.get("status") != "healthy":
        print("❌ Westend connection unhealthy")
        return False

    # Step 5: Send args.amount WND live transaction
    print(f"\n💸 Sending {args.amount} WND from dispenser to borg...")
    print(f"From: {dispenser_kp.ss58_address}")
    print(f"To: {borg_addr}")
    transfer_result = await adapter.transfer_from_dispenser(
        from_address=dispenser_kp.ss58_address,
        to_borg_id=borg_addr,
        amount=Decimal(str(args.amount)),
        dispenser_keypair=dispenser_kp
    )
    print("Transfer result:", transfer_result)

    if not transfer_result.get("success"):
        print("❌ Transfer failed:", transfer_result.get("error"))
        return False

    tx_hash = transfer_result.get("transaction_hash")
    print(f"✅ Transaction sent: {tx_hash}")
    print(f"   Explorer: https://westend.subscan.io/extrinsic/{tx_hash}")

    # Step 6: Log transaction in Supabase
    print("\n📊 Logging to Supabase transfer_transactions...")
    data = {
        "tx_hash": tx_hash,
        "from_addr": dispenser_kp.ss58_address,
        "to_addr": borg_addr,
        "amount": float(args.amount),
        "timestamp": datetime.utcnow().isoformat(),
        "network": "westend"
    }
    insert_res = supabase.table("transfer_transactions").insert(data).execute()
    print("Supabase insert result:", insert_res)
    
    if insert_res.data:
        print("✅ Full test SUCCESSFUL!")
        print(f"Tx: {tx_hash}")
        print(f"Borg funded: {borg_addr}")
        return True
    else:
        print("❌ Transaction logging failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)