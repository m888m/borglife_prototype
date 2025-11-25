"""
Borg Transfer Module
Provides secure WND transfers between borgs using live Westend network.
"""

import asyncio
from decimal import Decimal
from typing import Dict, Any, Optional

from jam_mock.borg_address_manager_address_primary import BorgAddressManagerAddressPrimary
from jam_mock.demo_audit_logger import DemoAuditLogger
from jam_mock.westend_adapter import WestendAdapter
from substrateinterface import Keypair


class BorgTransferError(Exception):
    """Raised when borg transfer operations fail."""


class BorgTransfer:
    """
    Handles secure WND transfers between borgs on Westend network.

    Uses BorgAddressManager for keypair access and WestendAdapter for blockchain operations.
    """

    def __init__(
        self,
        westend_adapter: Optional[WestendAdapter] = None,
        address_manager: Optional[BorgAddressManagerAddressPrimary] = None,
        audit_logger: Optional[DemoAuditLogger] = None,
    ):
        """
        Initialize BorgTransfer.

        Args:
            westend_adapter: WestendAdapter instance (created if None)
            address_manager: BorgAddressManager instance (created if None)
            audit_logger: Audit logger instance (created if None)
        """
        self.westend_adapter = westend_adapter or WestendAdapter("wss://westend-rpc.polkadot.io")
        self.address_manager = address_manager or BorgAddressManagerAddressPrimary()
        self.audit_logger = audit_logger or DemoAuditLogger()

    async def transfer_wnd_between_borgs(
        self,
        amount_wnd: float,
        from_borg: str,
        to_borg: str,
    ) -> Dict[str, Any]:
        """
        Transfer WND from one borg to another.

        Args:
            amount_wnd: Amount of WND to transfer
            from_borg: Source borg ID or address
            to_borg: Destination borg ID or address

        Returns:
            Transfer result with success status and details

        Raises:
            BorgTransferError: If transfer fails
        """
        try:
            # Resolve addresses
            from_address = self._resolve_address(from_borg)
            to_address = self._resolve_address(to_borg)

            if not from_address or not to_address:
                raise BorgTransferError(f"Could not resolve addresses: from={from_borg}, to={to_borg}")

            # Get keypair for sender
            from_keypair = self._get_keypair_for_borg(from_borg)
            if not from_keypair:
                raise BorgTransferError(f"No keypair found for borg {from_borg}")

            if from_keypair.ss58_address != from_address:
                raise BorgTransferError(
                    f"Keypair address mismatch for {from_borg}: expected {from_address}, got {from_keypair.ss58_address}"
                )

            # Check balance
            from_balance_planck = await self.westend_adapter.get_wnd_balance(from_address)
            from_balance_wnd = from_balance_planck / (10**12)

            if from_balance_wnd < amount_wnd:
                raise BorgTransferError(
                    f"Insufficient balance: {from_balance_wnd:.6f} WND < {amount_wnd:.6f} WND"
                )

            # Execute transfer
            amount_planck = int(Decimal(str(amount_wnd)) * (10**12))

            # Set keypair for transfer
            original_keypair = self.westend_adapter.keypair
            self.westend_adapter.keypair = from_keypair
            try:
                transfer_result = await self.westend_adapter.transfer_wnd(
                    from_address, to_address, amount_planck
                )
            finally:
                self.westend_adapter.keypair = original_keypair

            if not transfer_result.get("success"):
                # Update database balances and log transaction
                await self._update_balances_and_log_transaction(
                    from_address, to_address, amount_planck, transfer_result
                )
                error_msg = transfer_result.get("error", "Unknown transfer error")
                raise BorgTransferError(f"Transfer failed: {error_msg}")

            # Log successful transfer
            self.audit_logger.log_event(
                "borg_transfer_success",
                f"Transferred {amount_wnd} WND from {from_borg} to {to_borg}",
                {
                    "from_borg": from_borg,
                    "to_borg": to_borg,
                    "from_address": from_address,
                    "to_address": to_address,
                    "amount_wnd": amount_wnd,
                    "amount_planck": amount_planck,
                    "transaction_hash": transfer_result.get("transaction_hash"),
                    "block_number": transfer_result.get("block_number"),
                },
            )

            return {
                "success": True,
                "from_borg": from_borg,
                "to_borg": to_borg,
                "from_address": from_address,
                "to_address": to_address,
                "amount_wnd": amount_wnd,
                "transaction_hash": transfer_result.get("transaction_hash"),
                "block_number": transfer_result.get("block_number"),
                "explorer_url": f"https://westend.subscan.io/extrinsic/{transfer_result.get('transaction_hash')}",
            }

        except BorgTransferError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during borg transfer: {str(e)}"
            self.audit_logger.log_event(
                "borg_transfer_error",
                error_msg,
                {
                    "from_borg": from_borg,
                    "to_borg": to_borg,
                    "amount_wnd": amount_wnd,
                    "error": str(e),
                },
            )
            raise BorgTransferError(error_msg)

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

    def _get_keypair_for_borg(self, borg_identifier: str) -> Optional[Keypair]:
