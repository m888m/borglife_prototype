"""
JAM Interface for BorgLife Phase 1

Abstract interface defining JAM (Join-Accumulate Machine) operations
for DNA storage and retrieval. Supports both mock and real implementations.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Union


class JAMMode(Enum):
    """JAM operation modes."""

    MOCK = "mock"  # In-memory simulation
    TESTNET = "testnet"  # Real Kusama testnet
    MAINNET = "mainnet"  # Polkadot mainnet (future)


class JAMInterface(ABC):
    """Abstract interface for JAM operations."""

    pass


class JAMMockInterface(JAMInterface):
    """
    Abstract interface for JAM operations.

    JAM (Join-Accumulate Machine) provides trustless execution via
    refine/accumulate phases for DNA storage and wealth tracking.

    Supports configuration switching between mock and testnet modes.
    """

    @abstractmethod
    async def store_dna_hash(
        self, borg_id: str, dna_hash: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store DNA hash on-chain (accumulate phase).

        Args:
            borg_id: Unique identifier for the borg
            dna_hash: Blake2 hash of the DNA structure H(D)
            metadata: Optional metadata (wealth tracking, gas limits, etc.)

        Returns:
            Dict containing:
            - success: bool
            - block: block number/hash
            - transaction_hash: transaction identifier
            - cost: execution cost in DOT
        """
        pass

    @abstractmethod
    async def retrieve_dna_hash(self, borg_id: str) -> Optional[str]:
        """
        Retrieve DNA hash from chain (refine phase).

        Args:
            borg_id: Unique identifier for the borg

        Returns:
            DNA hash string if found, None otherwise
        """
        pass

    @abstractmethod
    async def verify_dna_integrity(self, borg_id: str, expected_hash: str) -> bool:
        """
        Verify DNA integrity: H(D') = H(D)

        Args:
            borg_id: Unique identifier for the borg
            expected_hash: Expected DNA hash

        Returns:
            True if hashes match, False otherwise
        """
        pass

    @abstractmethod
    async def get_wealth_balance(self, borg_id: str) -> Decimal:
        """
        Get current wealth balance Δ(W) = R - C

        Args:
            borg_id: Unique identifier for the borg

        Returns:
            Current wealth balance in DOT
        """
        pass

    @abstractmethod
    async def update_wealth(
        self, borg_id: str, amount: Decimal, operation: str, description: str
    ) -> bool:
        """
        Update wealth balance (accumulate phase).

        Args:
            borg_id: Unique identifier for the borg
            amount: Amount to add/subtract (positive = revenue, negative = cost)
            operation: Operation type ("revenue", "cost", "transfer")
            description: Human-readable description

        Returns:
            True if update successful
        """
        pass

    @abstractmethod
    async def get_transaction_history(self, borg_id: str, limit: int = 50) -> list:
        """
        Get transaction history for wealth tracking.

        Args:
            borg_id: Unique identifier for the borg
            limit: Maximum number of transactions to return

        Returns:
            List of transaction records
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check JAM service health.

        Returns:
            Dict with health status information
        """
        pass

    @abstractmethod
    def get_mode(self) -> JAMMode:
        """
        Get current JAM operation mode.

        Returns:
            Current mode (MOCK, TESTNET, or MAINNET)
        """
        pass

    @abstractmethod
    def set_mode(self, mode: JAMMode) -> bool:
        """
        Set JAM operation mode.

        Args:
            mode: New mode to switch to

        Returns:
            True if mode switch successful
        """
        pass

    @abstractmethod
    async def configure_testnet(
        self, rpc_url: str, keypair_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Configure testnet mode parameters.

        Args:
            rpc_url: Kusama testnet RPC endpoint
            keypair_data: Keypair configuration (seed, URI, etc.)

        Returns:
            True if configuration successful
        """
        pass

    @abstractmethod
    async def retrieve_dna_hash_from_blockchain(
        self, borg_id: str, block_range: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve DNA hash from blockchain with full transaction details.

        Enhanced version of retrieve_dna_hash that provides complete blockchain data.

        Args:
            borg_id: Unique identifier for the borg
            block_range: Optional (start_block, end_block) to limit search

        Returns:
            Dict with DNA hash and blockchain metadata, or None if not found:
            {
                'dna_hash': str,
                'block_number': int,
                'block_hash': str,
                'transaction_hash': str,
                'timestamp': int,
                'confirmation_count': int
            }
        """
        pass

    @abstractmethod
    async def verify_dna_integrity_with_proof(
        self, borg_id: str, expected_hash: str
    ) -> Dict[str, Any]:
        """
        Verify DNA integrity with cryptographic proof.

        Enhanced version that provides verification proof for on-chain validation.

        Args:
            borg_id: Unique identifier for the borg
            expected_hash: Expected DNA hash

        Returns:
            Dict with verification results and proof:
            {
                'verified': bool,
                'expected_hash': str,
                'actual_hash': str,
                'block_number': int,
                'transaction_hash': str,
                'proof_data': Dict[str, Any],  # Cryptographic proof
                'timestamp': int
            }
        """
        pass
