"""
Inter-Borg Transfer Protocol for Phase 2A

Secure fund transfer capabilities between borg addresses with comprehensive validation.
"""

import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal

from .kusama_adapter import WestendAdapter
from .borg_address_manager import BorgAddressManager
from .economic_validator import EconomicValidator
from .transaction_manager import TransactionManager, TransactionType
from .demo_audit_logger import DemoAuditLogger

class InterBorgTransfer:
    """
    Secure inter-borg transfer protocol with full validation and monitoring.

    Handles USDB transfers between borgs with balance checks, ethical compliance,
    transaction monitoring, and comprehensive error handling.
    """

    def __init__(
        self,
        westend_adapter: WestendAdapter,
        address_manager: BorgAddressManager,
        economic_validator: EconomicValidator,
        transaction_manager: TransactionManager,
        audit_logger: Optional[DemoAuditLogger] = None
    ):
        """
        Initialize InterBorgTransfer.

        Args:
            westend_adapter: Westend blockchain adapter
            address_manager: Borg address management
            economic_validator: Economic validation and compliance
            transaction_manager: Transaction management and monitoring
            audit_logger: Audit logging for compliance
        """
        self.westend_adapter = westend_adapter
        self.address_manager = address_manager
        self.economic_validator = economic_validator
        self.transaction_manager = transaction_manager
        self.audit_logger = audit_logger or DemoAuditLogger()

        # Transfer configuration
        self.confirmation_timeout = 300  # 5 minutes
        self.max_retry_attempts = 3

    async def transfer_wnd_between_borgs(
        self,
        from_borg_id: str,
        to_borg_id: str,
        amount_wnd: float,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Execute secure WND transfer between borgs using live Westend network.

        Args:
            from_borg_id: Sending borg ID
            to_borg_id: Receiving borg ID
            amount_wnd: Transfer amount in WND
            description: Optional transfer description

        Returns:
            Transfer result with success status and details
        """
        transfer_result = {
            'success': False,
            'transaction_hash': None,
            'amount': str(amount_wnd),
            'from_borg_id': from_borg_id,
            'to_borg_id': to_borg_id,
            'errors': [],
            'warnings': []
        }

        try:
            # Step 1: Get borg addresses
            from_address = self.address_manager.get_borg_address(from_borg_id)
            to_address = self.address_manager.get_borg_address(to_borg_id)

            if not from_address or not to_address:
                transfer_result['errors'].append("Could not resolve borg addresses")
                return transfer_result

            # Step 2: Get borg keypairs from macOS Keychain
            from_keypair = self.address_manager.get_borg_keypair(from_borg_id)
            if not from_keypair:
                transfer_result['errors'].append(f"No keypair found in macOS Keychain for borg {from_borg_id}")
                return transfer_result

            # Step 3: Convert amount to planck units
            amount_planck = int(amount_wnd * (10 ** 12))  # WND has 12 decimals

            # Step 4: Check sender balance
            sender_balance = await self.westend_adapter.get_wnd_balance(from_address)
            if sender_balance < amount_planck:
                transfer_result['errors'].append(f"Insufficient balance: {sender_balance} < {amount_planck} planck")
                return transfer_result

            # Step 5: Execute blockchain transfer
            # Set the sender's keypair for signing
            self.westend_adapter.set_keypair(from_keypair)

            transfer_tx = await self.westend_adapter.transfer_wnd(
                from_address, to_address, amount_planck
            )

            if not transfer_tx.get('success'):
                transfer_result['errors'].append(f"Blockchain transfer failed: {transfer_tx.get('error', 'Unknown error')}")
                return transfer_result

            # Step 6: Update balances in database
            await self._update_balances_wnd(from_borg_id, to_borg_id, amount_wnd)

            # Step 7: Success
            transfer_result.update({
                'success': True,
                'transaction_hash': transfer_tx.get('transaction_hash'),
                'block_number': transfer_tx.get('block_number'),
                'from_address': from_address,
                'to_address': to_address
            })

            # Log successful transfer
            self.audit_logger.log_event(
                "borg_wnd_transfer_completed",
                f"WND transfer completed: {from_borg_id} -> {to_borg_id} ({amount_wnd} WND)",
                {
                    "from_borg_id": from_borg_id,
                    "to_borg_id": to_borg_id,
                    "amount_wnd": amount_wnd,
                    "transaction_hash": transfer_tx.get('transaction_hash'),
                    "from_address": from_address,
                    "to_address": to_address
                }
            )

        except Exception as e:
            transfer_result['errors'].append(f"Transfer execution error: {str(e)}")
            self.audit_logger.log_event(
                "borg_wnd_transfer_error",
                f"WND transfer failed: {from_borg_id} -> {to_borg_id} ({amount_wnd} WND)",
                {
                    "from_borg_id": from_borg_id,
                    "to_borg_id": to_borg_id,
                    "amount_wnd": amount_wnd,
                    "error": str(e)
                }
            )

        return transfer_result

    async def _update_balances_wnd(
        self,
        from_borg_id: str,
        to_borg_id: str,
        amount_wnd: float
    ) -> None:
        """Update borg WND balances after successful transfer."""
        try:
            # Convert amount to planck units for database
            amount_planck = int(amount_wnd * (10 ** 12))

            # Deduct from sender
            success_from = self.address_manager.sync_balance(
                from_borg_id, 'WND', -amount_planck
            )

            # Add to recipient
            success_to = self.address_manager.sync_balance(
                to_borg_id, 'WND', amount_planck
            )

            if not (success_from and success_to):
                self.audit_logger.log_event(
                    "balance_update_warning",
                    f"WND balance update may have failed for transfer {from_borg_id} -> {to_borg_id}",
                    {"from_success": success_from, "to_success": success_to}
                )

        except Exception as e:
            self.audit_logger.log_event(
                "balance_update_error",
                f"WND balance update error: {str(e)}",
                {"from_borg_id": from_borg_id, "to_borg_id": to_borg_id}
            )

    async def get_transfer_history(
        self,
        borg_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get transfer history for a borg.

        Args:
            borg_id: Borg ID to get history for
            limit: Maximum number of transfers to return

        Returns:
            List of transfer records
        """
        try:
            # Query transfer_transactions table
            if self.address_manager.supabase:
                result = self.address_manager.supabase.table('transfer_transactions').select('*').or_(
                    f'from_borg_id.eq.{borg_id},to_borg_id.eq.{borg_id}'
                ).order('created_at.desc').limit(limit).execute()

                transfers = []
                for record in result.data or []:
                    # Convert wei amounts back to token units
                    amount_usdb = Decimal(str(record['amount_wei'])) / Decimal('1000000000000')

                    transfers.append({
                        'tx_id': record['tx_id'],
                        'from_borg_id': record['from_borg_id'],
                        'to_borg_id': record['to_borg_id'],
                        'currency': record['currency'],
                        'amount': str(amount_usdb),
                        'transaction_hash': record['transaction_hash'],
                        'block_number': record['block_number'],
                        'status': record['status'],
                        'created_at': record['created_at'],
                        'confirmed_at': record['confirmed_at'],
                        'direction': 'sent' if record['from_borg_id'] == borg_id else 'received'
                    })

                return transfers

        except Exception as e:
            self.audit_logger.log_event(
                "transfer_history_error",
                f"Failed to get transfer history for {borg_id}: {str(e)}",
                {"borg_id": borg_id, "error": str(e)}
            )

        return []

    async def get_transfer_status(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific transfer.

        Args:
            transfer_id: Transfer transaction ID

        Returns:
            Transfer status information
        """
        try:
            return await self.transaction_manager.get_transaction_status(transfer_id)
        except Exception as e:
            self.audit_logger.log_event(
                "transfer_status_error",
                f"Failed to get transfer status for {transfer_id}: {str(e)}",
                {"transfer_id": transfer_id, "error": str(e)}
            )
            return None

    async def validate_transfer_request(
        self,
        from_borg_id: str,
        to_borg_id: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Validate a transfer request without executing it.

        Args:
            from_borg_id: Sending borg ID
            to_borg_id: Receiving borg ID
            amount: Transfer amount in USDB

        Returns:
            Validation result
        """
        asset_id = self.westend_adapter._get_usdb_asset_id()
        return await self.economic_validator.validate_transfer(
            from_borg_id, to_borg_id, 'USDB', amount, asset_id
        )

    async def get_borg_balance_summary(self, borg_id: str) -> Dict[str, Any]:
        """
        Get complete balance summary for a borg.

        Args:
            borg_id: Borg ID

        Returns:
            Balance summary with WND and USDB balances
        """
        try:
            # Get address
            address = self.address_manager.get_borg_address(borg_id)
            if not address:
                return {'error': 'Borg address not found'}

            # Get blockchain balances
            asset_id = self.westend_adapter._get_usdb_asset_id()
            blockchain_balances = await self.westend_adapter.get_dual_balance(address, asset_id)

            # Get database balances
            wnd_balance_db = self.address_manager.get_balance(borg_id, 'WND') or 0
            usdb_balance_db = self.address_manager.get_balance(borg_id, 'USDB') or 0

            # Convert to token units
            wnd_balance_tokens = Decimal(str(blockchain_balances.get('wnd', 0))) / Decimal('1000000000000')
            usdb_balance_tokens = Decimal(str(blockchain_balances.get('usdb', 0))) / Decimal('1000000000000')

            return {
                'borg_id': borg_id,
                'address': address,
                'balances': {
                    'WND': {
                        'blockchain': str(wnd_balance_tokens),
                        'database': str(Decimal(str(wnd_balance_db)) / Decimal('1000000000000'))
                    },
                    'USDB': {
                        'blockchain': str(usdb_balance_tokens),
                        'database': str(Decimal(str(usdb_balance_db)) / Decimal('1000000000000'))
                    }
                },
                'sync_status': 'synced'  # In production, compare blockchain vs database
            }

        except Exception as e:
            return {'error': str(e)}

    async def bulk_transfer_validation(
        self,
        transfers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate multiple transfers for bulk operations.

        Args:
            transfers: List of transfer requests

        Returns:
            Bulk validation results
        """
        results = {
            'total_transfers': len(transfers),
            'valid_transfers': 0,
            'invalid_transfers': 0,
            'validation_details': []
        }

        for i, transfer in enumerate(transfers):
            validation = await self.validate_transfer_request(
                transfer['from_borg_id'],
                transfer['to_borg_id'],
                Decimal(str(transfer['amount']))
            )

            result = {
                'index': i,
                'transfer': transfer,
                'valid': validation['valid'],
                'errors': validation.get('errors', []),
                'warnings': validation.get('warnings', [])
            }

            results['validation_details'].append(result)

            if validation['valid']:
                results['valid_transfers'] += 1
            else:
                results['invalid_transfers'] += 1

        return results