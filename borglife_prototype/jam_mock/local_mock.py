"""
Local JAM Mock for BorgLife Phase 1 Development

Provides in-memory simulation of JAM operations for rapid development
and testing without blockchain dependencies.
"""

import time
import json
from typing import Dict, Any, Optional
from decimal import Decimal
from .interface import JAMInterface


class LocalJAMMock(JAMInterface):
    """
    Local in-memory mock of JAM functionality.

    Simulates JAM's refine/accumulate phases for DNA storage and wealth tracking.
    Perfect for development iteration and unit testing.
    """

    def __init__(self, persistence_file: Optional[str] = None):
        """
        Initialize local JAM mock.

        Args:
            persistence_file: Optional file path for data persistence across restarts
        """
        self.dna_storage: Dict[str, Dict[str, Any]] = {}
        self.wealth_balances: Dict[str, Decimal] = {}
        self.transaction_history: Dict[str, list] = {}
        self.block_height = 0
        self.persistence_file = persistence_file

        # Load persisted data if available
        if persistence_file:
            self._load_persistence()

    async def store_dna_hash(self, borg_id: str, dna_hash: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Simulate JAM accumulate phase for DNA storage.
        """
        self.block_height += 1
        timestamp = time.time()

        dna_record = {
            'dna_hash': dna_hash,
            'block': self.block_height,
            'timestamp': timestamp,
            'borg_id': borg_id,
            'metadata': metadata or {}
        }

        self.dna_storage[borg_id] = dna_record

        # Persist if configured
        if self.persistence_file:
            self._save_persistence()

        return {
            'success': True,
            'block': self.block_height,
            'transaction_hash': f"mock_tx_{borg_id}_{self.block_height}",
            'cost': Decimal('0.001'),  # Mock gas cost
            'timestamp': timestamp
        }

    async def retrieve_dna_hash(self, borg_id: str) -> Optional[str]:
        """
        Simulate JAM refine phase for DNA retrieval.
        """
        dna_record = self.dna_storage.get(borg_id)
        return dna_record['dna_hash'] if dna_record else None

    async def verify_dna_integrity(self, borg_id: str, expected_hash: str) -> bool:
        """
        Verify DNA integrity: H(D') = H(D)
        """
        stored_hash = await self.retrieve_dna_hash(borg_id)
        return stored_hash == expected_hash if stored_hash else False

    async def get_wealth_balance(self, borg_id: str) -> Decimal:
        """
        Get current wealth balance Δ(W) = R - C
        """
        return self.wealth_balances.get(borg_id, Decimal('0'))

    async def update_wealth(self, borg_id: str, amount: Decimal, operation: str, description: str) -> bool:
        """
        Update wealth balance with transaction logging.
        """
        if borg_id not in self.wealth_balances:
            self.wealth_balances[borg_id] = Decimal('0')

        # Update balance
        if operation in ['revenue', 'transfer']:
            self.wealth_balances[borg_id] += amount
        elif operation == 'cost':
            self.wealth_balances[borg_id] -= amount
        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Log transaction
        if borg_id not in self.transaction_history:
            self.transaction_history[borg_id] = []

        transaction = {
            'timestamp': time.time(),
            'operation': operation,
            'amount': float(amount),
            'description': description,
            'balance_after': float(self.wealth_balances[borg_id])
        }

        self.transaction_history[borg_id].append(transaction)

        # Persist if configured
        if self.persistence_file:
            self._save_persistence()

        return True

    async def get_transaction_history(self, borg_id: str, limit: int = 50) -> list:
        """
        Get transaction history for wealth tracking.
        """
        history = self.transaction_history.get(borg_id, [])
        return history[-limit:] if limit > 0 else history

    async def health_check(self) -> Dict[str, Any]:
        """
        Check local mock health.
        """
        return {
            'status': 'healthy',
            'mode': 'local_mock',
            'dna_records': len(self.dna_storage),
            'borgs_with_wealth': len(self.wealth_balances),
            'total_transactions': sum(len(txns) for txns in self.transaction_history.values()),
            'block_height': self.block_height,
            'persistence_enabled': self.persistence_file is not None
        }

    def _save_persistence(self):
        """Save state to persistence file."""
        if not self.persistence_file:
            return

        data = {
            'dna_storage': self.dna_storage,
            'wealth_balances': {k: float(v) for k, v in self.wealth_balances.items()},
            'transaction_history': self.transaction_history,
            'block_height': self.block_height
        }

        try:
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save persistence: {e}")

    def _load_persistence(self):
        """Load state from persistence file."""
        if not self.persistence_file:
            return

        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)

            self.dna_storage = data.get('dna_storage', {})
            self.wealth_balances = {k: Decimal(str(v)) for k, v in data.get('wealth_balances', {}).items()}
            self.transaction_history = data.get('transaction_history', {})
            self.block_height = data.get('block_height', 0)
        except FileNotFoundError:
            # First run, no persistence file yet
            pass
        except Exception as e:
            print(f"Warning: Failed to load persistence: {e}")