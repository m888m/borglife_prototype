#!/usr/bin/env python3
"""
Create USDB Stablecoin on Westend Asset Hub

Creates the USDBorglifeStablecoin asset on Westend Asset Hub using the Assets pallet.
This script handles asset creation, metadata setup, and initial supply minting.

Usage:
    python scripts/create_usdb_asset.py

Environment Variables Required:
    - WESTEND_RPC_URL: Westend RPC endpoint (default: wss://westend-asset-hub-rpc.polkadot.io)
    - ADMIN_SEED: Admin account seed phrase for asset management
"""

import os
import sys
import time
import asyncio
from typing import Dict, Any, Optional
from decimal import Decimal
from substrateinterface import SubstrateInterface, Keypair

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from jam_mock.secure_key_storage import SecureKeyStorage
from jam_mock.keypair_manager import AdvancedKeypairManager

class USDBAssetCreator:
    """Creates USDB stablecoin on Westend Asset Hub."""

    def __init__(self):
        self.rpc_url = os.getenv('WESTEND_RPC_URL', 'wss://westend-asset-hub-rpc.polkadot.io')
        self.admin_seed = os.getenv('ADMIN_SEED')

        if not self.admin_seed:
            raise ValueError("ADMIN_SEED environment variable required")

        # Initialize substrate connection
        self.substrate = SubstrateInterface(
            url=self.rpc_url,
            ss58_format=42  # Westend format
        )

        # Generate admin keypair
        self.admin_keypair = Keypair.create_from_seed(self.admin_seed)
        print(f"🔑 Admin address: {self.admin_keypair.ss58_address}")

        # Asset configuration
        self.asset_id: Optional[int] = None
        self.asset_name = "USDBorglifeStablecoin"
        self.asset_symbol = "USDB"
        self.asset_decimals = 12
        self.initial_supply = 1_000_000 * (10 ** self.asset_decimals)  # 1M USDB in planck units

    async def create_asset(self) -> bool:
        """Create the USDB asset using Assets.create extrinsic."""
        try:
            print("🏭 Creating USDB asset...")

            # Compose the create extrinsic
            call = self.substrate.compose_call(
                call_module='Assets',
                call_function='create',
                call_params={
                    'id': None,  # Let pallet assign ID
                    'admin': self.admin_keypair.ss58_address,
                    'min_balance': 1  # Minimum balance
                }
            )

            # Create signed extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call,
                keypair=self.admin_keypair
            )

            # Submit and wait for inclusion
            print("📤 Submitting asset creation extrinsic...")
            receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

            if receipt.is_success:
                # Extract asset ID from events
                self.asset_id = self._extract_asset_id_from_receipt(receipt)
                print(f"✅ Asset created successfully! Asset ID: {self.asset_id}")
                print(f"   Block: {receipt.block_hash}")
                print(f"   Transaction: {receipt.extrinsic_hash}")
                return True
            else:
                print(f"❌ Asset creation failed: {receipt.error_message}")
                return False

        except Exception as e:
            print(f"❌ Asset creation error: {e}")
            return False

    def _extract_asset_id_from_receipt(self, receipt) -> Optional[int]:
        """Extract asset ID from transaction receipt events."""
        try:
            # Look for Assets.Created event
            for event in receipt.triggered_events:
                if (event.value['module_id'] == 'Assets' and
                    event.value['event_id'] == 'Created'):
                    return int(event.value['attributes']['asset_id'])
        except Exception as e:
            print(f"Warning: Could not extract asset ID from receipt: {e}")

        return None

    async def set_metadata(self) -> bool:
        """Set asset metadata (name, symbol, decimals)."""
        if not self.asset_id:
            print("❌ No asset ID available for metadata")
            return False

        try:
            print(f"🏷️  Setting metadata for asset {self.asset_id}...")

            # Compose set_metadata extrinsic
            call = self.substrate.compose_call(
                call_module='Assets',
                call_function='set_metadata',
                call_params={
                    'asset_id': self.asset_id,
                    'name': self.asset_name.encode('utf-8'),
                    'symbol': self.asset_symbol.encode('utf-8'),
                    'decimals': self.asset_decimals
                }
            )

            # Create signed extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call,
                keypair=self.admin_keypair
            )

            # Submit and wait
            print("📤 Submitting metadata extrinsic...")
            receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

            if receipt.is_success:
                print("✅ Metadata set successfully!")
                print(f"   Name: {self.asset_name}")
                print(f"   Symbol: {self.asset_symbol}")
                print(f"   Decimals: {self.asset_decimals}")
                return True
            else:
                print(f"❌ Metadata setting failed: {receipt.error_message}")
                return False

        except Exception as e:
            print(f"❌ Metadata setting error: {e}")
            return False

    async def mint_initial_supply(self) -> bool:
        """Mint initial supply to admin account."""
        if not self.asset_id:
            print("❌ No asset ID available for minting")
            return False

        try:
            print(f"💰 Minting initial supply for asset {self.asset_id}...")

            # Compose mint extrinsic
            call = self.substrate.compose_call(
                call_module='Assets',
                call_function='mint',
                call_params={
                    'asset_id': self.asset_id,
                    'beneficiary': self.admin_keypair.ss58_address,
                    'amount': self.initial_supply
                }
            )

            # Create signed extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call,
                keypair=self.admin_keypair
            )

            # Submit and wait
            print("📤 Submitting mint extrinsic...")
            receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

            if receipt.is_success:
                print("✅ Initial supply minted successfully!")
                print(f"   Amount: {self.initial_supply:,} planck units")
                print(f"   Equivalent: {self.initial_supply / (10 ** self.asset_decimals):,} USDB")
                return True
            else:
                print(f"❌ Minting failed: {receipt.error_message}")
                return False

        except Exception as e:
            print(f"❌ Minting error: {e}")
            return False

    async def verify_asset(self) -> bool:
        """Verify asset creation via on-chain queries."""
        if not self.asset_id:
            print("❌ No asset ID to verify")
            return False

        try:
            print(f"🔍 Verifying asset {self.asset_id}...")

            # Query asset metadata
            metadata = self.substrate.query(
                module='Assets',
                storage_function='Metadata',
                params=[self.asset_id]
            )

            if metadata.value:
                print("✅ Asset metadata verified:")
                print(f"   Name: {bytes(metadata.value['name']).decode('utf-8', errors='ignore')}")
                print(f"   Symbol: {bytes(metadata.value['symbol']).decode('utf-8', errors='ignore')}")
                print(f"   Decimals: {metadata.value['decimals']}")
            else:
                print("❌ Could not retrieve asset metadata")
                return False

            # Query admin account balance
            balance = self.substrate.query(
                module='Assets',
                storage_function='Account',
                params=[self.asset_id, self.admin_keypair.ss58_address]
            )

            if balance.value:
                balance_amount = balance.value['balance']
                print("✅ Admin balance verified:")
                print(f"   Balance: {balance_amount:,} planck units")
                print(f"   Equivalent: {balance_amount / (10 ** self.asset_decimals):,} USDB")
            else:
                print("❌ Could not retrieve admin balance")
                return False

            return True

        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False

    def save_asset_config(self) -> bool:
        """Save asset ID to configuration file."""
        if not self.asset_id:
            print("❌ No asset ID to save")
            return False

        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', '.borglife_config')

            # Read existing config
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            config[key] = value

            # Add asset ID
            config['USDB_ASSET_ID'] = str(self.asset_id)

            # Write back
            with open(config_path, 'w') as f:
                for key, value in config.items():
                    f.write(f"{key}={value}\n")

            print(f"✅ Asset ID {self.asset_id} saved to .borglife_config")
            return True

        except Exception as e:
            print(f"❌ Config save error: {e}")
            return False

    async def run_creation(self) -> bool:
        """Run the complete USDB asset creation process."""
        print("🚀 Starting USDB Asset Creation on Westend Asset Hub")
        print("=" * 60)

        steps = [
            ("Creating USDB asset", self.create_asset),
            ("Setting asset metadata", self.set_metadata),
            ("Minting initial supply", self.mint_initial_supply),
            ("Verifying asset creation", self.verify_asset),
            ("Saving configuration", lambda: self.save_asset_config())
        ]

        success = True
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if asyncio.iscoroutinefunction(step_func):
                result = await step_func()
            else:
                result = step_func()

            if not result:
                success = False
                break

        print("\n" + "=" * 60)
        if success:
            print("🎉 USDB Asset Creation Complete!")
            print(f"   Asset ID: {self.asset_id}")
            print(f"   Asset: {self.asset_name} ({self.asset_symbol})")
            print(f"   Supply: {self.initial_supply / (10 ** self.asset_decimals):,} USDB")
            print("\nNext steps:")
            print("1. Verify asset on Subscan")
            print("2. Proceed to address management implementation")
        else:
            print("❌ USDB Asset Creation Failed!")
            print("Check the errors above and retry.")

        return success

async def main():
    """Main entry point."""
    try:
        creator = USDBAssetCreator()
        success = await creator.run_creation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Asset creation failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())