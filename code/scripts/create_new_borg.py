#!/usr/bin/env python3
"""
Create New Borg Script
Creates a new borg with Westend address, stores in Supabase with address as primary key,
stores keypair in keyring, and verifies private key access.
"""

import os
import asyncio
import sys
import uuid
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from jam_mock.borg_address_manager_address_primary import BorgAddressManagerAddressPrimary
from jam_mock.demo_audit_logger import DemoAuditLogger
from security.keyring_service import KeyringService
from substrateinterface import Keypair
from jam_mock.westend_adapter import WestendAdapter


async def create_new_borg(borg_id: str = None, dna_hash: str = None) -> dict:
    """
    Create a new borg with full security integration.
    
    Args:
        borg_id: Optional borg identifier (generated if None)
        dna_hash: Optional DNA hash (generated if None)
    
    Returns:
        Creation result with success status and borg details
    """
    westend = WestendAdapter(rpc_url="wss://westend-rpc.polkadot.io")
    try:
        # Generate borg_id if not provided
        if not borg_id:
            borg_id = f"borg-{uuid.uuid4().hex[:8]}"
        
        # Generate DNA hash if not provided (simplified for demo)
        if not dna_hash:
            dna_hash = uuid.uuid4().hex * 2  # 64 characters
        
        print(f"🚀 Creating new borg: {borg_id}")
        print(f"   DNA Hash: {dna_hash[:16]}...")
        
        # Initialize components
        audit_logger = DemoAuditLogger()
        address_manager = BorgAddressManagerAddressPrimary(audit_logger=audit_logger)
        
        # Register borg (this creates keypair, stores in keyring and DB)
        result = address_manager.register_borg_address(
            borg_id=borg_id,
            dna_hash=dna_hash,
            creator_signature=None,  # No creator for new borgs
            creator_public_key=None
        )
        
        if not result.get("success"):
            return result
        
        address = result["address"]
        print(f"✅ Borg created successfully!")
        print(f"   Address: {address}")
        print(f"   Storage: {result['storage_method']}")
        
        # Verify keypair access
        print(f"\n🔍 Verifying private key access...")
        keypair = address_manager.get_borg_keypair(address)
        
        if not keypair:
            return {
                "success": False,
                "error": "Failed to retrieve keypair from keyring",
                "borg_id": borg_id,
                "address": address
            }
        
        # Verify keypair integrity
        if keypair.ss58_address != address:
            return {
                "success": False,
                "error": f"Keypair address mismatch: expected {address}, got {keypair.ss58_address}",
                "borg_id": borg_id,
                "address": address
            }
        
        print(f"✅ Private key access verified!")
        print(f"   Public key: {keypair.public_key.hex()[:16]}...")
        print(f"   Address matches: {keypair.ss58_address == address}")
        
        # Verify database storage
        print(f"\n📊 Verifying database storage...")
        stored_borg_id = address_manager.get_borg_id(address)
        stored_address = address_manager.get_borg_address(borg_id)
        
        if stored_borg_id != borg_id:
            return {
                "success": False,
                "error": f"Database borg_id mismatch: expected {borg_id}, got {stored_borg_id}",
                "borg_id": borg_id,
                "address": address
            }
        
        if stored_address != address:
            return {
                "success": False,
                "error": f"Database address mismatch: expected {address}, got {stored_address}",
                "borg_id": borg_id,
                "address": address
            }
        
        print(f"✅ Database storage verified!")
        print(f"   Borg ID lookup: {stored_borg_id}")
        print(f"   Address lookup: {stored_address}")
        
        # Sync actual balances from blockchain
        print(f"\n💰 Syncing balances from blockchain...")
        
        # Sync WND balance
        wnd_balance = await address_manager.sync_address_balance_from_blockchain(address, westend, "WND")
        print(f"   WND balance synced: {wnd_balance} planck ({wnd_balance / (10**12):.6f} WND)")
        
        # Sync USDB balance (0 for new borgs)
        usdb_balance = await address_manager.sync_address_balance_from_blockchain(address, westend, "USDB")
        print(f"   USDB balance synced: {usdb_balance}")
        
        return {
            "success": True,
            "borg_id": borg_id,
            "address": address,
            "dna_hash": dna_hash,
            "storage_method": result["storage_method"],
            "created_at": datetime.utcnow().isoformat(),
            "keypair_verified": True,
            "database_verified": True,
            "balances_synced": True,
            "wnd_balance_planck": wnd_balance,
            "usdb_balance": usdb_balance
        }
    
    except Exception as e:
        error_msg = f"Failed to create borg: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "borg_id": borg_id
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a new borg")
    parser.add_argument("--borg-id", help="Borg identifier (auto-generated if not provided)")
    parser.add_argument("--dna-hash", help="DNA hash (auto-generated if not provided)")
    
    args = parser.parse_args()
    
    result = asyncio.run(create_new_borg(borg_id=args.borg_id, dna_hash=args.dna_hash))
    
    if result["success"]:
        print("\n🎉 Borg creation completed successfully!")
        print(f"   Borg ID: {result['borg_id']}")
        print(f"   Address: {result['address']}")
        print(f"   DNA Hash: {result['dna_hash'][:16]}...")
        print(f"   Storage: {result['storage_method']}")
        print(f"   Keypair Verified: {result['keypair_verified']}")
        print(f"   Database Verified: {result['database_verified']}")
        print(f"   Balances Synced: {result.get('balances_synced', False)}")
        if 'wnd_balance_planck' in result:
            print(f"   WND Balance: {result['wnd_balance_planck']} planck ({result['wnd_balance_planck'] / (10**12):.6f} WND)")
        if 'usdb_balance' in result:
            print(f"   USDB Balance: {result['usdb_balance']}")
        return 0
    else:
        print(f"\n❌ Borg creation failed: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
