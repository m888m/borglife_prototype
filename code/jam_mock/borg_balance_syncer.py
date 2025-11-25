"""
Borg Balance Syncer Module
Composable functions for syncing borg balances from blockchain to database.

This module provides reusable functions for balance synchronization that can be
imported and used by other Python modules without script-specific initialization.
"""

import asyncio
from typing import List, Dict, Any, Optional

from .borg_address_manager_address_primary import BorgAddressManagerAddressPrimary
from .demo_audit_logger import DemoAuditLogger
from .westend_adapter import WestendAdapter


class BorgBalanceSyncer:
    """
    Composable borg balance synchronization service.

    Provides methods to sync WND balances from Westend blockchain to Supabase database.
    Designed for reuse across different scripts and modules.
    """

    def __init__(
        self,
        supabase_client=None,
        audit_logger: Optional[DemoAuditLogger] = None,
        westend_adapter: Optional[WestendAdapter] = None,
        address_manager: Optional[BorgAddressManagerAddressPrimary] = None,
    ):
        """
        Initialize the balance syncer.

        Args:
            supabase_client: Supabase client for database operations
            audit_logger: Optional audit logger (creates default if None)
            westend_adapter: Optional Westend adapter (creates default if None)
        """
        self.supabase_client = supabase_client
        self.audit_logger = audit_logger or DemoAuditLogger()
        self.westend_adapter = westend_adapter
        self.asset_hub_adapter = None  # Initialize asset hub adapter

        self.address_manager = address_manager or BorgAddressManagerAddressPrimary(supabase_client=supabase_client, audit_logger=self.audit_logger)

    async def initialize_westend_adapter(self, rpc_url: str = "wss://westend-rpc.polkadot.io") -> bool:
        """
        Initialize or reinitialize the Westend adapter.

        Args:
            rpc_url: WebSocket URL for Westend RPC

        Returns:
            True if initialization successful
        """
        try:
            self.westend_adapter = WestendAdapter(rpc_url=rpc_url)
            health = await self.westend_adapter.health_check()
            return health.get("status") == "healthy"
        except Exception:
            return False

    async def initialize_asset_hub_adapter(self, rpc_url="wss://westend-asset-hub-rpc.polkadot.io", asset_id=None) -> bool:
        """
        Initialize or reinitialize the Asset Hub adapter.

        Args:
            rpc_url: WebSocket URL for Asset Hub RPC
            asset_id: USDB asset ID

        Returns:
            True if initialization successful
        """
        try:
            from .asset_hub_adapter import AssetHubAdapter
            self.asset_hub_adapter = AssetHubAdapter(rpc_url=rpc_url, asset_id=asset_id)
            return True
        except Exception:
            return False

    async def sync_all_borg_balances(
        self,
        batch_size: int = 10,
        max_borgs: int = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Sync WND balances for all borgs in Supabase from Westend blockchain.

        Args:
            batch_size: Number of borgs to process in each batch
            max_borgs: Maximum number of borgs to process (for testing)
            verbose: Whether to print progress messages

        Returns:
            Sync results with success/failure counts and details
        """
        if verbose:
            print("🔄 Starting borg balance synchronization...")
            print(f"   Batch size: {batch_size}")
            if max_borgs:
                print(f"   Max borgs: {max_borgs}")

        # Ensure Westend adapter is initialized
        if not self.westend_adapter:
            if not await self.initialize_westend_adapter():
                return {
                    "success": False,
                    "error": "Failed to initialize Westend adapter"
                }

        # Get all registered borgs
        if verbose:
            print("\n📋 Fetching all registered borgs...")

        borgs = self.address_manager.list_registered_borgs()
        if not borgs:
            return {
                "success": False,
                "error": "No borgs found in database"
            }

        total_borgs = len(borgs)
        if max_borgs:
            borgs = borgs[:max_borgs]
            total_borgs = len(borgs)

        if verbose:
            print(f"✅ Found {total_borgs} borg(s) to sync")

        # Process borgs in batches
        results = {
            "success": True,
            "total_borgs": total_borgs,
            "processed": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "details": []
        }

        for i in range(0, total_borgs, batch_size):
            batch = borgs[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_borgs + batch_size - 1) // batch_size

            if verbose:
                print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} borgs)...")

            for borg in batch:
                address = borg.get("substrate_address")
                borg_id = borg.get("borg_id")

                if not address:
                    if verbose:
                        print(f"⚠️  Skipping borg {borg_id}: no address")
                    results["failed_syncs"] += 1
                    results["details"].append({
                        "borg_id": borg_id,
                        "address": None,
                        "success": False,
                        "error": "No address"
                    })
                    continue

                try:
                    if verbose:
                        print(f"   🔄 Syncing {borg_id} ({address[:16]}...)")

                    # Sync WND balance from blockchain
                    balance_planck = await self.address_manager.sync_address_balance_from_blockchain(
                        address, self.westend_adapter, "WND"
                    )

                    balance_wnd = balance_planck / (10**12)
                    if verbose:
                        print(f"   ✅ Synced: {balance_planck} planck ({balance_wnd:.6f} WND)")

                    results["successful_syncs"] += 1
                    results["details"].append({
                        "borg_id": borg_id,
                        "address": address,
                        "success": True,
                        "balance_planck": balance_planck,
                        "balance_wnd": balance_wnd
                    })

                except Exception as e:
                    if verbose:
                        print(f"   ❌ Failed to sync {borg_id}: {str(e)}")
                    results["failed_syncs"] += 1
                    results["details"].append({
                        "borg_id": borg_id,
                        "address": address,
                        "success": False,
                        "error": str(e)
                    })

                results["processed"] += 1

            # Small delay between batches to be respectful to the RPC
            if i + batch_size < total_borgs:
                await asyncio.sleep(0.5)

        # Summary
        if verbose:
            print("\n📊 Synchronization Summary:")
            print(f"   Total borgs: {results['total_borgs']}")
            print(f"   Processed: {results['processed']}")
            print(f"   Successful: {results['successful_syncs']}")
            print(f"   Failed: {results['failed_syncs']}")

            if results["failed_syncs"] > 0:
                print(f"   ❌ Some syncs failed - check details")

        if results["failed_syncs"] > 0:
            results["success"] = False

        return results

    async def sync_single_borg_balance(self, borg_id: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Sync balance for a single borg by borg_id.

        Args:
            borg_id: Borg identifier
            verbose: Whether to print progress messages

        Returns:
            Sync result for the specific borg
        """
        if verbose:
            print(f"🔄 Syncing balance for borg: {borg_id}")

        # Ensure Westend adapter is initialized
        if not self.westend_adapter:
            if not await self.initialize_westend_adapter():
                return {
                    "success": False,
                    "error": "Failed to initialize Westend adapter"
                }

        # Get address for borg
        address = self.address_manager.get_borg_address(borg_id)
        if not address:
            return {
                "success": False,
                "error": f"Borg {borg_id} not found or has no address"
            }

        try:
            # Sync balance
            balance_planck = await self.address_manager.sync_address_balance_from_blockchain(
                address, self.westend_adapter, "WND"
            )

            balance_wnd = balance_planck / (10**12)
            if verbose:
                print(f"✅ Synced {borg_id}: {balance_planck} planck ({balance_wnd:.6f} WND)")

            return {
                "success": True,
                "borg_id": borg_id,
                "address": address,
                "balance_planck": balance_planck,
                "balance_wnd": balance_wnd
            }

        except Exception as e:
            if verbose:
                print(f"❌ Failed to sync {borg_id}: {str(e)}")
            return {
                "success": False,
                "borg_id": borg_id,
                "address": address,
                "error": str(e)
            }

    async def get_borg_balance_summary(self, borg_id: str) -> Dict[str, Any]:
        """
        Get current balance summary for a borg from database.

        Args:
            borg_id: Borg identifier

        Returns:
            Balance summary with WND and USDB balances
        """
        address = self.address_manager.get_borg_address(borg_id)
        if not address:
            return {
                "success": False,
                "error": f"Borg {borg_id} not found"
            }

        try:
            wnd_balance = self.address_manager.get_balance(address, "WND")
            usdb_balance = self.address_manager.get_balance(address, "USDB")

            return {
                "success": True,
                "borg_id": borg_id,
                "address": address,
                "balances": {
                    "WND": wnd_balance if wnd_balance is not None else 0,
                    "USDB": usdb_balance if usdb_balance is not None else 0
                }
            }
        except Exception as e:
            return {
                "success": False,
                "borg_id": borg_id,
                "error": str(e)
            }

    async def sync_single_borg_usdb_balance(self, borg_id: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Sync USDB balance for a single borg by borg_id.

        Args:
            borg_id: Borg identifier
            verbose: Whether to print progress messages

        Returns:
            Sync result for the specific borg
        """
        if verbose:
            print(f"🔄 Syncing USDB balance for borg: {borg_id}")

        # Ensure Asset Hub adapter is initialized
        if not self.asset_hub_adapter:
            asset_id = None
            try:
                from .config import load_usdb_asset_id
                asset_id = load_usdb_asset_id()
            except:
                pass
            if not await self.initialize_asset_hub_adapter(asset_id=asset_id):
                return {
                    "success": False,
                    "error": "Failed to initialize Asset Hub adapter"
                }

        # Get address for borg
        address = self.address_manager.get_borg_address(borg_id)
        if not address:
            return {
                "success": False,
                "error": f"Borg {borg_id} not found or has no address"
            }

        try:
            # Sync USDB balance from blockchain
            balance_planck = await self.address_manager.sync_address_balance_from_blockchain(
                address, self.asset_hub_adapter, "USDB"
            )

            balance_usdb = balance_planck / (10**12)
            if verbose:
                print(f"✅ Synced {borg_id}: {balance_planck} planck ({balance_usdb:.6f} USDB)")

            return {
                "success": True,
                "borg_id": borg_id,
                "address": address,
                "balance_planck": balance_planck,
                "balance_usdb": balance_usdb
            }

        except Exception as e:
            if verbose:
                print(f"❌ Failed to sync {borg_id}: {str(e)}")
            return {
                "success": False,
                "borg_id": borg_id,
                "address": address,
                "error": str(e)
            }


# Convenience functions for backward compatibility and easy importing
async def sync_all_borg_balances(
    supabase_client=None,
    batch_size: int = 10,
    max_borgs: int = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to sync all borg balances.

    Args:
        supabase_client: Supabase client (if None, will try to initialize)
        batch_size: Number of borgs to process in each batch
        max_borgs: Maximum number of borgs to process
        verbose: Whether to print progress messages

    Returns:
        Sync results
    """
    syncer = BorgBalanceSyncer(supabase_client=supabase_client)
    return await syncer.sync_all_borg_balances(
        batch_size=batch_size,
        max_borgs=max_borgs,
        verbose=verbose
    )


async def sync_single_borg_balance(
    borg_id: str,
    supabase_client=None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to sync a single borg balance.

    Args:
        borg_id: Borg identifier
        supabase_client: Supabase client (if None, will try to initialize)
        verbose: Whether to print progress messages

    Returns:
        Sync result
    """
    syncer = BorgBalanceSyncer(supabase_client=supabase_client)
    return await syncer.sync_single_borg_balance(borg_id, verbose=verbose)


async def get_borg_balance_summary(
    borg_id: str,
    supabase_client=None
) -> Dict[str, Any]:
    """
    Convenience function to get borg balance summary.

    Args:
        borg_id: Borg identifier
        supabase_client: Supabase client

    Returns:
        Balance summary
    """
    syncer = BorgBalanceSyncer(supabase_client=supabase_client)
    return await syncer.get_borg_balance_summary(borg_id)
