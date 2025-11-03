"""
Kusama Testnet Adapter for BorgLife Phase 1

Provides real blockchain integration with Kusama testnet for Phase 1 validation.
Uses system.remark extrinsics to store DNA hashes on-chain.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from decimal import Decimal
from substrateinterface import SubstrateInterface, Keypair
from .interface import JAMInterface, JAMMode


class KusamaAdapter(JAMInterface):
    """
    Kusama testnet adapter for real blockchain validation.

    Uses system.remark extrinsics to store DNA hashes on Kusama testnet.
    Provides verifiable proof of concept for on-chain DNA storage.
    """

    def __init__(self, rpc_url: str, keypair: Optional[Keypair] = None, connect_immediately: bool = True):
        """
        Initialize Kusama adapter.

        Args:
            rpc_url: Kusama RPC endpoint (e.g., wss://kusama-rpc.polkadot.io)
            keypair: Substrate keypair for signing transactions (optional)
            connect_immediately: Whether to connect to RPC immediately (default: True)
        """
        self.rpc_url = rpc_url
        self.keypair = keypair
        self.mode = JAMMode.TESTNET

        # In-memory cache for wealth tracking (since Kusama doesn't have native wealth tracking)
        self.wealth_cache: Dict[str, Decimal] = {}
        self.transaction_cache: Dict[str, list] = {}

        # Block scanning configuration
        self.max_scan_blocks = 1000  # Maximum blocks to scan in one operation
        self.scan_batch_size = 10    # Blocks to scan per batch
        self.scan_delay = 0.1        # Delay between batches to avoid rate limiting

        # Transaction cache for faster lookups
        self.tx_cache: Dict[str, Dict[str, Any]] = {}  # tx_hash -> tx_data

        # Initialize substrate connection
        self.substrate = None
        if connect_immediately:
            try:
                self.substrate = SubstrateInterface(url=rpc_url)
            except Exception as e:
                print(f"Warning: Failed to connect to Kusama RPC: {e}")
                print("Adapter will work in offline mode for some operations")

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
        Retrieve DNA hash from Kusama blockchain by scanning recent blocks.

        Scans recent blocks for system.remark extrinsics containing BORGLIFE data.
        """
        if not self.substrate:
            print("No substrate connection available")
            return None

        try:
            # Get current block number
            current_block = self.substrate.get_block_number()

            # Scan recent blocks (last 1000 blocks should be sufficient for Phase 1)
            scan_range = min(self.max_scan_blocks, current_block)
            start_block = max(0, current_block - scan_range)

            dna_hash = await self._scan_blocks_for_dna_hash(borg_id, start_block, current_block)
            return dna_hash

        except Exception as e:
            print(f"Error retrieving DNA hash for {borg_id}: {e}")
            return None

    async def _scan_blocks_for_dna_hash(self, borg_id: str, start_block: int, end_block: int) -> Optional[str]:
        """
        Scan block range for DNA hash in system.remark extrinsics.
        """
        # Process blocks in batches to avoid overwhelming the RPC
        for batch_start in range(start_block, end_block + 1, self.scan_batch_size):
            batch_end = min(batch_start + self.scan_batch_size - 1, end_block)

            # Scan this batch of blocks
            for block_number in range(batch_start, batch_end + 1):
                try:
                    dna_hash = await self._scan_single_block_for_dna_hash(borg_id, block_number)
                    if dna_hash:
                        return dna_hash

                    # Small delay to be respectful to RPC
                    await asyncio.sleep(self.scan_delay)

                except Exception as e:
                    print(f"Error scanning block {block_number}: {e}")
                    continue

        return None

    async def _scan_single_block_for_dna_hash(self, borg_id: str, block_number: int) -> Optional[str]:
        """
        Scan a single block for BORGLIFE system.remark extrinsics.
        """
        try:
            # Get block data
            block = self.substrate.get_block(block_number=block_number)

            if not block or 'extrinsics' not in block:
                return None

            # Check each extrinsic in the block
            for extrinsic in block['extrinsics']:
                dna_hash = self._extract_dna_hash_from_extrinsic(extrinsic, borg_id)
                if dna_hash:
                    return dna_hash

        except Exception as e:
            print(f"Error scanning block {block_number}: {e}")

        return None

    def _extract_dna_hash_from_extrinsic(self, extrinsic: Dict[str, Any], borg_id: str) -> Optional[str]:
        """
        Extract DNA hash from a system.remark extrinsic if it matches our format.
        """
        try:
            # Check if this is a system.remark extrinsic
            if (extrinsic.get('call', {}).get('call_module') == 'System' and
                extrinsic.get('call', {}).get('call_function') == 'remark'):

                # Get the remark data
                remark_bytes = extrinsic['call']['call_args']['remark']
                if isinstance(remark_bytes, str):
                    remark_data = remark_bytes
                else:
                    remark_data = bytes(remark_bytes).decode('utf-8', errors='ignore')

                # Check if it starts with our BORGLIFE prefix
                if remark_data.startswith('BORGLIFE:'):
                    parts = remark_data.split(':')
                    if len(parts) >= 3 and parts[1] == borg_id:
                        # Extract DNA hash (parts[2])
                        dna_hash = parts[2]
                        # Validate it's a proper hash (64 characters, hex)
                        if len(dna_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in dna_hash):
                            return dna_hash

        except Exception as e:
            # Silently ignore parsing errors
            pass

        return None

    async def verify_dna_integrity(self, borg_id: str, expected_hash: str) -> bool:
        """
        Verify DNA integrity on Kusama by retrieving and comparing hashes.
        """
        retrieved_hash = await self.retrieve_dna_hash(borg_id)
        return retrieved_hash == expected_hash if retrieved_hash else False

    async def get_transaction_by_hash(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve transaction details by hash from Kusama blockchain.
        """
        try:
            # Check cache first
            if tx_hash in self.tx_cache:
                return self.tx_cache[tx_hash]

            # Query blockchain for transaction
            receipt = self.substrate.get_extrinsic_by_hash(tx_hash)

            if receipt:
                tx_data = {
                    'hash': tx_hash,
                    'block_number': receipt.block_number,
                    'block_hash': receipt.block_hash,
                    'success': receipt.is_success,
                    'timestamp': time.time(),  # Approximate
                    'fee': getattr(receipt, 'fee', None),
                    'borg_data': self._extract_borg_data_from_receipt(receipt)
                }

                # Cache the result
                self.tx_cache[tx_hash] = tx_data
                return tx_data

        except Exception as e:
            print(f"Error retrieving transaction {tx_hash}: {e}")

        return None

    def _extract_borg_data_from_receipt(self, receipt) -> Optional[Dict[str, Any]]:
        """
        Extract BORGLIFE data from transaction receipt.
        """
        try:
            # Get the extrinsic data
            if hasattr(receipt, 'extrinsic'):
                extrinsic = receipt.extrinsic
                borg_data = self._extract_dna_data_from_extrinsic(extrinsic.value)
                return borg_data
        except Exception as e:
            print(f"Error extracting borg data from receipt: {e}")

        return None

    def _extract_dna_data_from_extrinsic(self, extrinsic_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract DNA-related data from extrinsic.
        """
        try:
            # Check if this is a system.remark with BORGLIFE data
            if (extrinsic_data.get('call', {}).get('call_module') == 'System' and
                extrinsic_data.get('call', {}).get('call_function') == 'remark'):

                remark_bytes = extrinsic_data['call']['call_args']['remark']
                if isinstance(remark_bytes, str):
                    remark_data = remark_bytes
                else:
                    remark_data = bytes(remark_bytes).decode('utf-8', errors='ignore')

                if remark_data.startswith('BORGLIFE:'):
                    parts = remark_data.split(':')
                    if len(parts) >= 3:
                        return {
                            'borg_id': parts[1],
                            'dna_hash': parts[2],
                            'metadata': parts[3] if len(parts) > 3 else None
                        }

        except Exception as e:
            print(f"Error extracting DNA data: {e}")

        return None

    async def scan_block_range_for_borgs(self, start_block: int, end_block: int) -> List[Dict[str, Any]]:
        """
        Scan a range of blocks for all BORGLIFE transactions.
        """
        borg_transactions = []

        try:
            # Limit scan range for performance
            max_range = min(end_block - start_block + 1, self.max_scan_blocks)
            actual_end_block = start_block + max_range - 1

            print(f"Scanning blocks {start_block} to {actual_end_block} for BORGLIFE transactions...")

            for block_number in range(start_block, actual_end_block + 1):
                try:
                    block_borgs = await self._scan_single_block_for_all_borgs(block_number)
                    borg_transactions.extend(block_borgs)

                    # Rate limiting delay
                    await asyncio.sleep(self.scan_delay)

                except Exception as e:
                    print(f"Error scanning block {block_number}: {e}")
                    continue

        except Exception as e:
            print(f"Error in block range scan: {e}")

        return borg_transactions

    async def _scan_single_block_for_all_borgs(self, block_number: int) -> List[Dict[str, Any]]:
        """
        Scan a single block for all BORGLIFE system.remark extrinsics.
        """
        borg_data = []

        try:
            block = self.substrate.get_block(block_number=block_number)

            if not block or 'extrinsics' not in block:
                return borg_data

            for extrinsic in block['extrinsics']:
                borg_info = self._extract_borg_info_from_extrinsic(extrinsic, block_number)
                if borg_info:
                    borg_data.append(borg_info)

        except Exception as e:
            print(f"Error scanning block {block_number}: {e}")

        return borg_data

    def _extract_borg_info_from_extrinsic(self, extrinsic: Dict[str, Any], block_number: int) -> Optional[Dict[str, Any]]:
        """
        Extract complete borg information from extrinsic.
        """
        dna_data = self._extract_dna_data_from_extrinsic(extrinsic)
        if dna_data:
            return {
                'block_number': block_number,
                'borg_id': dna_data['borg_id'],
                'dna_hash': dna_data['dna_hash'],
                'metadata': dna_data.get('metadata'),
                'extrinsic_hash': extrinsic.get('hash'),
                'timestamp': time.time()  # Approximate
            }
        return None

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
        base_info = {
            'mode': self.mode.value,
            'rpc_url': self.rpc_url,
            'keypair_configured': self.keypair is not None,
            'cached_wealth_records': len(self.wealth_cache),
            'cached_transactions': len(self.tx_cache),
            'scan_config': {
                'max_scan_blocks': self.max_scan_blocks,
                'scan_batch_size': self.scan_batch_size,
                'scan_delay': self.scan_delay
            }
        }

        if not self.substrate:
            return {
                'status': 'offline',
                'error': 'No substrate connection',
                **base_info
            }

        try:
            # Test connection by getting chain name
            chain_name = self.substrate.get_chain_name()
            block_number = self.substrate.get_block_number()

            return {
                'status': 'healthy',
                'chain_name': chain_name,
                'block_number': block_number,
                **base_info
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                **base_info
            }

    def get_mode(self) -> JAMMode:
        """Get current JAM mode."""
        return self.mode

    def set_mode(self, mode: JAMMode) -> bool:
        """Set JAM mode."""
        self.mode = mode
        return True

    async def configure_testnet(self, rpc_url: str, keypair_data: Optional[Dict[str, Any]] = None) -> bool:
        """Configure testnet parameters."""
        try:
            self.rpc_url = rpc_url
            self.substrate = SubstrateInterface(url=rpc_url)

            if keypair_data:
                if 'seed' in keypair_data:
                    self.set_keypair_from_seed(keypair_data['seed'])
                elif 'uri' in keypair_data:
                    self.set_keypair_from_uri(keypair_data['uri'])

            return True
        except Exception as e:
            print(f"Error configuring testnet: {e}")
            return False

    def set_keypair(self, keypair: Keypair):
        """Set the keypair for signing transactions."""
        self.keypair = keypair

    def set_keypair_from_seed(self, seed: str):
        """Set keypair from seed phrase."""
        self.keypair = Keypair.create_from_seed(seed)

    def set_keypair_from_uri(self, uri: str):
        """Set keypair from URI (seed or mnemonic)."""
        self.keypair = Keypair.create_from_uri(uri)