#!/usr/bin/env python3
"""
USDB Asset Manager Module
Composable functions for creating and managing USDB stablecoin on Westend Asset Hub.

This module provides reusable functions for USDB asset operations that can be
imported and used by other Python modules without script-specific initialization.
"""

import asyncio
import os
import sys
from typing import Optional

import keyring
from substrateinterface import Keypair, SubstrateInterface


class USDBAssetError(Exception):
    """Raised when USDB asset operations fail."""


class USDBAssetManager:
    """
    Composable USDB asset manager for Westend Asset Hub.

    Provides methods to create, configure, and manage USDB stablecoin assets.
    Designed for reuse across different scripts and modules.
    """

    def __init__(
        self,
        substrate: Optional[SubstrateInterface] = None,
        admin_keypair: Optional[Keypair] = None,
        rpc_url: Optional[str] = None,
        dispenser_address: Optional[str] = None,
    ):
        """
        Initialize the USDB asset manager.

        Args:
            substrate: SubstrateInterface instance (created if None)
            admin_keypair: Admin keypair for asset operations (created if None)
            rpc_url: WebSocket URL for Westend Asset Hub RPC
            dispenser_address: Dispenser account address (derived from keypair if None)
        """
        self.rpc_url = rpc_url or os.getenv(
            "WESTEND_RPC_URL", "wss://westend-asset-hub-rpc.polkadot.io"
        )
        self.substrate = substrate or self._initialize_substrate()
        self.admin_keypair = admin_keypair or self._initialize_keypair()
        self.dispenser_address = dispenser_address or self.admin_keypair.ss58_address

        # Asset configuration
        self.asset_name = "USDBorglifeStablecoin"
        self.asset_symbol = "USDB"
        self.asset_decimals = 12
        self.initial_supply = 1_000_000 * (10**self.asset_decimals)  # 1M USDB in planck units

    def _initialize_substrate(self) -> SubstrateInterface:
        """Initialize SubstrateInterface with error handling."""
        try:
            substrate = SubstrateInterface(url=self.rpc_url, ss58_format=42)
            print(f"✅ Substrate connected - Block: {substrate.get_block_number(None)}")
            try:
                props = substrate.query("System", "Properties")
                print(f"✅ System Properties: {props.value}")
            except Exception as prop_e:
                print(f"⚠️ System.Properties query failed (non-critical): {prop_e}")
            return substrate
        except Exception as e:
            print(f"❌ SubstrateInterface failed: {e}")
            import traceback
            traceback.print_exc()
            raise USDBAssetError(f"Failed to initialize SubstrateInterface: {e}")

    def _initialize_keypair(self) -> Keypair:
        """Initialize admin keypair from keyring."""
        private_key_hex = keyring.get_password("borglife-dispenser", "private_key")
        if not private_key_hex:
            raise USDBAssetError("Dispenser private key not found in keyring")
        return Keypair(private_key=bytes.fromhex(private_key_hex), ss58_format=42)

    async def create_asset(self) -> int:
        """
        Create USDB asset using Assets.create extrinsic.

        Returns:
            Asset ID of the created asset

        Raises:
            USDBAssetError: If asset creation fails
        """
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

            extrinsic = self.substrate.create_signed_extrinsic(
                call=call, keypair=self.admin_keypair
            )
            receipt = self.substrate.submit_extrinsic(
                extrinsic, wait_for_inclusion=True
            )

            if receipt.is_success:
                print(f"✅ Asset created successfully! Asset ID: {next_asset_id}")
                print(f"   Transaction hash: {receipt.extrinsic_hash}")
                print(f"   Block: {receipt.block_number}")
                return next_asset_id
            else:
                raise USDBAssetError(f"Asset creation failed: {receipt.error_message}")

        except USDBAssetError:
            raise
        except Exception as e:
            raise USDBAssetError(f"Asset creation error: {e}")

    async def set_metadata(self, asset_id: int) -> bool:
        """
        Set asset metadata using Assets.set_metadata extrinsic.

        Args:
            asset_id: Asset ID to set metadata for

        Returns:
            True if successful

        Raises:
            USDBAssetError: If metadata setting fails
        """
        try:
            print(f"🏷️ Setting metadata for asset {asset_id}...")

            call = self.substrate.compose_call(
                call_module="Assets",
                call_function="set_metadata",
                call_params={
                    "id": asset_id,
                    "name": self.asset_name.encode(),
                    "symbol": self.asset_symbol.encode(),
                    "decimals": self.asset_decimals,
                },
            )

            extrinsic = self.substrate.create_signed_extrinsic(
                call=call, keypair=self.admin_keypair
            )
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
                raise USDBAssetError(f"Metadata setting failed: {receipt.error_message}")

        except USDBAssetError:
            raise
        except Exception as e:
            raise USDBAssetError(f"Metadata setting error: {e}")

    async def mint_initial_supply(self, asset_id: int) -> bool:
        """
        Mint initial supply using Assets.mint extrinsic.

        Args:
            asset_id: Asset ID to mint supply for

        Returns:
            True if successful

        Raises:
            USDBAssetError: If minting fails
        """
        try:
            print(f"💰 Minting initial supply for asset {asset_id}...")

            call = self.substrate.compose_call(
                call_module="Assets",
                call_function="mint",
                call_params={
                    "id": asset_id,
                    "beneficiary": self.admin_keypair.ss58_address,
                    "amount": self.initial_supply,
                },
            )

            extrinsic = self.substrate.create_signed_extrinsic(
                call=call, keypair=self.admin_keypair
            )
            receipt = self.substrate.submit_extrinsic(
                extrinsic, wait_for_inclusion=True, tip=10**10
            )

            if receipt.is_success:
                print("✅ Initial supply minted successfully!")
                print(f"   Amount: {self.initial_supply:,} planck units")
                print(f"   Equivalent: {self.initial_supply / (10 ** self.asset_decimals):,} USDB")
                print(f"   Minted to: {self.admin_keypair.ss58_address}")
                return True
            else:
                raise USDBAssetError(f"Minting failed: {receipt.error_message}")

        except USDBAssetError:
            raise
        except Exception as e:
            raise USDBAssetError(f"Minting error: {e}")
    async def mint_usdb(self, asset_id: int, beneficiary: str, amount: int) -> bool:
        """
        Mint USDB tokens using Assets.mint extrinsic.

        Args:
            asset_id: Asset ID to mint for
            beneficiary: Address to mint to
            amount: Amount in planck units

        Returns:
            True if successful

        Raises:
            USDBAssetError: If minting fails
        """
        try:
            print(f"💰 Minting {amount} planck USDB to {beneficiary[:20]}...")

            call = self.substrate.compose_call(
                call_module="Assets",
                call_function="mint",
                call_params={
                    "id": asset_id,
                    "beneficiary": beneficiary,
                    "amount": amount,
                },
            )

            extrinsic = self.substrate.create_signed_extrinsic(
                call=call, keypair=self.admin_keypair
            )
            receipt = self.substrate.submit_extrinsic(
                extrinsic, wait_for_inclusion=True
            )

            if receipt.is_success:
                print("✅ USDB minted successfully!")
                print(f"   Amount: {amount:,} planck units")
                print(f"   Equivalent: {amount / (10 ** self.asset_decimals):,} USDB")
                print(f"   Minted to: {beneficiary}")
                print(f"   Tx: {receipt.extrinsic_hash}")
                print(f"   Block: {receipt.block_number}")
                return True
            else:
                raise USDBAssetError(f"Minting failed: {receipt.error_message}")

        except USDBAssetError:
            raise
        except Exception as e:
            raise USDBAssetError(f"Minting error: {e}")

    async def verify_asset(self, asset_id: int) -> bool:
        """
        Verify asset creation by querying on-chain state.

        Args:
            asset_id: Asset ID to verify

        Returns:
            True if verification successful

        Raises:
            USDBAssetError: If verification fails
        """
        try:
            print(f"🔍 Verifying asset {asset_id}...")

            # Query asset metadata
            metadata = self.substrate.query(
                module="Assets", storage_function="Metadata", params=[asset_id]
            )

            if metadata.value:
                name_raw = metadata.value.get("name", b"")
                name_str = name_raw.decode("utf-8") if isinstance(name_raw, bytes) else str(name_raw)
                symbol_raw = metadata.value.get("symbol", b"")
                symbol_str = symbol_raw.decode("utf-8") if isinstance(symbol_raw, bytes) else str(symbol_raw)
                decimals = int(metadata.value.get("decimals", 0))

                print("✅ Asset metadata verified:")
                print(f"   Name: {name_str}")
                print(f"   Symbol: {symbol_str}")
                print(f"   Decimals: {decimals}")
            else:
                raise USDBAssetError("Asset metadata not found")

            # Query admin balance
            balance = self.substrate.query(
                module="Assets",
                storage_function="Account",
                params=[asset_id, self.admin_keypair.ss58_address],
            )

            if balance.value:
                balance_raw = balance.value.get("balance", "0")
                admin_balance = int(balance_raw) if isinstance(balance_raw, (str, int)) else 0
                print("✅ Admin balance verified:")
                print(f"   Balance: {admin_balance:,} planck units")
                print(f"   Equivalent: {admin_balance / (10 ** self.asset_decimals):,} USDB")
            else:
                print("❌ Admin balance not found")
                return False

            return True

        except USDBAssetError:
            raise
        except Exception as e:
            raise USDBAssetError(f"Verification error: {e}")

    def save_asset_config(self, asset_id: int) -> bool:
        """
        Save asset ID to configuration file.

        Args:
            asset_id: Asset ID to save

        Returns:
            True if successful

        Raises:
            USDBAssetError: If saving fails
        """
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", ".borglife_config")

            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            config[key] = value

            config["USDB_ASSET_ID"] = str(asset_id)

            with open(config_path, "w") as f:
                for key, value in config.items():
                    f.write(f"{key}={value}\n")

            print(f"✅ Asset ID {asset_id} saved to .borglife_config")
            return True

        except Exception as e:
            raise USDBAssetError(f"Config save error: {e}")

    async def run_creation(self) -> bool:
        """
        Run the complete USDB asset creation process.

        Returns:
            True if all steps successful
        """
        print("🚀 Starting USDB Asset Creation on Westend Asset Hub")
        print("=" * 60)

        try:
            # Create asset
            print("\n📋 Creating USDB asset...")
            asset_id = await self.create_asset()

            # Set metadata
            print("\n📋 Setting asset metadata...")
            await self.set_metadata(asset_id)

            # Mint supply
            print("\n📋 Minting initial supply...")
            await self.mint_initial_supply(asset_id)

            # Verify
            print("\n📋 Verifying asset creation...")
            await self.verify_asset(asset_id)

            # Save config
            print("\n📋 Saving configuration...")
            self.save_asset_config(asset_id)

            print("\n" + "=" * 60)
            print("🎉 USDB Asset Creation Complete!")
            print(f"   Asset ID: {asset_id}")
            print(f"   Asset: {self.asset_name} ({self.asset_symbol})")
            print(f"   Supply: {self.initial_supply / (10 ** self.asset_decimals):,} USDB")
            print("\nNext steps:")
            print("1. Verify asset on Subscan")
            print("2. Proceed to address management implementation")
            return True

        except USDBAssetError as e:
            print(f"\n❌ USDB Asset Creation Failed: {e}")
            print("Check the errors above and retry.")
            return False


# Convenience functions for backward compatibility and easy importing
async def create_usdb_asset(
    substrate: Optional[SubstrateInterface] = None,
    admin_keypair: Optional[Keypair] = None,
    rpc_url: Optional[str] = None,
) -> int:
    """
    Convenience function to create USDB asset.

    Args:
        substrate: SubstrateInterface instance
        admin_keypair: Admin keypair
        rpc_url: RPC URL

    Returns:
        Asset ID
    """
    manager = USDBAssetManager(
        substrate=substrate, admin_keypair=admin_keypair, rpc_url=rpc_url
    )
    return await manager.create_asset()


async def set_usdb_metadata(
    asset_id: int,
    substrate: Optional[SubstrateInterface] = None,
    admin_keypair: Optional[Keypair] = None,
    rpc_url: Optional[str] = None,
) -> bool:
    """
    Convenience function to set USDB metadata.

    Args:
        asset_id: Asset ID
        substrate: SubstrateInterface instance
        admin_keypair: Admin keypair
        rpc_url: RPC URL

    Returns:
        True if successful
    """
    manager = USDBAssetManager(
        substrate=substrate, admin_keypair=admin_keypair, rpc_url=rpc_url
    )
    return await manager.set_metadata(asset_id)


async def mint_usdb_supply(
    asset_id: int,
    substrate: Optional[SubstrateInterface] = None,
    admin_keypair: Optional[Keypair] = None,
    rpc_url: Optional[str] = None,
) -> bool:
    """
    Convenience function to mint USDB supply.

    Args:
        asset_id: Asset ID
        substrate: SubstrateInterface instance
        admin_keypair: Admin keypair
        rpc_url: RPC URL

    Returns:
        True if successful
    """
    manager = USDBAssetManager(
        substrate=substrate, admin_keypair=admin_keypair, rpc_url=rpc_url
    )
    return await manager.mint_initial_supply(asset_id)


async def verify_usdb_asset(
    asset_id: int,
    substrate: Optional[SubstrateInterface] = None,
    admin_keypair: Optional[Keypair] = None,
    rpc_url: Optional[str] = None,
) -> bool:
    """
    Convenience function to verify USDB asset.

    Args:
        asset_id: Asset ID
        substrate: SubstrateInterface instance
        admin_keypair: Admin keypair
        rpc_url: RPC URL

    Returns:
        True if successful
    """
    manager = USDBAssetManager(
        substrate=substrate, admin_keypair=admin_keypair, rpc_url=rpc_url
    )
    return await manager.verify_asset(asset_id)


async def run_usdb_creation(
    substrate: Optional[SubstrateInterface] = None,
    admin_keypair: Optional[Keypair] = None,
    rpc_url: Optional[str] = None,
) -> bool:
    """
    Convenience function to run complete USDB creation.

    Args:
        substrate: SubstrateInterface instance
        admin_keypair: Admin keypair
        rpc_url: RPC URL

    Returns:
        True if successful
    """
    manager = USDBAssetManager(
        substrate=substrate, admin_keypair=admin_keypair, rpc_url=rpc_url
    )
    return await manager.run_creation()


async def main():
    """Main entry point for script execution."""
    try:
        success = await run_usdb_creation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Asset creation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
