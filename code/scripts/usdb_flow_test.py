#!/usr/bin/env python3
"""
USDB Flow Live Test

Tests USDB transfers on Westend Asset Hub with balance verification.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional

# Fix path for jam_mock imports when running from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jam_mock.asset_hub_adapter import AssetHubAdapter
from dotenv import load_dotenv
from jam_mock.borg_address_manager_address_primary import BorgAddressManagerAddressPrimary
from jam_mock.borg_balance_syncer import BorgBalanceSyncer
from jam_mock.usdb_transfer import USDBTransfer
from scripts.create_usdb_asset import USDBAssetManager
from supabase import create_client, Client
from jam_mock.config import load_usdb_asset_id


def init_supabase() -> Optional[Client]:
    """Initialize Supabase client."""
    # Load environment variables from .env.borglife
    load_dotenv(".env.borglife")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY")
    if not url or not key:
        print("Warning: No Supabase env vars, db sync skipped")
        return None
    return create_client(url, key)


async def ensure_test_borgs(address_manager: BorgAddressManagerAddressPrimary, borg_ids: list[str]):
    """Ensure test borgs exist, register if needed."""
    test_dna_hashes = {
        "test_borg1": "a" * 64,
        "test_borg2": "b" * 64
    }
    for borg_id in borg_ids:
        if not address_manager.get_borg_address(borg_id):
            print(f"Registering {borg_id}...")
            # Unique dummy DNA hashes for testing only - not production DNA
            dna_hash = test_dna_hashes.get(borg_id, "c" * 64)
            result = address_manager.register_borg_address(borg_id, dna_hash)
            if not result["success"]:
                raise Exception(f"Failed to register {borg_id}: {result.get('error')}")
            print(f"Registered {borg_id} at {result['address']}")


async def get_usdb_balance_planck(syncer: BorgBalanceSyncer, borg_id: str) -> int:
    """Sync and get USDB balance in planck for a borg."""
    await syncer.sync_single_borg_usdb_balance(borg_id)
    return (await syncer.get_borg_balance_summary(borg_id))["balances"]["USDB"]


async def assert_usdb_balance(
    syncer: BorgBalanceSyncer,
    borg_id: str,
    expected_planck: int,
    msg_prefix: str = ""
) -> None:
    """Assert USDB balance matches expected, with logging."""
    balance_planck = await get_usdb_balance_planck(syncer, borg_id)
    print(f"{msg_prefix}{borg_id}: actual={balance_planck / 10**12:.0f}, expected={expected_planck / 10**12:.0f}")
    if balance_planck != expected_planck:
        raise Exception(
            f"{msg_prefix}Balance mismatch {borg_id}: {balance_planck} != {expected_planck}"
        )


async def drain_usdb_for_isolation(
    transfer: USDBTransfer,
    syncer: BorgBalanceSyncer,
    borg_id: str,
    target: str = "dispenser"
) -> dict:
    """Drain excess USDB from borg for test isolation (leave ~1 USDB)."""
    balance = await get_usdb_balance_planck(syncer, borg_id)
    if balance <= 10**12:  # <= 1 USDB
        return {"success": True, "note": "No pre-balance to drain"}
    usdb = balance // 10**12
    drain_usdb = min(usdb - 1, usdb // 2)
    print(f"  Draining {drain_usdb} USDB from {borg_id} (pre: {usdb} USDB)")
    if drain_usdb > 0:
        return await transfer.transfer_usdb_between_borgs(drain_usdb, borg_id, target)
    return {"success": True, "note": "No drain needed"}


async def cleanup_excess_usdb(
    transfer: USDBTransfer,
    syncer: BorgBalanceSyncer,
    borg_id: str,
    initial_dust_planck: int,
    target: str = "dispenser"
) -> dict:
    """Cleanup post-test excess USDB back to target (conservative)."""
    balance = await get_usdb_balance_planck(syncer, borg_id)
    if balance <= initial_dust_planck:
        return {"success": True, "note": "Cleanup skipped"}
    excess_planck = balance - initial_dust_planck
    excess_usdb = excess_planck // 10**12
    cleanup_usdb = min(excess_usdb - 1, excess_usdb // 2) if excess_usdb > 1 else 0
    print(f"  Cleaning up {cleanup_usdb} USDB from {borg_id} (excess: {excess_usdb} USDB)")
    if cleanup_usdb > 0:
        return await transfer.transfer_usdb_between_borgs(cleanup_usdb, borg_id, target)
    return {"success": True, "note": "No significant excess to cleanup"}


async def fund_borg_wnd(
    adapter: AssetHubAdapter,
    dispenser_kp,
    borg_addr: str,
    amount_planck: int
) -> dict:
    """Fund a borg address with WND for tx fees."""
    return await adapter.transfer_native(dispenser_kp, borg_addr, amount_planck)

async def main():
    """Main test execution."""
    print("🚀 === USDB Flow Live Test Started ===")
    print("Step 0: Loading config...")
    # Load config
    asset_id = load_usdb_asset_id()
    print(f"✅ Loaded USDB asset ID: {asset_id}")
    
    print("Step 1: Initializing clients...")
    # Init clients
    supabase_client = init_supabase()
    print(f"✅ Supabase: {'connected' if supabase_client else 'skipped'}")
    address_manager = BorgAddressManagerAddressPrimary(supabase_client=supabase_client)
    print("✅ Address manager initialized")
    asset_manager = USDBAssetManager()
    print("✅ Asset manager initialized")
    asset_hub_adapter = AssetHubAdapter(asset_id=asset_id)
    print("✅ Asset Hub adapter connected")
    transfer = USDBTransfer(asset_hub_adapter=asset_hub_adapter, address_manager=address_manager)
    print("✅ Transfer initialized")
    syncer = BorgBalanceSyncer(supabase_client=supabase_client, address_manager=address_manager)
    print("✅ Syncer initialized")
    
    test_borgs = ["test_borg1", "test_borg2"]
    
    print("Step 2: Ensuring test borgs exist...")
    # Ensure test borgs
    await ensure_test_borgs(address_manager, test_borgs)
    print("✅ Test borgs ready")
    
    print("Step 2.5: Funding test borgs with 0.2 WND for tx fees...")
    # Get addresses and dispenser keypair
    borg_addresses = {borg: address_manager.get_borg_address(borg) for borg in test_borgs}
    dispenser_kp = transfer._get_keypair_for_borg("dispenser")
    if not all([dispenser_kp] + list(borg_addresses.values())):
        raise Exception("Failed to resolve addresses or dispenser keypair")
    
    wnd_amount = int(0.2 * 10**12)  # 0.2 WND
    fund_results = []
    for borg_id in test_borgs:
        fund_result = await fund_borg_wnd(asset_hub_adapter, dispenser_kp, borg_addresses[borg_id], wnd_amount)
        print(f"Fund {borg_id} result: {fund_result}")
        if not fund_result["success"]:
            print(f"⚠️ Fund {borg_id} warning: {fund_result.get('error', 'unknown')}")
        fund_results.append(fund_result)
    print("✅ Test borgs funded (best-effort)")
    await asyncio.sleep(10)  # Wait for confirmations and nonce advancement
    print("⏳ Waited 10s for tx confirmations")
    
    print("Step 3: Pre-test cleanup...")
    # Pre-test cleanup: drain existing USDB from test borgs for isolation
    print("🧹 Pre-test cleanup: Draining existing USDB balances from test borgs...")
    drain_results = []
    for borg_id in test_borgs:
        drain_result = await drain_usdb_for_isolation(transfer, syncer, borg_id)
        drain_results.append(drain_result)
        if drain_result.get("success", False) or "note" in drain_result:
            print(f"✅ Pre-drain {borg_id}: {drain_result.get('note', 'done')}")
        else:
            print(f"⚠️ Pre-drain {borg_id} failed (non-fatal): {drain_result}")
    
    # Verify drained (allow conservative drain residue)
    for borg_id in test_borgs:
        post_drain = await get_usdb_balance_planck(syncer, borg_id)
        print(f"Post-drain {borg_id}: {post_drain / 10**12:.0f} USDB")
        assert post_drain <= 400 * 10**12, f"Pre-drain {borg_id} failed - excessive balance remains: {post_drain / 10**12:.0f} USDB"
    print("✅ Pre-test cleanup complete - allowing conservative drain residue")
    
    print("Step 4: Recording initial dust balances...")
    initial_balances = {
        borg_id: await get_usdb_balance_planck(syncer, borg_id)
        for borg_id in test_borgs
    }
    print("Initial dust:", ", ".join(f"{borg}={bal / 10**12:.0f} USDB" for borg, bal in initial_balances.items()))
    
    print("Step 5: Minting 1000 USDB to dispenser...")
    # Mint 1000 USDB to dispenser
    dispenser_address = "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD"
    amount_1000 = 1000 * 10**12
    success = await asset_manager.mint_usdb(asset_id, dispenser_address, amount_1000)
    if not success:
        raise Exception("Mint failed")
    print("✅ Mint complete")
    
    print("Steps 6-8: Performing transfers and balance assertions...")
    # Configurable transfers (from, to, amount_usdb); dispenser not tracked in expected
    transfers = [
        (600, "dispenser", "test_borg1"),
        (300, "dispenser", "test_borg2"),
        (50, "test_borg1", "test_borg2"),
    ]
    transfer_results = []
    expected_balances = initial_balances.copy()
    
    for i, (amount_usdb, from_borg, to_borg) in enumerate(transfers, 1):
        print(f"Transfer {i}: {amount_usdb} USDB {from_borg} -> {to_borg}...")
        result = await transfer.transfer_usdb_between_borgs(amount_usdb, from_borg, to_borg)
        print(f"Transfer {i} result: {result}")
        transfer_results.append(result)
        if not result["success"]:
            raise Exception(f"Transfer {i} failed")
        
        # Update expected (only for tracked test_borgs)
        amount_planck = amount_usdb * 10**12
        if to_borg in expected_balances:
            expected_balances[to_borg] += amount_planck
        if from_borg in expected_balances:
            expected_balances[from_borg] -= amount_planck
        
        # Assert both test borgs after each transfer
        for borg_id in test_borgs:
            await assert_usdb_balance(
                syncer, borg_id, expected_balances[borg_id],
                f"After transfer {i} "
            )
        print(f"✅ Balances verified after transfer {i}")
    
    print("Step 9: Post-test cleanup...")
    # Post-test cleanup: transfer excess back to dispenser
    cleanup_results = []
    for borg_id in test_borgs:
        cleanup_result = await cleanup_excess_usdb(
            transfer, syncer, borg_id, initial_balances[borg_id]
        )
        cleanup_results.append(cleanup_result)
        if not cleanup_result["success"]:
            print(f"⚠️ Cleanup {borg_id} failed (non-fatal): {cleanup_result}")
    
    print("✅ Cleanup complete")
    
    print("Step 10: Generating report...")
    # Final sync for report
    final_balances = {
        borg_id: await get_usdb_balance_planck(syncer, borg_id)
        for borg_id in test_borgs
    }
    
    # JSON report
    report = {
        "asset_id": asset_id,
        "test_borgs": test_borgs,
        "fund_results": fund_results,
        "transfers": transfer_results,
        "drains": drain_results,
        "cleanups": cleanup_results,
        "initial_balances": initial_balances,
        "final_balances": final_balances,
    }
    with open("usdb_flow_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("🎉 USDB flow test completed successfully!")
    print("Report saved to usdb_flow_test_report.json")
    print("🚀 === Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())