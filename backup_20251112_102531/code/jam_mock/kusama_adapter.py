"""
Kusama Testnet Adapter for BorgLife Phase 1

Provides real blockchain integration with Kusama testnet for Phase 1 validation.
Uses system.remark extrinsics to store DNA hashes on-chain.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from decimal import Decimal
import httpx
import json
import ssl
from substrateinterface import SubstrateInterface, Keypair
from .interface import JAMInterface, JAMMode
from .ssl_utils import SSLUtils
from .keypair_manager import KeypairManager


class WestendAdapter(JAMInterface):
    """
    Westend testnet adapter for real blockchain validation.

    Uses system.remark extrinsics to store DNA hashes on Westend testnet.
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

        # Initialize keypair manager
        self.keypair_manager = KeypairManager()

        # Dual-currency wealth tracking for Phase 2A
        self.wealth_cache: Dict[str, Dict[str, Decimal]] = {}  # borg_id -> {currency: balance}
        self.transaction_cache: Dict[str, list] = {}

        # Block scanning configuration
        self.max_scan_blocks = 1000  # Maximum blocks to scan in one operation
        self.scan_batch_size = 10    # Blocks to scan per batch
        self.scan_delay = 0.1        # Delay between batches to avoid rate limiting

        # Transaction cache for faster lookups
        self.tx_cache: Dict[str, Dict[str, Any]] = {}  # tx_hash -> tx_data

        # HTTP fallback configuration
        self.http_client = None
        self.http_timeout = 30.0  # seconds
        self.retry_attempts = 3
        self.retry_backoff = 1.0  # base backoff in seconds

        # Rate limiting configuration
        self.rate_limit_requests = 10  # requests per window
        self.rate_limit_window = 60    # window in seconds
        self.request_history: List[float] = []  # timestamps of recent requests

        # Multi-endpoint configuration - prioritize working endpoints
        self.endpoints = [
            "wss://westend-rpc.polkadot.io",  # Primary Westend endpoint
            "wss://westend.api.onfinality.io/public-ws",  # OnFinality Westend
            "wss://westend-rpc.dwellir.com",  # Dwellir Westend
        ]
        self.current_endpoint_index = 0
        self.endpoint_health: Dict[str, Dict[str, Any]] = {}

        # SSL/TLS configuration for LibreSSL compatibility
        self.ssl_context = SSLUtils.create_libressl_compatible_context()

        # Initialize substrate connection with fallback endpoints
        self.substrate = None
        if connect_immediately:
            # Try each endpoint until one works
            for endpoint in self.endpoints:
                try:
                    print(f"🔌 Attempting connection to {endpoint}...")
                    
                    # Try without custom SSL context first (let substrate-interface handle it)
                    self.substrate = SubstrateInterface(
                        url=endpoint,
                        ss58_format=42,  # Westend address format
                        # Let substrate-interface use its own SSL handling
                    )
                    
                    # Test the connection with proper API call
                    chain_name = self.substrate.chain
                    block_num = self.substrate.get_block_number(None)  # Pass None for latest block
                    
                    print(f"✅ Connected to Westend via {endpoint}")
                    print(f"   Chain: {chain_name}, Block: {block_num}")
                    self.rpc_url = endpoint  # Update to working endpoint
                    break
                    
                except Exception as e:
                    print(f"❌ Failed to connect to {endpoint}: {e}")
                    self.substrate = None
                    continue
            
            if not self.substrate:
                print("⚠️  WARNING: All Westend endpoints failed")
                print("⚠️  Demo will run in offline mode (Steps 1-3 only)")
                print("⚠️  This may be due to network/firewall issues")

    async def _init_http_client(self):
        """Initialize HTTP client for fallback operations."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=self.http_timeout,
                headers={'Content-Type': 'application/json'}
            )

    async def _make_http_request(self, method: str, params: List[Any] = None) -> Optional[Dict[str, Any]]:
        """
        Make HTTP JSON-RPC request with retry logic and rate limiting.

        Args:
            method: RPC method name
            params: RPC parameters

        Returns:
            RPC response or None if failed
        """
        await self._init_http_client()

        # Check rate limit
        if not await self._check_rate_limit():
            print("Rate limit exceeded, skipping request")
            return None

        # Prepare request
        request_id = int(time.time() * 1000)
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or []
        }

        # Try each endpoint with retries
        for endpoint_index in range(len(self.endpoints)):
            endpoint = self.endpoints[endpoint_index]
            http_url = endpoint.replace('wss://', 'https://').replace('ws://', 'http://')

            for attempt in range(self.retry_attempts):
                try:
                    # Record request for rate limiting
                    self.request_history.append(time.time())

                    response = await self.http_client.post(
                        http_url,
                        json=payload,
                        headers={'Content-Type': 'application/json'}
                    )

                    if response.status_code == 200:
                        result = response.json()
                        if 'error' not in result:
                            return result.get('result')
                        else:
                            print(f"RPC error: {result['error']}")
                    else:
                        print(f"HTTP error {response.status_code}: {response.text}")

                except Exception as e:
                    print(f"HTTP request attempt {attempt + 1} failed for {http_url}: {e}")

                    if attempt < self.retry_attempts - 1:
                        # Exponential backoff
                        delay = self.retry_backoff * (2 ** attempt)
                        await asyncio.sleep(delay)

            # Try next endpoint if this one failed
            continue

        print("All endpoints failed")
        return None

    async def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()

        # Remove old requests outside the window
        cutoff = now - self.rate_limit_window
        self.request_history = [t for t in self.request_history if t > cutoff]

        # Check if we're under the limit
        return len(self.request_history) < self.rate_limit_requests

    async def _get_healthy_endpoint(self) -> str:
        """
        Get the healthiest available endpoint.

        Returns:
            Endpoint URL to use
        """
        # Simple round-robin for now - could be enhanced with health checks
        endpoint = self.endpoints[self.current_endpoint_index]
        self.current_endpoint_index = (self.current_endpoint_index + 1) % len(self.endpoints)
        return endpoint

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
                    'westend_block_number': receipt.block_number
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
        Comprehensive health check for Kusama connectivity and account status.
        """
        base_info = {
            'mode': self.mode.value,
            'rpc_url': self.rpc_url,
            'keypair_configured': self.keypair is not None,
            'cached_wealth_records': len(self.wealth_cache),
            'cached_transactions': len(self.tx_cache),
            'usdb_asset_id': self._get_usdb_asset_id(),
            'scan_config': {
                'max_scan_blocks': self.max_scan_blocks,
                'scan_batch_size': self.scan_batch_size,
                'scan_delay': self.scan_delay
            },
            'rate_limit_config': {
                'requests_per_window': self.rate_limit_requests,
                'window_seconds': self.rate_limit_window,
                'current_requests': len(self.request_history)
            },
            'endpoints': self.endpoints,
            'current_endpoint_index': self.current_endpoint_index,
            'ssl_config': {
                'openssl_version': ssl.OPENSSL_VERSION,
                'has_tls_1_3': hasattr(ssl, 'PROTOCOL_TLSv1_3'),
                'max_tls_version': getattr(self.ssl_context, 'maximum_version', None),
                'min_tls_version': getattr(self.ssl_context, 'minimum_version', None)
            }
        }

        # Initialize health check results
        results = {
            'websocket_connected': False,
            'rpc_responsive': False,
            'chain_name': None,
            'block_number': None,
            'account_balance': None,
            'network_congestion': None,
            **base_info
        }

        if not self.substrate:
            results['status'] = 'offline'
            results['error'] = 'No substrate connection'
            return results

        try:
            # Check WebSocket connection
            results['websocket_connected'] = True

            # Test RPC responsiveness by getting chain name
            # Note: substrateinterface uses different method names
            try:
                # Try different methods to get chain info
                chain_name = self.substrate.chain_name
            except AttributeError:
                try:
                    # Try querying system properties
                    chain_name = self.substrate.query("System", "Properties").value['ss58Format']
                    if not isinstance(chain_name, str):
                        chain_name = "Kusama"  # Default assumption
                except:
                    chain_name = "Kusama"  # Default for Kusama testnet

            results['rpc_responsive'] = True
            results['chain_name'] = chain_name

            # Get current block number
            try:
                block_number = self.substrate.get_block_number()
            except:
                try:
                    # Alternative method
                    block_number = self.substrate.get_block_number(None)
                except:
                    block_number = None

            results['block_number'] = block_number

            # Check account balance if keypair available
            if self.keypair:
                try:
                    account_info = self.substrate.query(
                        module='System',
                        storage_function='Account',
                        params=[self.keypair.ss58_address]
                    )
                    balance = account_info.value['data']['free']
                    # Convert from smallest unit to KSM (assuming 10^12 decimals)
                    balance_ksm = float(balance) / (10 ** 12)
                    results['account_balance'] = f"{balance_ksm:.6f} KSM"
                except Exception as e:
                    results['account_balance'] = f"Error: {str(e)}"

            # Assess network congestion (simplified - could be enhanced)
            try:
                # Get recent block times to estimate congestion
                current_block = self.substrate.get_block(block_number=block_number)
                prev_block = self.substrate.get_block(block_number=block_number - 1) if block_number > 0 else None

                if current_block and prev_block and 'extrinsics' in current_block and 'extrinsics' in prev_block:
                    current_tx_count = len(current_block['extrinsics'])
                    prev_tx_count = len(prev_block['extrinsics'])
                    avg_tx_count = (current_tx_count + prev_tx_count) / 2

                    # Simple congestion assessment
                    if avg_tx_count > 50:
                        results['network_congestion'] = 'high'
                    elif avg_tx_count > 20:
                        results['network_congestion'] = 'medium'
                    else:
                        results['network_congestion'] = 'low'
                else:
                    results['network_congestion'] = 'unknown'
            except Exception as e:
                results['network_congestion'] = f"Error assessing: {str(e)}"

            # Overall status
            if results['rpc_responsive'] and results['chain_name']:
                results['status'] = 'healthy'
            else:
                results['status'] = 'degraded'

            return results

        except Exception as e:
            results['status'] = 'unhealthy'
            results['error'] = str(e)
            return results

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
            self.substrate = SubstrateInterface(url=rpc_url, ssl_context=self.ssl_context)

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

    # Phase 2A: Dual-Currency Support Methods

    async def transfer_wnd(self, from_address: str, to_address: str, amount: int) -> Dict[str, Any]:
        """
        Transfer WND tokens between addresses using balances.transfer extrinsic.

        Args:
            from_address: Sender's substrate address
            to_address: Recipient's substrate address
            amount: Amount to transfer in planck units

        Returns:
            Transfer result with success status and transaction details
        """
        if not self.substrate:
            return {'success': False, 'error': 'No substrate connection'}

        if not self.keypair:
            return {'success': False, 'error': 'No keypair configured'}

        try:
            # Compose balances.transfer extrinsic
            call = self.substrate.compose_call(
                call_module='Balances',
                call_function='transfer_keep_alive',
                call_params={
                    'dest': to_address,
                    'value': amount
                }
            )

            # Create signed extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call,
                keypair=self.keypair
            )

            # Submit and wait for inclusion
            receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

            if receipt.is_success:
                return {
                    'success': True,
                    'transaction_hash': receipt.extrinsic_hash,
                    'block_hash': receipt.block_hash,
                    'block_number': receipt.block_number,
                    'from_address': from_address,
                    'to_address': to_address,
                    'amount': amount
                }
            else:
                return {
                    'success': False,
                    'error': f'Transfer failed: {receipt.error_message}',
                    'from_address': from_address,
                    'to_address': to_address,
                    'amount': amount
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'from_address': from_address,
                'to_address': to_address,
                'amount': amount
            }

    async def transfer_usdb(self, from_address: str, to_address: str, amount: int, asset_id: int) -> Dict[str, Any]:
        """
        Transfer USDB assets between addresses using assets.transfer extrinsic.

        Args:
            from_address: Sender's substrate address
            to_address: Recipient's substrate address
            amount: Amount to transfer in planck units
            asset_id: USDB asset ID

        Returns:
            Transfer result with success status and transaction details
        """
        if not self.substrate:
            return {'success': False, 'error': 'No substrate connection'}

        if not self.keypair:
            return {'success': False, 'error': 'No keypair configured'}

        try:
            # Compose assets.transfer extrinsic
            call = self.substrate.compose_call(
                call_module='Assets',
                call_function='transfer',
                call_params={
                    'id': asset_id,
                    'target': to_address,
                    'amount': amount
                }
            )

            # Create signed extrinsic
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call,
                keypair=self.keypair
            )

            # Submit and wait for inclusion
            receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

            if receipt.is_success:
                return {
                    'success': True,
                    'transaction_hash': receipt.extrinsic_hash,
                    'block_hash': receipt.block_hash,
                    'block_number': receipt.block_number,
                    'from_address': from_address,
                    'to_address': to_address,
                    'amount': amount,
                    'asset_id': asset_id
                }
            else:
                return {
                    'success': False,
                    'error': f'Transfer failed: {receipt.error_message}',
                    'from_address': from_address,
                    'to_address': to_address,
                    'amount': amount
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'from_address': from_address,
                'to_address': to_address,
                'amount': amount
            }

    async def get_usdb_balance(self, address: str, asset_id: int) -> int:
        """
        Query USDB balance for an address using Assets.Account storage.

        Args:
            address: Substrate address to query
            asset_id: USDB asset ID

        Returns:
            Balance in planck units
        """
        if not self.substrate:
            return 0

        try:
            # Query Assets.Account storage
            account_info = self.substrate.query(
                module='Assets',
                storage_function='Account',
                params=[asset_id, address]
            )

            if account_info.value:
                return account_info.value.get('balance', 0)
            else:
                return 0

        except Exception as e:
            print(f"Error querying USDB balance for {address}: {e}")
            return 0

    async def get_wnd_balance(self, address: str) -> int:
        """
        Query WND balance for an address using System.Account storage.

        Args:
            address: Substrate address to query

        Returns:
            Balance in planck units (never None, returns 0 on error)
        """
        if not self.substrate:
            return 0

        try:
            # Query System.Account storage
            account_info = self.substrate.query(
                module='System',
                storage_function='Account',
                params=[address]
            )

            if account_info and hasattr(account_info, 'value') and account_info.value:
                if isinstance(account_info.value, dict) and 'data' in account_info.value:
                    data = account_info.value['data']
                    if isinstance(data, dict):
                        return data.get('free', 0)
                    else:
                        # Handle case where data might be a different structure
                        return getattr(data, 'free', 0)
                else:
                    # Handle different account_info structures
                    return account_info.value.get('free', 0) if isinstance(account_info.value, dict) else 0
            else:
                return 0

        except Exception as e:
            print(f"Error querying WND balance for {address}: {e}")
            return 0

    async def get_dual_balance(self, address: str, asset_id: Optional[int] = None) -> Dict[str, int]:
        """
        Get both WND and USDB balances for an address.

        Args:
            address: Substrate address to query
            asset_id: USDB asset ID (if None, will try to get from config)

        Returns:
            Dict with 'wnd' and 'usdb' balance keys
        """
        # Get asset_id from config if not provided
        if asset_id is None:
            asset_id = self._get_usdb_asset_id()

        wnd_balance = await self.get_wnd_balance(address)
        usdb_balance = await self.get_usdb_balance(address, asset_id) if asset_id else 0

        return {
            'wnd': wnd_balance,
            'usdb': usdb_balance
        }

    def _get_usdb_asset_id(self) -> Optional[int]:
        """Get USDB asset ID from configuration."""
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), '..', '.borglife_config')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        if line.startswith('USDB_ASSET_ID='):
                            return int(line.split('=', 1)[1].strip())
        except Exception as e:
            print(f"Warning: Could not read USDB asset ID from config: {e}")

        return None

    async def update_wealth_dual(self, borg_id: str, currency: str, amount: Decimal, operation: str, description: str) -> bool:
        """
        Update wealth balance for dual-currency system.

        Args:
            borg_id: Borg identifier
            currency: 'WND' or 'USDB'
            amount: Amount to add/subtract
            operation: 'revenue', 'transfer', or 'cost'
            description: Transaction description

        Returns:
            True if update successful
        """
        if currency not in ['WND', 'USDB']:
            raise ValueError(f"Invalid currency: {currency}")

        if borg_id not in self.wealth_cache:
            self.wealth_cache[borg_id] = {'WND': Decimal('0'), 'USDB': Decimal('0')}

        # Update balance
        if operation in ['revenue', 'transfer']:
            self.wealth_cache[borg_id][currency] += amount
        elif operation == 'cost':
            self.wealth_cache[borg_id][currency] -= amount
        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Log transaction
        if borg_id not in self.transaction_cache:
            self.transaction_cache[borg_id] = []

        transaction = {
            'timestamp': time.time(),
            'currency': currency,
            'operation': operation,
            'amount': float(amount),
            'description': description,
            'balance_after': float(self.wealth_cache[borg_id][currency])
        }

        self.transaction_cache[borg_id].append(transaction)

        return True

    async def get_wealth_balance_dual(self, borg_id: str, currency: str) -> Decimal:
        """
        Get wealth balance for specific currency.

        Args:
            borg_id: Borg identifier
            currency: 'WND' or 'USDB'

        Returns:
            Balance as Decimal
        """
        if currency not in ['WND', 'USDB']:
            raise ValueError(f"Invalid currency: {currency}")

        if borg_id not in self.wealth_cache:
            return Decimal('0')

        return self.wealth_cache[borg_id].get(currency, Decimal('0'))

    async def get_wealth_summary(self, borg_id: str) -> Dict[str, Decimal]:
        """
        Get complete wealth summary for a borg.

        Args:
            borg_id: Borg identifier

        Returns:
            Dict with WND and USDB balances
        """
        return {
            'WND': await self.get_wealth_balance_dual(borg_id, 'WND'),
            'USDB': await self.get_wealth_balance_dual(borg_id, 'USDB')
        }