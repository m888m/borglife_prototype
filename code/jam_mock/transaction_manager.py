"""
Transaction Manager for Westend Testnet Operations

Provides comprehensive transaction validation, signing, submission, and monitoring
for BorgLife DNA storage operations on Westend testnet.
"""

import asyncio
import time
import hashlib
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from substrateinterface import SubstrateInterface, Keypair
from .advanced_keypair_features import AdvancedKeypairManager, TransactionSigner


class TransactionStatus(Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TransactionType(Enum):
    """Transaction type enumeration."""
    DNA_STORAGE = "dna_storage"
    WEALTH_UPDATE = "wealth_update"
    BATCH_OPERATION = "batch_operation"
    TRANSFER = "transfer"           # WND transfers
    ASSET_TRANSFER = "asset_transfer"  # USDB transfers


@dataclass
class TransactionRecord:
    """Transaction record for tracking and auditing."""
    tx_id: str
    borg_id: str
    transaction_type: TransactionType
    status: TransactionStatus
    created_at: datetime
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    block_number: Optional[int] = None
    block_hash: Optional[str] = None
    transaction_hash: Optional[str] = None
    fee_paid: Optional[Decimal] = None
    gas_used: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    # Phase 2A: Transfer-specific fields
    from_borg_id: Optional[str] = None
    to_borg_id: Optional[str] = None
    currency: Optional[str] = None  # 'WND' or 'USDB'
    transfer_amount: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert enums to strings
        data['transaction_type'] = self.transaction_type.value
        data['status'] = self.status.value
        # Convert datetime to ISO string
        for field in ['created_at', 'submitted_at', 'confirmed_at']:
            if data[field]:
                data[field] = data[field].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionRecord':
        """Create from dictionary."""
        # Convert strings back to enums
        data['transaction_type'] = TransactionType(data['transaction_type'])
        data['status'] = TransactionStatus(data['status'])
        # Convert ISO strings back to datetime
        for field in ['created_at', 'submitted_at', 'confirmed_at']:
            if data[field]:
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)


class TransactionValidationError(Exception):
    """Raised when transaction validation fails."""
    pass


class TransactionManager:
    """
    Comprehensive transaction manager for Westend operations.

    Handles validation, signing, submission, monitoring, and recovery
    for all BorgLife blockchain transactions.
    """

    def __init__(
        self,
        westend_adapter,
        keypair_manager: AdvancedKeypairManager,
        confirmation_timeout_seconds: int = 300,  # 5 minutes
        max_retry_attempts: int = 3
    ):
        self.westend_adapter = westend_adapter
        self.keypair_manager = keypair_manager
        self.transaction_signer = TransactionSigner(keypair_manager)

        # Configuration
        self.confirmation_timeout = timedelta(seconds=confirmation_timeout_seconds)
        self.max_retry_attempts = max_retry_attempts

        # Transaction tracking
        self.pending_transactions: Dict[str, TransactionRecord] = {}
        self.completed_transactions: Dict[str, TransactionRecord] = {}
        self.failed_transactions: Dict[str, TransactionRecord] = {}

        # Monitoring
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

    async def start_monitoring(self):
        """Start transaction monitoring loop."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitor_transactions())
        print("✅ Transaction monitoring started")

    async def stop_monitoring(self):
        """Stop transaction monitoring."""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        print("✅ Transaction monitoring stopped")

    def validate_transaction_comprehensive(
        self,
        borg_id: str,
        transaction_data: Dict[str, Any],
        keypair_name: str
    ) -> Dict[str, Any]:
        """
        Comprehensive transaction validation.

        Args:
            borg_id: Borg identifier
            transaction_data: Transaction details
            keypair_name: Keypair to use

        Returns:
            Validation results with detailed checks
        """
        validation_results = {
            'valid': True,
            'checks': {},
            'warnings': [],
            'errors': [],
            'recommendations': []
        }

        # Basic validation using keypair manager
        basic_validation = self.keypair_manager.validate_transaction(keypair_name, transaction_data)
        validation_results['checks']['basic'] = basic_validation

        if not basic_validation['valid']:
            validation_results['valid'] = False
            validation_results['errors'].extend(basic_validation['errors'])

        # Borg ID validation
        if not self._validate_borg_id(borg_id):
            validation_results['errors'].append(f"Invalid borg ID format: {borg_id}")
            validation_results['valid'] = False

        # Transaction type validation
        tx_type = transaction_data.get('type', 'dna_storage')
        if tx_type not in [t.value for t in TransactionType]:
            validation_results['errors'].append(f"Invalid transaction type: {tx_type}")
            validation_results['valid'] = False

        # DNA hash validation (for DNA storage)
        if tx_type == 'dna_storage':
            dna_hash = transaction_data.get('dna_hash')
            if not dna_hash or not self._is_valid_hash(dna_hash):
                validation_results['errors'].append("Invalid or missing DNA hash")
                validation_results['valid'] = False

        # Fee estimation and validation
        fee_info = self.keypair_manager.estimate_transaction_fee(keypair_name, transaction_data)
        validation_results['checks']['fee'] = fee_info

        if 'error' in fee_info:
            validation_results['warnings'].append(f"Fee estimation failed: {fee_info['error']}")
        else:
            estimated_fee = fee_info.get('estimated_fee', Decimal('0'))
            max_fee = self.keypair_manager.max_transaction_fee

            if estimated_fee > max_fee:
                validation_results['errors'].append(
                    f"Estimated fee {estimated_fee} WND exceeds maximum {max_fee} WND"
                )
                validation_results['valid'] = False
            elif estimated_fee > max_fee * Decimal('0.8'):
                validation_results['warnings'].append(
                    f"High fee: {estimated_fee} WND (close to maximum {max_fee} WND)"
                )

        # Network health check
        try:
            health = asyncio.run(self.westend_adapter.health_check())
            validation_results['checks']['network'] = health

            if health.get('status') != 'healthy':
                validation_results['warnings'].append("Network health check failed")
        except Exception as e:
            validation_results['warnings'].append(f"Network check error: {e}")

        # Add recommendations
        if validation_results['valid']:
            validation_results['recommendations'].append("Transaction ready for submission")
        else:
            validation_results['recommendations'].append("Fix validation errors before submission")

        return validation_results

    async def submit_transaction(
        self,
        borg_id: str,
        transaction_data: Dict[str, Any],
        keypair_name: str,
        wait_for_confirmation: bool = True
    ) -> Dict[str, Any]:
        """
        Submit a transaction with comprehensive validation and monitoring.

        Args:
            borg_id: Borg identifier
            transaction_data: Transaction details
            keypair_name: Keypair to use for signing
            wait_for_confirmation: Whether to wait for confirmation

        Returns:
            Transaction submission results
        """
        # Generate transaction ID
        tx_id = self._generate_transaction_id(borg_id, transaction_data)

        # Comprehensive validation
        validation = self.validate_transaction_comprehensive(borg_id, transaction_data, keypair_name)

        if not validation['valid']:
            return {
                'success': False,
                'tx_id': tx_id,
                'error': 'Validation failed',
                'validation_errors': validation['errors'],
                'validation_warnings': validation['warnings']
            }

        # Create transaction record
        tx_record = TransactionRecord(
            tx_id=tx_id,
            borg_id=borg_id,
            transaction_type=TransactionType(transaction_data.get('type', 'dna_storage')),
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        )

        # Add to pending transactions
        self.pending_transactions[tx_id] = tx_record

        try:
            # Submit transaction
            tx_record.status = TransactionStatus.SUBMITTED
            tx_record.submitted_at = datetime.utcnow()

            result = await self.transaction_signer.sign_and_submit_transaction(
                keypair_name, transaction_data, self.westend_adapter
            )

            if result.get('success'):
                tx_record.status = TransactionStatus.CONFIRMED
                tx_record.confirmed_at = datetime.utcnow()
                tx_record.transaction_hash = result.get('transaction_hash')
                tx_record.block_hash = result.get('block')
                tx_record.block_number = result.get('westend_block_number')
                tx_record.fee_paid = result.get('cost', Decimal('0'))

                # Move to completed
                self.completed_transactions[tx_id] = tx_record
                del self.pending_transactions[tx_id]

                return {
                    'success': True,
                    'tx_id': tx_id,
                    'transaction_hash': tx_record.transaction_hash,
                    'block_number': tx_record.block_number,
                    'fee_paid': tx_record.fee_paid,
                    'validation_warnings': validation['warnings']
                }
            else:
                # Handle submission failure
                tx_record.status = TransactionStatus.FAILED
                tx_record.error_message = result.get('error', 'Unknown error')
                tx_record.retry_count += 1

                # Check if we should retry
                if tx_record.retry_count < tx_record.max_retries:
                    # Move back to pending for retry
                    pass  # Will be retried by monitoring loop
                else:
                    # Move to failed
                    self.failed_transactions[tx_id] = tx_record
                    del self.pending_transactions[tx_id]

                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': tx_record.error_message,
                    'retry_count': tx_record.retry_count,
                    'max_retries': tx_record.max_retries
                }

        except Exception as e:
            tx_record.status = TransactionStatus.FAILED
            tx_record.error_message = str(e)

            self.failed_transactions[tx_id] = tx_record
            del self.pending_transactions[tx_id]

            return {
                'success': False,
                'tx_id': tx_id,
                'error': str(e)
            }

    async def get_transaction_status(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a transaction.

        Args:
            tx_id: Transaction ID

        Returns:
            Transaction status information
        """
        # Check all transaction stores
        for store in [self.pending_transactions, self.completed_transactions, self.failed_transactions]:
            if tx_id in store:
                record = store[tx_id]
                status_info = record.to_dict()

                # Add additional computed fields
                if record.status == TransactionStatus.CONFIRMED:
                    if record.confirmed_at and record.submitted_at:
                        confirmation_time = record.confirmed_at - record.submitted_at
                        status_info['confirmation_time_seconds'] = confirmation_time.total_seconds()

                return status_info

        return None

    async def cancel_transaction(self, tx_id: str) -> bool:
        """
        Cancel a pending transaction.

        Args:
            tx_id: Transaction ID

        Returns:
            True if cancelled successfully
        """
        if tx_id in self.pending_transactions:
            record = self.pending_transactions[tx_id]
            record.status = TransactionStatus.CANCELLED
            record.error_message = "Cancelled by user"

            self.failed_transactions[tx_id] = record
            del self.pending_transactions[tx_id]
            return True

        return False

    async def retry_failed_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """
        Retry a failed transaction.

        Args:
            tx_id: Transaction ID

        Returns:
            New transaction results if retry was attempted
        """
        if tx_id not in self.failed_transactions:
            return None

        record = self.failed_transactions[tx_id]

        if record.retry_count >= record.max_retries:
            return {'error': 'Max retries exceeded'}

        # Move back to pending for retry
        record.retry_count += 1
        record.status = TransactionStatus.PENDING
        record.error_message = None

        self.pending_transactions[tx_id] = record
        del self.failed_transactions[tx_id]

        return {'status': 'retry_queued', 'retry_count': record.retry_count}

    def get_transaction_statistics(self) -> Dict[str, Any]:
        """Get comprehensive transaction statistics."""
        now = datetime.utcnow()

        # Calculate statistics
        total_submitted = len(self.completed_transactions) + len(self.failed_transactions) + len(self.pending_transactions)
        successful = len(self.completed_transactions)
        failed = len(self.failed_transactions)
        pending = len(self.pending_transactions)

        # Success rate
        success_rate = (successful / total_submitted * 100) if total_submitted > 0 else 0

        # Average confirmation time
        confirmation_times = []
        for record in self.completed_transactions.values():
            if record.confirmed_at and record.submitted_at:
                confirmation_times.append((record.confirmed_at - record.submitted_at).total_seconds())

        avg_confirmation_time = sum(confirmation_times) / len(confirmation_times) if confirmation_times else 0

        # Fee statistics
        fees = [record.fee_paid for record in self.completed_transactions.values() if record.fee_paid]
        avg_fee = sum(fees) / len(fees) if fees else Decimal('0')
        total_fees = sum(fees) if fees else Decimal('0')

        return {
            'total_transactions': total_submitted,
            'successful': successful,
            'failed': failed,
            'pending': pending,
            'success_rate_percent': round(success_rate, 2),
            'avg_confirmation_time_seconds': round(avg_confirmation_time, 2),
            'avg_fee_ksm': float(avg_fee),
            'total_fees_ksm': float(total_fees),
            'timestamp': now.isoformat()
        }

    async def _monitor_transactions(self):
        """Monitor pending transactions for confirmation."""
        while self.monitoring_active:
            try:
                # Check each pending transaction
                tx_ids_to_remove = []

                for tx_id, record in list(self.pending_transactions.items()):
                    # Check if transaction has timed out
                    if record.submitted_at:
                        elapsed = datetime.utcnow() - record.submitted_at
                        if elapsed > self.confirmation_timeout:
                            record.status = TransactionStatus.TIMEOUT
                            record.error_message = f"Confirmation timeout after {elapsed.total_seconds()} seconds"
                            self.failed_transactions[tx_id] = record
                            tx_ids_to_remove.append(tx_id)
                            continue

                    # For submitted transactions, check confirmation status
                    if record.status == TransactionStatus.SUBMITTED and record.transaction_hash:
                        # In a real implementation, we would query the blockchain
                        # For now, simulate confirmation after some time
                        if record.submitted_at:
                            elapsed = datetime.utcnow() - record.submitted_at
                            if elapsed.total_seconds() > 10:  # Simulate 10 second confirmation
                                record.status = TransactionStatus.CONFIRMED
                                record.confirmed_at = datetime.utcnow()
                                record.block_number = 1000000  # Mock block number
                                record.block_hash = "0x" + "a" * 64  # Mock block hash

                                self.completed_transactions[tx_id] = record
                                tx_ids_to_remove.append(tx_id)

                # Remove processed transactions
                for tx_id in tx_ids_to_remove:
                    if tx_id in self.pending_transactions:
                        del self.pending_transactions[tx_id]

            except Exception as e:
                print(f"Transaction monitoring error: {e}")

            # Wait before next check
            await asyncio.sleep(5)  # Check every 5 seconds

    def _generate_transaction_id(self, borg_id: str, transaction_data: Dict[str, Any]) -> str:
        """Generate unique transaction ID."""
        # Create deterministic hash from borg_id and transaction data
        data_str = f"{borg_id}:{json.dumps(transaction_data, sort_keys=True)}:{time.time()}"
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _validate_borg_id(self, borg_id: str) -> bool:
        """Validate borg ID format."""
        return bool(borg_id and len(borg_id) <= 50 and borg_id.replace('-', '').replace('_', '').isalnum())

    def _is_valid_hash(self, hash_str: str) -> bool:
        """Validate hash format."""
        if len(hash_str) != 64:
            return False
        try:
            int(hash_str, 16)
            return True
        except ValueError:
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_monitoring()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_monitoring()