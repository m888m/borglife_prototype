"""
Borg USDB Transfer Module
Provides secure USDB transfers between borgs using live Westend Asset Hub.
"""

import asyncio
import os
from decimal import Decimal
from typing import Dict, Any, Optional

from jam_mock.asset_hub_adapter import AssetHubAdapter
from jam_mock.borg_address_manager_address_primary import BorgAddressManagerAddressPrimary
from jam_mock.demo_audit_logger import DemoAuditLogger
from .config import load_usdb_asset_id


class USDBTransferError(Exception):
    """Raised when USDB transfer operations fail."""


class USDBTransfer:
    """
    Handles secure USDB transfers between borgs on Westend Asset Hub.
    
    Note: "dispenser" borg_id is special-cased for admin operations:
    - Resolves to hardcoded address: 5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD
    - Keypair from dedicated keyring service "borglife-dispenser" (not deterministic from DNA/registered in address_manager)
    - Enables minting/distribution without conflicting with deterministic borg keypairs
    
    Uses BorgAddressManager for keypair access and AssetHubAdapter for blockchain operations.
    """

    def __init__(
        self,
        asset_hub_adapter: Optional[AssetHubAdapter] = None,
        address_manager: Optional[BorgAddressManagerAddressPrimary] = None,
        audit_logger: Optional[DemoAuditLogger] = None,
    ):
        """
        Initialize USDBTransfer.

        Args:
            asset_hub_adapter: AssetHubAdapter instance (created if None)
            address_manager: BorgAddressManager instance (created if None)
            audit_logger: Audit logger instance (created if None)
        """
        asset_id = load_usdb_asset_id()
        self.asset_hub_adapter = asset_hub_adapter or AssetHubAdapter(asset_id=asset_id)
        self.address_manager = address_manager or BorgAddressManagerAddressPrimary()
        self.audit_logger = audit_logger or DemoAuditLogger()

    async def transfer_usdb_between_borgs(
        self,
        amount_usdb: float,
        from_borg: str,
        to_borg: str,
    ) -> Dict[str, Any]:
        """
        Transfer USDB from one borg to another.

        Args:
            amount_usdb: Amount of USDB to transfer
            from_borg: Source borg ID or address
            to_borg: Destination borg ID or address

        Returns:
            Transfer result with success status and details

        Raises:
            USDBTransferError: If transfer fails
        """
        try:
            # Resolve addresses
            from_address = self._resolve_address(from_borg)
            to_address = self._resolve_address(to_borg)

            if not from_address or not to_address:
                raise USDBTransferError(f"Could not resolve addresses: from={from_borg}, to={to_borg}")

            # Get keypair for sender
            from_keypair = self._get_keypair_for_borg(from_borg)
            if not from_keypair:
                raise USDBTransferError(f"No keypair found for borg {from_borg}")

            if from_keypair.ss58_address != from_address:
                raise USDBTransferError(
                    f"Keypair address mismatch for {from_borg}: expected {from_address}, got {from_keypair.ss58_address}"
                )

            # Check balance
            from_balance_planck = self.asset_hub_adapter.get_usdb_balance(from_address)
            from_balance_usdb = from_balance_planck / (10**12)

            if from_balance_usdb < amount_usdb:
                raise USDBTransferError(
                    f"Insufficient balance: {from_balance_usdb:.6f} USDB < {amount_usdb:.6f} USDB"
                )

            # Execute transfer
            amount_planck = int(Decimal(str(amount_usdb)) * (10**12))

            result = await self.asset_hub_adapter.transfer_usdb(
                from_keypair, to_address, amount_planck
            )

            if not result.get("success"):
                error_msg = result.get("error", "Unknown transfer error")
                raise USDBTransferError(f"Transfer failed: {error_msg}")

            # Log successful transfer
            self.audit_logger.log_event(
                "usdb_transfer_success",
                f"Transferred {amount_usdb} USDB from {from_borg} to {to_borg}",
                {
                    "from_borg": from_borg,
                    "to_borg": to_borg,
                    "from_address": from_address,
                    "to_address": to_address,
                    "amount_usdb": amount_usdb,
                    "amount_planck": amount_planck,
                    "transaction_hash": result.get("transaction_hash"),
                    "block_number": result.get("block_number"),
                },
            )

            return {
                "success": True,
                "from_borg": from_borg,
                "to_borg": to_borg,
                "from_address": from_address,
                "to_address": to_address,
                "amount_usdb": amount_usdb,
                "transaction_hash": result.get("transaction_hash"),
                "block_number": result.get("block_number"),
                "explorer_url": result.get("explorer_url"),
            }

        except USDBTransferError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during USDB transfer: {str(e)}"
            self.audit_logger.log_event(
                "usdb_transfer_error",
                error_msg,
                {
                    "from_borg": from_borg,
                    "to_borg": to_borg,
                    "amount_usdb": amount_usdb,
                    "error": str(e),
                },
            )
            raise USDBTransferError(error_msg)

    def _resolve_address(self, borg_identifier: str) -> Optional[str]:
        """
        Resolve borg identifier to address.

        Args:
            borg_identifier: Borg ID or address

        Returns:
            Address string or None if not found
        """
        # Handle special borg IDs
        if borg_identifier == "dispenser":
            return "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD"

        # If it looks like an address, return as-is
        if borg_identifier.startswith("5"):
            return borg_identifier

        # Otherwise, look up by borg ID
        return self.address_manager.get_borg_address(borg_identifier)

    def _get_keypair_for_borg(self, borg_identifier: str) -> Optional[Any]:
            """
            Get keypair for borg identifier.
            
            For dispenser, returns the admin keypair from keyring.
            For other borgs, looks up in address manager.
            """
            if borg_identifier == "dispenser":
                # Dispenser uses the admin keypair from keyring
                import keyring
                from substrateinterface import Keypair
                
                private_key_hex = keyring.get_password("borglife-dispenser", "private_key")
                if not private_key_hex:
                    return None
                return Keypair(private_key=bytes.fromhex(private_key_hex), ss58_format=42)
            
            # For regular borgs, look up in address manager
            return self.address_manager.get_borg_keypair(borg_identifier)

# Convenience functions for backward compatibility and easy importing
async def transfer_usdb_between_borgs(
    amount_usdb: float,
    from_borg: str,
    to_borg: str,
    asset_hub_adapter: Optional[AssetHubAdapter] = None,
    address_manager: Optional[BorgAddressManagerAddressPrimary] = None,
    audit_logger: Optional[DemoAuditLogger] = None,
) -> Dict[str, Any]:
    """
    Convenience function to transfer USDB between borgs.

    Args:
        amount_usdb: Amount of USDB to transfer
        from_borg: Source borg ID or address
        to_borg: Destination borg ID or address
        asset_hub_adapter: AssetHubAdapter instance
        address_manager: BorgAddressManager instance
        audit_logger: Audit logger instance

    Returns:
        Transfer result
    """
    transfer = USDBTransfer(
        asset_hub_adapter=asset_hub_adapter,
        address_manager=address_manager,
        audit_logger=audit_logger,
    )
    return await transfer.transfer_usdb_between_borgs(amount_usdb, from_borg, to_borg)
