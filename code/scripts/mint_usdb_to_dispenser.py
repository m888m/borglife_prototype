#!/usr/bin/env python3
"""
Mint USDB Tokens to Dispenser Script

Mints 1M USDB tokens to the dispenser address on Westend Asset Hub.
Uses SecureDispenser for secure key management and Asset Hub operations.
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from security.secure_dispenser import SecureDispenser


async def main():
    """Main execution function."""
    print("🚀 Starting USDB Minting to Dispenser")
    print("=" * 50)

    try:
        # Initialize dispenser
        dispenser = SecureDispenser()

        # Unlock dispenser session
        print("\n🔐 Unlocking dispenser session...")
        if not dispenser.unlock_for_session():
            print("❌ Failed to unlock dispenser")
            return False

        # Mint 1M USDB tokens
        print("\n🏭 Minting 1,000,000 USDB tokens to dispenser...")
        mint_amount = 1000000.0  # 1M USDB

        mint_result = await dispenser.mint_usdb_tokens(mint_amount)

        if mint_result["success"]:
            print("✅ USDB Minting Successful!")
            print(f"   Amount: {mint_amount:,.0f} USDB")
            print(f"   Transaction Hash: {mint_result['transaction_hash']}")
            print(f"   Block Number: {mint_result['block_number']}")
            print(f"   Asset ID: {mint_result['asset_id']}")
            print(f"   Dispenser Address: {dispenser.unlocked_keypair.ss58_address}")

            # Verify balance after minting
            print("\n🔍 Verifying dispenser balance...")
            balance = await dispenser.get_usdb_balance(
                dispenser.unlocked_keypair.ss58_address
            )
            balance_usdb = balance / (10**12)

            print(
                f"   Dispenser USDB Balance: {balance_usdb:,.0f} USDB ({balance:,} planck)"
            )

            if balance >= int(mint_amount * (10**12)):
                print("✅ Balance verification successful!")
                return True
            else:
                print("❌ Balance verification failed!")
                return False

        else:
            print(f"❌ Minting failed: {mint_result['error']}")
            return False

    except Exception as e:
        print(f"❌ Script execution failed: {e}")
        return False

    finally:
        # Always lock the session
        dispenser.lock_session()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
