"""
Kusama Testnet Adapter for BorgLife Phase 1

Provides real blockchain integration with Kusama testnet for Phase 1 validation.
Uses system.remark extrinsics to store DNA hashes on-chain.
"""

import time
from typing import Dict, Any, Optional
from decimal import Decimal
from substrateinterface import SubstrateInterface, Keypair
from .interface import JAMInterface


class KusamaAdapter(JAMInterface):
    """
    Kusama testnet adapter for real blockchain validation.

    Uses system.remark extrinsics to store DNA hashes on Kusama testnet.
    Provides verifiable proof of concept for on-chain DNA storage.
    """

    def __init__(self, rpc_url: str, keypair: Optional[Keypair] = None):
        """
        Initialize Kusama adapter.

        Args:
            rpc_url: Kusama RPC endpoint (e.g., wss://kusama-rpc.polkadot.io)
            keypair: Substrate keypair for signing transactions (optional)
        """
        self.rpc_url = rpc_url
        self.substrate = SubstrateInterface(url=rpc_url)
        self.keypair = keypair

        # In-memory cache for wealth tracking (since Kusama doesn't have native wealth tracking)
        self.wealth_cache: Dict[str, Decimal] = {}
        self.transaction_cache: Dict[str, list] = {}

    async def store_dna_hash(self, borg_id: str, dna_hash: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Store DNA hash on Kusama using system.remark extrinsic.

        Since JAM doesn't exist yet, we use system.remark to store DNA hashes
        in a verifiable way on Kusama testnet.
        """
        if not self.keypair:
            raise ValueError("Keypair required for Kusama transactions")

        # Create remark data: BORGLIFE:<borg_id>:<dna_hash>
        remark_data = f"BORGLIFE:{borg_id}:{dna_hash}"

        # Add metadata if provided
        if metadata:
            remark_data += f":{metadata}"

        try:
            # Create and sign extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=self.substrate.compose_call(
                    call_module='System',
                    call_function='remark',
                    call_params={'remark': remark_data.encode('utf-8')}
                ),
                keypair=self.keypair
            )

            # Submit and wait for inclusion
            receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

            if receipt.is_success:
                # Calculate mock gas cost (simplified)
                gas_cost = Decimal('0.001')  # Fixed cost for Phase 1

                return {
                    'success': True,
                    'block': receipt.block_hash,
                    'transaction_hash': receipt.extrinsic_hash,
                    'cost': gas_cost,
                    'timestamp': time.time(),
                    'kusama_block_number': receipt.block_number
                }
            else:
                return {
                    'success': False,
                    'error': f"Transaction failed: {receipt.error_message}",
                    'cost': Decimal('0')
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'cost': Decimal('0')
            }

    async def retrieve_dna_hash(self, borg_id: str) -> Optional[str]:
        """
        Retrieve DNA hash from Kusama blockchain.

        This is complex as we'd need to scan blocks for system.remark extrinsics.
        For Phase 1, this is a simplified implementation.
        """
        # Note: Real implementation would require block scanning
        # For Phase 1 demo, we use a cache or simplified lookup
        # In production, this would query the blockchain directly

        # Placeholder implementation - would need indexer or block scanning
        # For demo purposes, return None (not implemented for Phase 1)
        return None

    async def verify_dna_integrity(self, borg_id: str, expected_hash: str) -> bool:
        """
        Verify DNA integrity on Kusama.

        For Phase 1, this is a placeholder. Real implementation would
        scan recent blocks for the borg's DNA hash.
        """
        retrieved_hash = await self.retrieve_dna_hash(borg_id)
        return retrieved_hash == expected_hash if retrieved_hash else False

    async def get_wealth_balance(self, borg_id: str) -> Decimal:
        """
        Get wealth balance from cache (Kusama doesn't have native wealth tracking).
        """
        return self.wealth_cache.get(borg_id, Decimal('0'))

    async def update_wealth(self, borg_id: str, amount: Decimal, operation: str, description: str) -> bool:
        """
        Update wealth balance in local cache.
        """
        if borg_id not in self.wealth_cache:
            self.wealth_cache[borg_id] = Decimal('0')

        # Update balance
        if operation in ['revenue', 'transfer']:
            self.wealth_cache[borg_id] += amount
        elif operation == 'cost':
            self.wealth_cache[borg_id] -= amount
        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Log transaction
        if borg_id not in self.transaction_cache:
            self.transaction_cache[borg_id] = []

        transaction = {
            'timestamp': time.time(),
            'operation': operation,
            'amount': float(amount),
            'description': description,
            'balance_after': float(self.wealth_cache[borg_id])
        }

        self.transaction_cache[borg_id].append(transaction)

        return True

    async def get_transaction_history(self, borg_id: str, limit: int = 50) -> list:
        """
        Get transaction history from cache.
        """
        history = self.transaction_cache.get(borg_id, [])
        return history[-limit:] if limit > 0 else history

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Kusama connection health.
        """
        try:
            # Test connection by getting chain name
            chain_name = self.substrate.get_chain_name()
            block_number = self.substrate.get_block_number()

            return {
                'status': 'healthy',
                'mode': 'kusama_testnet',
                'chain_name': chain_name,
                'block_number': block_number,
                'rpc_url': self.rpc_url,
                'keypair_configured': self.keypair is not None,
                'cached_wealth_records': len(self.wealth_cache)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'mode': 'kusama_testnet',
                'error': str(e),
                'rpc_url': self.rpc_url
            }

    def set_keypair(self, keypair: Keypair):
        """Set the keypair for signing transactions."""
        self.keypair = keypair

    def set_keypair_from_seed(self, seed: str):
        """Set keypair from seed phrase."""
        self.keypair = Keypair.create_from_seed(seed)

    def set_keypair_from_uri(self, uri: str):
        """Set keypair from URI (seed or mnemonic)."""
        self.keypair = Keypair.create_from_uri(uri)