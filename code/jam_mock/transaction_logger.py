#!/usr/bin/env python3
"""
Transaction Logger - Unified Westend Transaction Metadata Registration
Handles logging of all transaction types (WND, USDB) between borgs and dispensers to Supabase.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.borglife"))

try:
    from supabase import create_client, Client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")
    supabase_client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
except ImportError:
    supabase_client = None


class TransactionLogger:
    """
    Unified transaction metadata logger for Westend blockchain transactions.

    Handles logging of:
    - WND transfers (borg-to-borg, dispenser-to-borg)
    - USDB transfers (future asset transfers)
    - Transaction metadata with validation and error handling
    """

    SUPPORTED_CURRENCIES = ["WND", "USDB"]

    def __init__(self, supabase_client: Optional[Client] = None):
        """
        Initialize TransactionLogger.

        Args:
            supabase_client: Supabase client (uses global if None)
        """
        self.supabase = supabase_client or supabase_client

    def log_wnd_transfer(
        self,
        tx_hash: str,
        from_address: str,
        to_address: str,
        amount_planck: int,
        block_number: Optional[int] = None,
        block_hash: Optional[str] = None,
        fee_planck: Optional[int] = None,
        timestamp: Optional[float] = None,
        network: str = "westend"
    ) -> Dict[str, Any]:
        """
        Log WND transfer transaction metadata.

        Args:
            tx_hash: Transaction hash
            from_address: Sender address
            to_address: Recipient address
            amount_planck: Amount in planck units
            block_number: Westend block number
            block_hash: Block hash
            fee_planck: Transaction fee in planck
            timestamp: Unix timestamp
            network: Network name

        Returns:
            Logging result with success status
        """
        return self._log_transaction(
            tx_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            currency="WND",
            amount_planck=amount_planck,
            block_number=block_number,
            block_hash=block_hash,
            fee_planck=fee_planck,
            timestamp=timestamp,
            network=network
        )

    def log_usdb_transfer(
        self,
        tx_hash: str,
        from_address: str,
        to_address: str,
        amount_planck: int,
        asset_id: Optional[int] = None,
        block_number: Optional[int] = None,
        block_hash: Optional[str] = None,
        fee_planck: Optional[int] = None,
        timestamp: Optional[float] = None,
        network: str = "westend"
    ) -> Dict[str, Any]:
        """
        Log USDB transfer transaction metadata.

        Args:
            tx_hash: Transaction hash
            from_address: Sender address
            to_address: Recipient address
            amount_planck: Amount in planck units
            asset_id: USDB asset ID
            block_number: Westend block number
            block_hash: Block hash
            fee_planck: Transaction fee in planck
            timestamp: Unix timestamp
            network: Network name

        Returns:
            Logging result with success status
        """
        return self._log_transaction(
            tx_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            currency="USDB",
            amount_planck=amount_planck,
            asset_id=asset_id,
            block_number=block_number,
            block_hash=block_hash,
            fee_planck=fee_planck,
            timestamp=timestamp,
            network=network
        )

    def log_transfer_from_result(
        self,
        transfer_result: Dict[str, Any],
        currency: str = "WND",
        asset_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Log transaction from transfer result dict (convenience method).

        Args:
            transfer_result: Result from transfer_wnd or similar
            currency: Currency type
            asset_id: Asset ID for non-native currencies

        Returns:
            Logging result
        """
        if not transfer_result.get("success"):
            return {
                "success": False,
                "error": "Transfer was not successful",
                "transfer_result": transfer_result
            }

        return self._log_transaction(
            tx_hash=transfer_result["transaction_hash"],
            from_address=transfer_result["from_address"],
            to_address=transfer_result["to_address"],
            currency=currency,
            amount_planck=int(transfer_result.get("amount_planck", transfer_result.get("amount", 0)) * 10**12),
            block_number=transfer_result.get("westend_block_number"),
            block_hash=transfer_result.get("block"),
            fee_planck=transfer_result.get("fee_planck"),
            timestamp=transfer_result.get("timestamp"),
            asset_id=asset_id,
            network="westend"
        )

    def _log_transaction(
        self,
        tx_hash: str,
        from_address: str,
        to_address: str,
        currency: str,
        amount_planck: int,
        asset_id: Optional[int] = None,
        block_number: Optional[int] = None,
        block_hash: Optional[str] = None,
        fee_planck: Optional[int] = None,
        timestamp: Optional[float] = None,
        network: str = "westend"
    ) -> Dict[str, Any]:
        """
        Internal method to log transaction to Supabase.
        """
        try:
            # Validate inputs
            if currency not in self.SUPPORTED_CURRENCIES:
                return {"success": False, "error": f"Unsupported currency: {currency}"}

            if not tx_hash or not from_address or not to_address:
                return {"success": False, "error": "Missing required transaction data"}

            # Prepare transaction record
            transaction_data = {
                "tx_hash": tx_hash,
                "from_addr": from_address,
                "to_addr": to_address,
                "amount": amount_planck / 10**12,  # Convert to human readable amount
                "timestamp": (datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else datetime.now(timezone.utc)).isoformat(),
                "network": network,
            }

            if not self.supabase:
                return {
                    "success": False,
                    "error": "No Supabase client available",
                    "transaction_data": transaction_data
                }

            # Insert into transfer_transactions table
            result = self.supabase.table("transfer_transactions").insert(transaction_data).execute()

            if result.data:
                return {
                    "success": True,
                    "transaction_id": result.data[0].get("id"),
                    "tx_hash": tx_hash,
                    "message": f"Logged {currency} transfer: {amount_planck} planck"
                }
            else:
                return {
                    "success": False,
                    "error": "Supabase insert returned no data",
                    "transaction_data": transaction_data
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "transaction_data": {
                    "tx_hash": tx_hash,
                    "from_address": from_address,
                    "to_address": to_address,
                    "currency": currency,
                    "amount_planck": amount_planck
                }
            }

    def get_transaction_history(
        self,
        address: Optional[str] = None,
        currency: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get transaction history with optional filtering.

        Args:
            address: Filter by address (from_addr or to_addr)
            currency: Filter by currency
            limit: Maximum number of transactions

        Returns:
            Transaction history result
        """
        try:
            if not self.supabase:
                return {"success": False, "error": "No Supabase client available"}

            query = self.supabase.table("transfer_transactions").select("*")

            if address:
                # Note: This is a simplified filter - in production might need OR condition
                query = query.or_(f"from_addr.eq.{address},to_addr.eq.{address}")

            if currency:
                query = query.eq("currency", currency)

            query = query.order("timestamp", desc=True).limit(limit)

            result = query.execute()

            return {
                "success": True,
                "transactions": result.data or [],
                "count": len(result.data) if result.data else 0
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_transaction_by_hash(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction details by hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction data or None
        """
        try:
            if not self.supabase:
                return None

            result = self.supabase.table("transfer_transactions").select("*").eq("tx_hash", tx_hash).execute()

            return result.data[0] if result.data else None

        except Exception:
            return None