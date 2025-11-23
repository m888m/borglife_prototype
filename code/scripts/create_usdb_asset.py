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

import asyncio
import os
import sys
import time
from decimal import Decimal
from typing import Any, Dict, Optional

import keyring
from substrateinterface import Keypair, SubstrateInterface

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Note: SecureKeyStorage and AdvancedKeypairManager imports removed
# as they are not needed for basic USDB asset creation


class USDBAssetCreator:
    """Creates USDB stablecoin on Westend Asset Hub."""

    def __init__(self):
        # Use live Westend Asset Hub RPC endpoint
        self.rpc_url = os.getenv(
            "WESTEND_RPC_URL", "wss://westend-asset-hub-rpc.polkadot.io"
        )

        # Load dispenser private key from keyring service
        private_key_hex = keyring.get_password("borglife-dispenser", "private_key")
        if not private_key_hex:
            raise ValueError("Dispenser private key not found in keyring")

        # Convert hex to bytes and create keypair
        self.admin_keypair = Keypair(
            private_key=bytes.fromhex(private_key_hex), ss58_format=42
        )

        try:
            self.substrate = SubstrateInterface(url=self.rpc_url, ss58_format=42)
            print(
                f"✅ Substrate connected - Block: {self.substrate.get_block_number(None)}"
            )
            try:
                props = self.substrate.query("System", "Properties")
                print(f"✅ System Properties: {props.value}")
            except Exception as prop_e:
                print(f"⚠️ System.Properties query failed (non-critical): {prop_e}")
        except Exception as e:
            print(f"❌ SubstrateInterface failed: {e}")
            import traceback

            traceback.print_exc()
            raise ValueError(f"Failed to initialize SubstrateInterface: {e}")

        self.dispenser_address = self.admin_keypair.ss58_address

        # Asset configuration
        self.asset_id = None  # Will be assigned by chain
        self.asset_name = "USDBorglifeStablecoin"
        self.asset_symbol = "USDB"
        self.asset_decimals = 12
        self.initial_supply = 1_000_000 * (
            10**self.asset_decimals
        )  # 1M USDB in planck units

    async def create_asset(self) -> bool:
        """Create USDB asset using Assets.create extrinsic (signed account)."""
        try:
            print("🏭 Creating USDB asset on Westend Asset Hub...")

            # Query next available asset ID
            next_asset_id_result = self.substrate.query(
                module="Assets", storage_function="NextAssetId"
            )
            next_asset_id = next_asset_id_result.value

            print(f"📋 Next available asset ID: {next_asset_id}")

            # Create asset with dispenser as admin
            call = self.substrate.compose_call(
                call_module="Assets",
                call_function="create",
                call_params={
                    "id": next_asset_id,
                    "admin": self.admin_keypair.ss58_address,
                    "is_sufficient": True,
                    "min_balance": 1,
                },
            )

            # Create signed extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call, keypair=self.admin_keypair
            )

            # Submit and wait for inclusion
            receipt = self.substrate.submit_extrinsic(
                extrinsic, wait_for_inclusion=True
            )

            if receipt.is_success:
                self.asset_id = next_asset_id
                print(f"✅ Asset created successfully! Asset ID: {self.asset_id}")
                print(f"   Transaction hash: {receipt.extrinsic_hash}")
                print(f"   Block: {receipt.block_number}")
                return True
            else:
                print(f"❌ Asset creation failed: {receipt.error_message}")
                return False

        except Exception as e:
            print(f"❌ Asset creation error: {e}")
            return False

    def _extract_asset_id_from_receipt(self, receipt) -> Optional[int]:
        """Extract asset ID from successful receipt."""
        # Asset ID is predetermined from NextAssetId query
        return self.asset_id

    async def set_metadata(self) -> bool:
        """Set asset metadata using Assets.set_metadata extrinsic."""
        if not self.asset_id:
            print("❌ No asset ID available")
            return False

        try:
            print(f"🏷️  Setting metadata for asset {self.asset_id}...")

            # Set metadata
            call = self.substrate.compose_call(
                call_module="Assets",
                call_function="set_metadata",
                call_params={
                    "id": self.asset_id,
                    "name": self.asset_name.encode(),
                    "symbol": self.asset_symbol.encode(),
                    "decimals": self.asset_decimals,
                },
            )

            # Create signed extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call, keypair=self.admin_keypair
            )

            # Submit and wait for inclusion
            receipt = self.substrate.submit_extrinsic(
                extrinsic, wait_for_inclusion=True
            )

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
        """Mint initial supply using Assets.mint extrinsic."""
        if not self.asset_id:
            print("❌ No asset ID available")
            return False

        try:
            print(f"💰 Minting initial supply for asset {self.asset_id}...")

            # Mint initial supply to admin account
            call = self.substrate.compose_call(
                call_module="Assets",
                call_function="mint",
                call_params={
                    "id": self.asset_id,
                    "beneficiary": self.admin_keypair.ss58_address,
                    "amount": self.initial_supply,
                },
            )

            # Create signed extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call, keypair=self.admin_keypair
            )

            # Submit and wait for inclusion
            receipt = self.substrate.submit_extrinsic(
                extrinsic, wait_for_inclusion=True
            )

            if receipt.is_success:
                print("✅ Initial supply minted successfully!")
                print(f"   Amount: {self.initial_supply:,} planck units")
                print(
                    f"   Equivalent: {self.initial_supply / (10 ** self.asset_decimals):,} USDB"
                )
                print(f"   Minted to: {self.admin_keypair.ss58_address}")
                return True
            else:
                print(f"❌ Minting failed: {receipt.error_message}")
                return False

        except Exception as e:
            print(f"❌ Minting error: {e}")
            return False

    async def verify_asset(self) -> bool:
        """Verify asset creation by querying on-chain state."""
        if not self.asset_id:
            print("❌ No asset ID available")
            return False

        try:
            print(f"🔍 Verifying asset {self.asset_id}...")

            # Query asset metadata
            metadata = self.substrate.query(
                module="Assets", storage_function="Metadata", params=[self.asset_id]
            )

            if metadata.value:
                name_raw = metadata.value.get("name", b"")
                name_str = (
                    name_raw.decode("utf-8")
                    if isinstance(name_raw, bytes)
                    else str(name_raw)
                )
                symbol_raw = metadata.value.get("symbol", b"")
                symbol_str = (
                    symbol_raw.decode("utf-8")
                    if isinstance(symbol_raw, bytes)
                    else str(symbol_raw)
                )
                decimals = int(metadata.value.get("decimals", 0))

                print("✅ Asset metadata verified:")
                print(f"   Name: {name_str}")
                print(f"   Symbol: {symbol_str}")
                print(f"   Decimals: {decimals}")
            else:
                print("❌ Asset metadata not found")
                return False

            # Query admin balance
            balance = self.substrate.query(
                module="Assets",
                storage_function="Account",
                params=[self.asset_id, self.admin_keypair.ss58_address],
            )

            admin_balance = 0
            if balance.value:
                balance_raw = balance.value.get("balance", "0")
                admin_balance = (
                    int(balance_raw) if isinstance(balance_raw, (str, int)) else 0
                )

                print("✅ Admin balance verified:")
                print(f"   Balance: {admin_balance:,} planck units")
                print(
                    f"   Equivalent: {admin_balance / (10 ** self.asset_decimals):,} USDB"
                )
            else:
                print("❌ Admin balance not found")

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
            config_path = os.path.join(
                os.path.dirname(__file__), "..", ".borglife_config"
            )

            # Read existing config
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            config[key] = value

            # Add asset ID
            config["USDB_ASSET_ID"] = str(self.asset_id)

            # Write back
            with open(config_path, "w") as f:
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
            ("Saving configuration", lambda: self.save_asset_config()),
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
            print(
                f"   Supply: {self.initial_supply / (10 ** self.asset_decimals):,} USDB"
            )
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
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
