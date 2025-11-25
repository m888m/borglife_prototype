#!/usr/bin/env python3
"""
Asset Hub Adapter for Westend Asset Hub
Composable adapter for USDB operations on Asset Hub.
"""

from typing import Dict, Any, Optional
from substrateinterface import Keypair, SubstrateInterface


class AssetHubAdapter:
    """
    Adapter for Westend Asset Hub operations (USDB transfers, balances).
    """
    def __init__(
        self,
        rpc_url: str = "wss://westend-asset-hub-rpc.polkadot.io",
        asset_id: Optional[int] = None,
    ):
        self.substrate = SubstrateInterface(url=rpc_url, ss58_format=42)
        self.asset_id = asset_id
        if not asset_id:
            raise ValueError("asset_id required for USDB operations")

    def get_usdb_balance(self, address: str) -> int:
        """
        Get USDB balance for address in planck units.
        """
        balance = self.substrate.query(
            "Assets",
            "Account",
            params=[self.asset_id, address]
        )
        return int(balance.value["balance"]) if balance.value else 0

    async def transfer_usdb(
        self,
        from_keypair: Keypair,
        to_address: str,
        amount_planck: int,
        tip: int = 10000000000
    ) -> Dict[str, Any]:
        """
        Transfer USDB using Assets.transfer extrinsic.
        """
        call = self.substrate.compose_call(
            call_module="Assets",
            call_function="transfer",
            call_params={
                "id": self.asset_id,
                "target": to_address,
                "amount": amount_planck,
            },
        )
        nonce = self.substrate.get_account_nonce(from_keypair.ss58_address)
        extrinsic = self.substrate.create_signed_extrinsic(call=call, keypair=from_keypair, nonce=nonce, tip=tip)
        receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        
        if not receipt.is_success:
            error_parts: List[str] = []
            if receipt.error_message:
                error_parts.append(receipt.error_message)
            if hasattr(receipt, 'error') and receipt.error is not None:
                error_parts.append(f"Error object: {str(receipt.error)}")
            if receipt.triggered_events:
                event_details: List[Dict[str, str]] = []
                for e in receipt.triggered_events[:5]:
                    try:
                        mid = getattr(e, 'module_id', 'unknown')
                        eid = getattr(e, 'event_id', 'unknown')
                        evalue = str(getattr(e, 'value', 'no_value'))
                        event_details.append(f"{mid}.{eid}: {evalue}")
                    except Exception:
                        event_details.append(f"Event parse error: {str(e)}")
                error_parts.append(f"Events ({len(receipt.triggered_events)}): {'; '.join(event_details)}")
            error_msg = '; '.join(error_parts) if error_parts else "Unknown Substrate failure"
        else:
            error_msg = None

        result = {
            "success": receipt.is_success,
            "transaction_hash": receipt.extrinsic_hash,
            "block_number": receipt.block_number or "unconfirmed",
            "explorer_url": f"https://westend-asset-hub.subscan.io/extrinsic/{receipt.extrinsic_hash}",
            "error": error_msg,
        }
        if result["block_number"] == "unconfirmed" and result["success"]:
            result["warning"] = "Transaction success but block_number not yet confirmed"
        return result

    async def transfer_native(
        self,
        from_keypair: Keypair,
        to_address: str,
        amount_planck: int,
        tip: int = 10**10
    ) -> Dict[str, Any]:
        """
        Transfer native tokens using Balances.transfer_keep_alive extrinsic.
        """
        call = self.substrate.compose_call(
            call_module="Balances",
            call_function="transfer_keep_alive",
            call_params={
                "dest": to_address,
                "value": amount_planck,
            },
        )
        nonce = self.substrate.get_account_nonce(from_keypair.ss58_address)
        extrinsic = self.substrate.create_signed_extrinsic(call=call, keypair=from_keypair, nonce=nonce, tip=tip)
        receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        
        if not receipt.is_success:
            error_parts = []
            if receipt.error_message:
                error_parts.append(receipt.error_message)
            if hasattr(receipt, 'error') and receipt.error is not None:
                error_parts.append(f"Error object: {str(receipt.error)}")
            if receipt.triggered_events:
                event_details = []
                for e in receipt.triggered_events[:5]:
                    try:
                        mid = getattr(e, 'module_id', 'unknown')
                        eid = getattr(e, 'event_id', 'unknown')
                        evalue = str(getattr(e, 'value', 'no_value'))
                        event_details.append(f"{mid}.{eid}: {evalue}")
                    except Exception:
                        event_details.append(f"Event parse error: {str(e)}")
                error_parts.append(f"Events ({len(receipt.triggered_events)}): {'; '.join(event_details)}")
            error_msg = '; '.join(error_parts) if error_parts else "Unknown Substrate failure"
        else:
            error_msg = None

        result = {
            "success": receipt.is_success,
            "transaction_hash": receipt.extrinsic_hash,
            "block_number": receipt.block_number or "unconfirmed",
            "explorer_url": f"https://westend-asset-hub.subscan.io/extrinsic/{receipt.extrinsic_hash}",
            "error": error_msg,
        }
        if result["block_number"] == "unconfirmed" and result["success"]:
            result["warning"] = "Transaction success but block_number not yet confirmed"
        return result