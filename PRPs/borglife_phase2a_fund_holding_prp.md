# BorgLife Phase 2A: Borg Fund Holding & Transfer System PRP

## Feature: Borg Fund Holding and Inter-Borg Transfer Protocol

## Goal

Implement a comprehensive fund holding and transfer system for borgs, enabling persistent wealth storage, secure inter-borg transfers, and clear separation between blockchain operations (WND) and economic wealth (USDB stablecoin).

## Deliverable

A fully functional borg economic system where borgs can hold persistent wealth in USDB tokens, transfer funds securely between each other, and participate in autonomous economic activities while maintaining clear separation from blockchain operational costs.

## Prerequisites

### Database Schema Setup
**Required Supabase Tables:**
```sql
-- Borg addresses and keypair management
CREATE TABLE borg_addresses (
    borg_id VARCHAR(50) PRIMARY KEY,
    substrate_address VARCHAR(64) NOT NULL UNIQUE,
    dna_hash VARCHAR(64) NOT NULL,
    keypair_encrypted TEXT NOT NULL, -- AES-256 encrypted
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Dual-currency balance tracking
CREATE TABLE borg_balances (
    borg_id VARCHAR(50) REFERENCES borg_addresses(borg_id),
    currency VARCHAR(10) NOT NULL, -- 'WND' or 'USDB'
    balance_wei BIGINT NOT NULL DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (borg_id, currency)
);

-- Transfer transaction history
CREATE TABLE transfer_transactions (
    tx_id VARCHAR(32) PRIMARY KEY,
    from_borg_id VARCHAR(50) REFERENCES borg_addresses(borg_id),
    to_borg_id VARCHAR(50) REFERENCES borg_addresses(borg_id),
    currency VARCHAR(10) NOT NULL,
    amount_wei BIGINT NOT NULL,
    transaction_hash VARCHAR(66),
    block_number BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX idx_balances_borg_currency ON borg_balances(borg_id, currency);
CREATE INDEX idx_transfers_status ON transfer_transactions(status);
CREATE INDEX idx_transfers_created ON transfer_transactions(created_at DESC);
```

### Migration Scripts
- `scripts/setup_phase2a_database.py` - Automated schema creation
- `scripts/migrate_borg_balances.py` - Data migration from Phase 1

### Existing Infrastructure Integration
**Key Components to Extend:**
- `jam_mock/kusama_adapter.py` - WestendAdapter class (currently Phase 1 focused)
- `jam_mock/transaction_manager.py` - TransactionManager class (needs TRANSFER/ASSET_TRANSFER types)
- `jam_mock/secure_key_storage.py` - SecureKeyStorage for borg keypair management
- `jam_mock/ethical_compliance_monitor.py` - EthicalComplianceMonitor for transfer validation
- `jam_mock/demo_cost_controller.py` - DemoCostController for dual-currency budgeting
- `jam_mock/demo_audit_logger.py` - DemoAuditLogger for transfer compliance logging

## Context

### Current State
- Phase 1 completed with Westend integration for DNA storage
- Borgs have in-memory wealth tracking but no persistent fund holding
- All transactions use WND, creating confusion between operational costs and economic wealth
- No mechanism for borg-to-borg economic interactions
- Security hardening, compliance validation, and monitoring systems implemented

### Technical Context
- **Blockchain**: Westend Asset Hub (Polkadot testnet) - `wss://westend-asset-hub-rpc.polkadot.io`
- **Native Token**: WND for blockchain operations (gas, storage, network fees)
- **Stablecoin**: USDB (USDBorglifeStablecoin) for borg wealth and transfers
- **Libraries**: substrate-interface>=1.7.0 (updated from requirements.txt), existing BorgLife architecture
- **Security**: AES-256 encrypted key storage, transaction validation, audit logging
- **Database**: Supabase with dual-currency balance tracking
- **Existing Infrastructure**: EthicalComplianceMonitor, DemoCostController, TransactionManager

### Business Context
- **Economic Foundation**: Enables Δ(W) = R - C wealth dynamics from whitepaper
- **Autonomous Borgs**: Borgs can accumulate and transfer wealth independently
- **Testing Infrastructure**: USDB eliminates faucet dependencies for economic testing
- **Market Preparation**: Foundation for mating markets and organ trading
- **Compliance**: Integrates with existing ethical monitoring and cost controls

### Technical Architecture Context

#### Asset Hub Architecture
- **System Chain**: Asset Hub serves as Polkadot's system parachain for asset management
- **Pallet Structure**: Uses FRAME pallets including Assets, Balances, and System
- **Cross-Chain Communication**: XCM protocol for cross-chain asset transfers
- **Asset Creation**: Assets pallet provides `create`, `mint`, `transfer`, and `burn` functions
- **Storage**: Asset metadata and balances stored in pallet-specific storage maps

#### USDB Stablecoin Design
- **Asset Type**: Fungible token created via Assets pallet
- **Decimals**: 12 decimal places (Polkadot standard for precision)
- **Initial Supply**: 1,000,000 USDB minted to dispenser account
- **Transfer Mechanism**: `assets.transfer` extrinsic for peer-to-peer transfers
- **Balance Queries**: `Assets.Account` storage map for balance lookups

#### Network Configuration Requirements
- **RPC Endpoints**: Primary `wss://westend-asset-hub-rpc.polkadot.io`, fallbacks available
- **Chain Spec**: Westend Asset Hub chain specification with Assets pallet enabled
- **Genesis Config**: Asset Hub genesis includes pallet configurations
- **Block Production**: 6-second block time with Babe consensus
- **Finality**: GRANDPA finality gadget for deterministic finality

#### Smart Contract Interaction Protocols
- **Extrinsic Format**: Substrate extrinsics with call data and signatures
- **Pallet Calls**: Assets pallet calls: `create`, `mint`, `transfer`, `set_metadata`
- **Storage Queries**: Runtime API queries for balance and metadata lookups
- **Event Monitoring**: System events for transaction confirmation
- **Error Handling**: DispatchError types for transaction failure classification

#### Gas Fee Optimization Strategies
- **Fee Calculation**: Based on extrinsic weight and length
- **Priority Fees**: Optional tip for faster inclusion
- **Batch Transactions**: Multiple operations in single extrinsic
- **Weight Estimation**: Pre-calculation of computational weight
- **Fee Preferences**: Dynamic adjustment based on network congestion

#### Security Considerations
- **Key Management**: AES-256 encrypted keypairs in macOS Keychain
- **Transaction Signing**: Ed25519 signatures with replay protection
- **Balance Validation**: Pre-transfer balance checks with race condition protection
- **Audit Trail**: Comprehensive logging of all economic operations
- **Access Control**: Role-based permissions for asset operations

#### Testing Methodologies
- **Unit Tests**: Individual component testing with mock blockchain
- **Integration Tests**: Full system testing with testnet
- **Economic Scenario Tests**: Multi-borg interaction simulations
- **Load Testing**: Performance validation under high transaction volume
- **Security Testing**: Penetration testing and vulnerability assessment

#### Integration Patterns
- **Database Synchronization**: Real-time balance updates with conflict resolution
- **Event-Driven Architecture**: Reactive processing of blockchain events
- **Circuit Breaker Pattern**: Failure isolation and graceful degradation
- **Retry Mechanisms**: Exponential backoff for transient failures
- **Monitoring Integration**: Comprehensive observability and alerting

## Implementation Tasks

### Task 1: Create USDB Stablecoin on Westend Asset Hub
**Description**: Mint USDB stablecoin for borg economic activities, separate from WND operational costs.

**Technical Details**:
- **Asset Creation**: Use Assets pallet on Westend Asset Hub (`assets.create`)
- **Initial Supply**: 1,000,000 USDB (1,000,000 * 10^12 planck units)
- **Asset ID**: Auto-assigned by pallet, tracked in configuration
- **Metadata**: Set name, symbol, decimals via `assets.setMetadata`
- **Admin Account**: Funded Westend account for asset management
- **Dispenser Account**: Dedicated account for initial USDB distribution to borgs

**Implementation Steps**:
1. Create `scripts/create_usdb_asset.py` using substrate-interface 1.7.0+
2. Generate admin keypair using existing `AdvancedKeypairManager` from `jam_mock/keypair_manager.py`
3. Execute `assets.create` extrinsic with metadata parameters:
   ```python
   # Create asset with dispenser as admin
   call = substrate.compose_call(
       call_module='Assets',
       call_function='create',
       call_params={
           'id': asset_id,  # Let pallet assign
           'admin': dispenser_address,  # Dispenser account controls asset
           'min_balance': 1  # Minimum balance in planck units
       }
   )
   ```
4. Set metadata using `assets.set_metadata` extrinsic:
   ```python
   metadata_call = substrate.compose_call(
       call_module='Assets',
       call_function='set_metadata',
       call_params={
           'id': asset_id,
           'name': 'USDBorglifeStablecoin'.encode(),
           'symbol': 'USDB'.encode(),
           'decimals': 12
       }
   )
   ```
5. Mint initial supply using `assets.mint` to dispenser account:
   ```python
   mint_call = substrate.compose_call(
       call_module='Assets',
       call_function='mint',
       call_params={
           'id': asset_id,
           'beneficiary': dispenser_address,
           'amount': 1_000_000 * (10 ** 12)  # 1M USDB in planck units
       }
   )
   ```
6. Store asset ID in `code/.borglife_config` configuration file
7. Verify asset creation via `assets.metadata` and `assets.account` queries

**Network Configuration Requirements**:
- **RPC Endpoint**: `wss://westend-asset-hub-rpc.polkadot.io` (primary)
- **Fallback Endpoints**: `wss://westend.api.onfinality.io/public-ws`, `wss://westend-rpc.dwellir.com`
- **Chain ID**: Westend Asset Hub (parachain ID: 1000)
- **Genesis Hash**: Verified against known Westend Asset Hub genesis
- **Assets Pallet Version**: Compatible with substrate-interface 1.7.0+

**Smart Contract Interaction Protocols**:
- **Extrinsic Construction**: Use `substrate.compose_call()` for pallet calls
- **Transaction Signing**: Ed25519 signatures with keypair from secure storage
- **Batch Transactions**: Combine create, metadata, and mint operations
- **Event Monitoring**: Listen for `Assets.Created`, `Assets.MetadataSet`, `Assets.Minted` events
- **Error Handling**: Handle `DispatchError` types (InsufficientBalance, BadOrigin, etc.)

**Gas Fee Optimization Strategies**:
- **Weight Estimation**: Pre-calculate extrinsic weight using `payment_queryInfo`
- **Fee Calculation**: Base fee + weight fee + length fee
- **Priority Adjustment**: Add tip for faster inclusion during congestion
- **Batch Operations**: Combine multiple calls in single extrinsic to reduce total fees
- **Optimal Timing**: Execute during low-congestion periods

**Security Considerations**:
- **Keypair Security**: Admin keypair encrypted with AES-256 in macOS Keychain
- **Transaction Signing**: Secure signing with hardware-backed entropy when available
- **Access Control**: Dispenser account has exclusive minting rights
- **Audit Trail**: All asset creation operations logged with transaction hashes
- **Backup Recovery**: Admin seed phrase securely backed up offline

**Integration Points**:
- Uses existing `jam_mock/kusama_adapter.py` connection logic (WestendAdapter class)
- Leverages `jam_mock/secure_key_storage.py` for admin keypair management
- Updates configuration system for asset ID tracking
- Integrates with existing transaction monitoring infrastructure

**Validation**:
- Asset created successfully on Westend Asset Hub
- Initial supply minted and visible on chain via Subscan
- Asset metadata correctly set (name: "USDBorglifeStablecoin", symbol: "USDB", decimals: 12)
- Asset ID stored in configuration and retrievable
- Dispenser account shows correct balance in asset
- Asset appears in Polkadot.js explorer with correct properties

**Troubleshooting**:
- **Asset Creation Fails**: Check admin account WND balance (minimum 0.1 WND required)
- **Metadata Not Set**: Verify admin account has permission to set metadata
- **Minting Fails**: Ensure dispenser account exists and has proper permissions
- **RPC Connection Issues**: Try fallback endpoints, check network connectivity
- **Transaction Timeout**: Increase timeout settings, check network congestion

**Best Practices**:
- Test asset creation on small amounts first
- Verify all operations on testnet explorer before production
- Implement comprehensive error handling and rollback procedures
- Document all asset parameters for future reference
- Set up monitoring for asset-related events

**Dependencies**: None
**Estimated Effort**: 4 hours

### Task 2: Implement Borg-Specific Address Management
**Description**: Create deterministic address generation and management for borg fund holding.

**Technical Details**:
- **Address Generation**: Deterministic keypairs from borg DNA hash using PBKDF2
- **Storage**: Secure encrypted storage of borg keypairs using AES-256
- **Registration**: Track borg addresses in Supabase database with referential integrity
- **Synchronization**: Real-time balance tracking across WND and USDB currencies
- **Key Derivation**: Hierarchical deterministic (HD) key derivation for borg accounts

**Implementation Steps**:
1. Create `BorgAddressManager` class extending existing keypair management:
   ```python
   class BorgAddressManager:
       def __init__(self, supabase_client, secure_storage: SecureKeypairManager):
           self.supabase = supabase_client
           self.secure_storage = secure_storage
           self.key_derivation_path = "m/44'/354'/0'/0"  # BorgLife HD path
   ```

2. Implement deterministic keypair creation with enhanced security:
   ```python
   def create_borg_keypair(self, borg_id: str, dna_hash: str) -> Dict[str, Any]:
       # Use PBKDF2 with borg DNA hash as salt
       seed = hashlib.pbkdf2_hmac(
           'sha512',
           dna_hash.encode(),
           f"borglife-{borg_id}".encode(),
           2048  # iterations
       )[:32]  # Take first 32 bytes

       # Create keypair from derived seed
       keypair = Keypair.create_from_seed(seed.hex())

       # Store securely
       self.secure_storage.store_keypair(f"borg-{borg_id}", keypair, {
           'borg_id': borg_id,
           'dna_hash': dna_hash,
           'derivation_method': 'pbkdf2',
           'created_at': datetime.utcnow().isoformat()
       })

       return {
           'borg_id': borg_id,
           'address': keypair.ss58_address,
           'public_key': keypair.public_key.hex()
       }
   ```

3. Add Supabase tables for borg addresses and balances with constraints:
   ```sql
   -- Enhanced borg addresses table
   CREATE TABLE borg_addresses (
       borg_id VARCHAR(50) PRIMARY KEY,
       substrate_address VARCHAR(64) NOT NULL UNIQUE,
       dna_hash VARCHAR(64) NOT NULL,
       keypair_encrypted TEXT NOT NULL,
       derivation_path VARCHAR(100),
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       last_sync TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       status VARCHAR(20) DEFAULT 'active'
   );

   -- Enhanced dual-currency balance tracking
   CREATE TABLE borg_balances (
       borg_id VARCHAR(50) REFERENCES borg_addresses(borg_id) ON DELETE CASCADE,
       currency VARCHAR(10) NOT NULL CHECK (currency IN ('WND', 'USDB')),
       balance_wei BIGINT NOT NULL DEFAULT 0 CHECK (balance_wei >= 0),
       last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       last_block_synced BIGINT,
       PRIMARY KEY (borg_id, currency)
   );
   ```

4. Implement balance synchronization with conflict resolution:
   ```python
   async def sync_borg_balance(self, borg_id: str, currency: str, asset_id: Optional[int] = None) -> bool:
       """Synchronize borg balance with on-chain state."""
       try:
           # Get borg address
           address_result = self.supabase.table('borg_addresses').select('substrate_address').eq('borg_id', borg_id).execute()
           if not address_result.data:
               raise ValueError(f"Borg {borg_id} not found")

           address = address_result.data[0]['substrate_address']

           # Query on-chain balance
           if currency == 'WND':
               balance = await self.westend_adapter.get_wnd_balance(address)
           else:  # USDB
               balance = await self.westend_adapter.get_usdb_balance(address, asset_id)

           # Update database with optimistic locking
           self.supabase.table('borg_balances').upsert({
               'borg_id': borg_id,
               'currency': currency,
               'balance_wei': balance,
               'last_updated': datetime.utcnow().isoformat(),
               'last_block_synced': await self.westend_adapter.get_current_block()
           }).execute()

           return True
       except Exception as e:
           print(f"Balance sync failed for {borg_id}: {e}")
           return False
   ```

5. Create address registration and validation methods:
   ```python
   async def register_borg_address(self, borg_id: str, dna_hash: str) -> Dict[str, Any]:
       """Register new borg address with validation."""
       # Validate DNA hash format
       if not re.match(r'^[0-9a-fA-F]{64}$', dna_hash):
           raise ValueError("Invalid DNA hash format")

       # Check for existing registration
       existing = self.supabase.table('borg_addresses').select('borg_id').eq('borg_id', borg_id).execute()
       if existing.data:
           raise ValueError(f"Borg {borg_id} already registered")

       # Create keypair and register
       keypair_data = self.create_borg_keypair(borg_id, dna_hash)

       # Register in database
       self.supabase.table('borg_addresses').insert({
           'borg_id': borg_id,
           'substrate_address': keypair_data['address'],
           'dna_hash': dna_hash,
           'keypair_encrypted': 'stored_in_keychain',  # Reference only
           'derivation_path': self.key_derivation_path
       }).execute()

       # Initialize balances
       for currency in ['WND', 'USDB']:
           self.supabase.table('borg_balances').insert({
               'borg_id': borg_id,
               'currency': currency,
               'balance_wei': 0
           }).execute()

       return keypair_data
   ```

**Security Considerations**:
- **Key Derivation**: PBKDF2 with high iteration count prevents brute force attacks
- **Encryption**: AES-256-GCM encryption for keypair storage
- **Access Control**: Role-based access to borg keypairs
- **Audit Trail**: All address operations logged with timestamps
- **Backup Recovery**: Secure backup procedures for keypairs

**Integration Patterns**:
- **Database Transactions**: Atomic operations for address registration
- **Event-Driven Sync**: Reactive balance updates on blockchain events
- **Circuit Breaker**: Failure isolation for external service dependencies
- **Caching Layer**: Redis caching for frequently accessed balances

**Testing Methodologies**:
- **Deterministic Testing**: Verify address generation consistency
- **Security Testing**: Key derivation strength validation
- **Integration Testing**: End-to-end address registration flow
- **Load Testing**: Concurrent address registration handling

**Validation**:
- Deterministic address generation works consistently across environments
- Keypairs stored securely with AES-256 encryption in macOS Keychain
- Database schema supports address and balance tracking with constraints
- Address generation is reproducible from DNA hash with proper validation
- Balance synchronization works correctly with on-chain state
- Address registration prevents duplicates and validates inputs

**Troubleshooting**:
- **Key Derivation Fails**: Check DNA hash format and encoding
- **Database Constraints**: Verify foreign key relationships and data types
- **Encryption Errors**: Check macOS Keychain accessibility
- **Balance Sync Issues**: Verify RPC connectivity and address formats
- **Duplicate Registration**: Implement proper conflict resolution

**Best Practices**:
- Use cryptographically secure random generation for salts
- Implement proper key rotation procedures
- Regular security audits of key management
- Comprehensive logging of all address operations
- Backup strategies for critical keypairs

**Dependencies**: Task 1 (USDB asset creation)
**Estimated Effort**: 4 hours

### Task 3: Extend WestendAdapter for Dual-Currency Support
**Description**: Add USDB asset operations to WestendAdapter alongside existing WND operations.

**Technical Details**:
- **Asset Transfers**: Implement USDB transfers using Assets pallet (`assets.transfer`)
- **Balance Queries**: Query both WND (`System.Account`) and USDB (`Assets.Account`) balances
- **Dual Tracking**: Maintain separate caches for WND and USDB in existing wealth_cache
- **Transaction Types**: Support both native (`Balances.transfer`) and asset transfers
- **Batch Operations**: Support multiple asset operations in single transaction
- **Event Monitoring**: Track asset transfer events and confirmations

**Implementation Steps**:
1. Add asset transfer methods to `jam_mock/kusama_adapter.py` WestendAdapter class:
   ```python
   async def transfer_usdb(self, from_address: str, to_address: str, amount: int, asset_id: int) -> Dict[str, Any]:
       """Transfer USDB assets between addresses with comprehensive error handling."""
       if not self.substrate:
           return {'success': False, 'error': 'No substrate connection'}

       if not self.keypair:
           return {'success': False, 'error': 'No keypair configured for signing'}

       try:
           # Validate addresses
           if not (from_address.startswith('5') and to_address.startswith('5')):
               return {'success': False, 'error': 'Invalid Substrate addresses'}

           # Check sender balance before transfer
           sender_balance = await self.get_usdb_balance(from_address, asset_id)
           if sender_balance < amount:
               return {'success': False, 'error': f'Insufficient balance: {sender_balance} < {amount}'}

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
                   'asset_id': asset_id,
                   'fee': getattr(receipt, 'total_fee_amount', 0)
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
               'error': f'Transfer error: {str(e)}',
               'from_address': from_address,
               'to_address': to_address,
               'amount': amount
           }
   ```

2. Implement balance queries for both currencies with caching:
   ```python
   async def get_usdb_balance(self, address: str, asset_id: int) -> int:
       """Query USDB balance using Assets.Account storage with caching."""
       if not self.substrate:
           return 0

       # Check cache first
       cache_key = f"usdb_{address}_{asset_id}"
       if cache_key in self.wealth_cache:
           cached_data = self.wealth_cache[cache_key]
           # Cache for 30 seconds
           if time.time() - cached_data['timestamp'] < 30:
               return cached_data['balance']

       try:
           # Query Assets.Account storage
           account_info = self.substrate.query(
               module='Assets',
               storage_function='Account',
               params=[asset_id, address]
           )

           balance = 0
           if account_info.value:
               balance = account_info.value.get('balance', 0)

           # Update cache
           self.wealth_cache[cache_key] = {
               'balance': balance,
               'timestamp': time.time()
           }

           return balance

       except Exception as e:
           print(f"Error querying USDB balance for {address}: {e}")
           return 0
   ```

3. Extend wealth cache to support multiple assets:
   ```python
   # Enhanced wealth cache structure
   self.wealth_cache: Dict[str, Dict[str, Any]] = {}  # key -> {'balance': int, 'timestamp': float, 'currency': str}
   self.transaction_cache: Dict[str, list] = {}
   ```

4. Add asset-specific transaction composition and batch operations:
   ```python
   async def batch_asset_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
       """Execute multiple asset operations in single transaction."""
       if not self.substrate or not self.keypair:
           return {'success': False, 'error': 'Adapter not properly configured'}

       calls = []
       for op in operations:
           if op['type'] == 'transfer':
               call = self.substrate.compose_call(
                   call_module='Assets',
                   call_function='transfer',
                   call_params={
                       'id': op['asset_id'],
                       'target': op['to_address'],
                       'amount': op['amount']
                   }
               )
               calls.append(call)

       if not calls:
           return {'success': False, 'error': 'No valid operations'}

       # Create batch extrinsic
       batch_call = self.substrate.compose_call(
           call_module='Utility',
           call_function='batch',
           call_params={'calls': calls}
       )

       extrinsic = self.substrate.create_signed_extrinsic(
           call=batch_call,
           keypair=self.keypair
       )

       receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

       return {
           'success': receipt.is_success,
           'transaction_hash': receipt.extrinsic_hash if receipt.is_success else None,
           'error': receipt.error_message if not receipt.is_success else None,
           'operations_count': len(operations)
       }
   ```

5. Update `health_check()` method to include asset balances and network metrics:
   ```python
   async def health_check(self) -> Dict[str, Any]:
       """Enhanced health check with dual-currency support."""
       base_info = {
           'mode': self.mode.value,
           'rpc_url': self.rpc_url,
           'keypair_configured': self.keypair is not None,
           'usdb_asset_id': self._get_usdb_asset_id(),
           # ... existing fields ...
       }

       if not self.substrate:
           return {**base_info, 'status': 'offline', 'error': 'No substrate connection'}

       try:
           # ... existing checks ...

           # Check USDB balance if asset_id available
           usdb_balance = None
           if self.keypair and base_info['usdb_asset_id']:
               usdb_balance = await self.get_usdb_balance(
                   self.keypair.ss58_address,
                   base_info['usdb_asset_id']
               )

           results['usdb_balance'] = usdb_balance

           # Network congestion based on recent blocks
           congestion = await self._assess_network_congestion()
           results['network_congestion'] = congestion

           return results

       except Exception as e:
           return {**base_info, 'status': 'unhealthy', 'error': str(e)}
   ```

**Gas Fee Optimization Strategies**:
- **Dynamic Fee Adjustment**: Monitor network congestion and adjust tips
- **Batch Operations**: Combine multiple transfers to reduce per-operation fees
- **Optimal Timing**: Execute during low-congestion periods (off-peak hours)
- **Fee Estimation**: Pre-calculate fees using `payment_queryInfo` runtime API
- **Length Optimization**: Minimize extrinsic size for lower length fees

**Security Considerations**:
- **Replay Protection**: Include nonce in all transactions
- **Balance Validation**: Pre-transfer balance checks prevent overdrafts
- **Address Validation**: Verify Substrate address formats
- **Error Handling**: Comprehensive error classification and user feedback
- **Audit Logging**: All operations logged with full context

**Integration Patterns**:
- **Event-Driven Updates**: Reactive balance updates on transfer events
- **Optimistic UI**: Immediate UI updates with server-side confirmation
- **Conflict Resolution**: Handle concurrent transfer scenarios
- **Rate Limiting**: Prevent abuse with request throttling
- **Monitoring**: Comprehensive metrics collection for operations

**Testing Methodologies**:
- **Unit Tests**: Individual method testing with mock substrate
- **Integration Tests**: Full transfer flows with testnet
- **Load Tests**: High-frequency transfer validation
- **Security Tests**: Attempt invalid operations and verify protections
- **Network Tests**: Various network conditions and failure scenarios

**Validation**:
- USDB transfers work correctly using `assets.transfer` extrinsic
- Balance queries return accurate data for both currencies via storage queries
- Transaction composition handles asset parameters correctly
- Batch operations execute multiple transfers efficiently
- Health checks include asset information alongside existing WND data
- Error scenarios handled gracefully with detailed error messages
- Event monitoring captures all transfer confirmations

**Troubleshooting**:
- **Transfer Fails**: Check balance, address format, and network connectivity
- **Balance Query Errors**: Verify asset ID and address validity
- **RPC Timeouts**: Try fallback endpoints and increase timeouts
- **Extrinsic Rejections**: Check for sufficient WND balance for fees
- **Cache Inconsistencies**: Implement cache invalidation strategies

**Best Practices**:
- Implement comprehensive error handling and recovery
- Use batch operations for multiple transfers when possible
- Monitor network conditions and adjust operations accordingly
- Implement proper logging and monitoring for all operations
- Regular testing of failure scenarios and edge cases

**Dependencies**: Tasks 1-2
**Estimated Effort**: 5 hours

### Task 4: Implement Inter-Borg Transfer Protocol
**Description**: Create secure fund transfer capabilities between borg addresses.

**Technical Details**:
- **Transfer Validation**: Balance checks, amount validation, address verification using Supabase queries
- **Security**: Encrypted transaction signing using existing keypair infrastructure, replay protection via nonce
- **Confirmation**: Block confirmation monitoring for transfers using existing transaction monitoring
- **Error Handling**: Comprehensive error handling for failed transfers with user-friendly messages

**Implementation Steps**:
1. Create `transfer_usdb()` method in `jam_mock/kusama_adapter.py` WestendAdapter class:
   ```python
   async def transfer_usdb(self, from_borg_id: str, to_borg_id: str, amount: int, asset_id: int) -> Dict[str, Any]:
       """Transfer USDB between borg addresses with full validation."""
       # Get addresses from Supabase borg_addresses table
       # Validate balances using EconomicValidator
       # Compose and submit assets.transfer extrinsic
   ```
2. Add balance validation before transfers using Supabase balance queries
3. Implement transfer transaction composition and signing using existing patterns
4. Add transfer confirmation monitoring using existing transaction manager infrastructure
5. Create transfer error handling and recovery with rollback capabilities

**Integration Points**:
- Uses Supabase `borg_balances` and `borg_addresses` tables for validation
- Integrates with `EconomicValidator` for transfer compliance checks
- Leverages existing transaction submission and monitoring in `transaction_manager.py`
- Uses existing error handling patterns from `user_friendly_error_handler.py`

**Validation**:
- Transfers execute successfully between borg addresses using `assets.transfer`
- Balance validation prevents overdrafts via real-time Supabase queries
- Transfer confirmations are monitored correctly using existing infrastructure
- Error scenarios handled gracefully with clear user feedback

**Dependencies**: Tasks 1-3
**Estimated Effort**: 3 hours

### Task 5: Extend TransactionManager for Transfer Operations
**Description**: Add transfer transaction support to the existing transaction management system.

**Technical Details**:
- **Transfer Types**: Add TRANSFER and ASSET_TRANSFER types to TransactionType enum (extends existing DNA_STORAGE, WEALTH_UPDATE, BATCH_OPERATION)
- **Dual Currency**: Support both WND and USDB transaction tracking with currency field
- **Transfer Records**: Enhanced TransactionRecord with from_borg_id, to_borg_id, currency, amount fields
- **Audit Trail**: Integration with existing DemoAuditLogger for transfer compliance

**Implementation Steps**:
1. Extend TransactionType enum in `jam_mock/transaction_manager.py`:
   ```python
   class TransactionType(Enum):
       DNA_STORAGE = "dna_storage"
       WEALTH_UPDATE = "wealth_update"
       BATCH_OPERATION = "batch_operation"
       TRANSFER = "transfer"           # WND transfers
       ASSET_TRANSFER = "asset_transfer"  # USDB transfers
   ```
2. Add transfer fields to TransactionRecord dataclass:
   ```python
   @dataclass
   class TransactionRecord:
       # ... existing fields ...
       from_borg_id: Optional[str] = None
       to_borg_id: Optional[str] = None
       currency: Optional[str] = None  # 'WND' or 'USDB'
       transfer_amount: Optional[Decimal] = None
   ```
3. Update `validate_transaction_comprehensive()` for transfer validation
4. Add transfer-specific monitoring in `_monitor_transactions()`
5. Integrate with DemoAuditLogger for transfer compliance logging

**Integration Points**:
- Builds on existing transaction tracking infrastructure in `jam_mock/transaction_manager.py`
- Uses existing validation patterns for consistency
- Leverages audit logging for compliance requirements

**Validation**:
- Transfer transactions tracked correctly with currency separation
- TransactionRecord includes from_borg_id, to_borg_id, amount, currency
- Validation works for both WND and USDB transfer operations
- Audit logs capture transfer activities with compliance context
- Transaction statistics include transfer metrics

**Dependencies**: Tasks 1-4
**Estimated Effort**: 2 hours

### Task 6: Implement Economic Validation and Controls
**Description**: Add comprehensive economic validation for transfers and wealth management with dual-currency support.

**Technical Details**:
- **Balance Checks**: Prevent overdraft transfers using database balance queries
- **Economic Compliance**: Integration with EthicalComplianceMonitor for transfer validation (fair distribution, no harmful transfers)
- **Cost Controls**: Extend DemoCostController for dual-currency budgeting (WND operations, USDB wealth)
- **Transfer Limits**: Daily/monthly limits per borg to prevent abuse

**Implementation Steps**:
1. Create `EconomicValidator` class in `jam_mock/economic_validator.py` integrating existing components:
   ```python
   class EconomicValidator:
       def __init__(self, cost_controller: DemoCostController,
                    compliance_monitor: EthicalComplianceMonitor,
                    supabase_client):
           self.cost_controller = cost_controller
           self.compliance_monitor = compliance_monitor
           self.supabase = supabase_client
   ```
2. Implement balance validation methods for both currencies using Supabase queries
3. Add transfer-specific ethical compliance checks:
   - Prevent transfers that could cause borg "starvation" (below minimum balance)
   - Validate transfer amounts against borg wealth thresholds
   - Check for unusual transfer patterns
4. Extend DemoCostController with USDB budget tracking
5. Implement transfer rate limiting and daily limits

**Integration Points**:
- Uses existing `jam_mock/ethical_compliance_monitor.py` for transfer ethics validation
- Extends `jam_mock/demo_cost_controller.py` with dual-currency support
- Integrates with Supabase balance queries for real-time validation
- Leverages existing `jam_mock/demo_audit_logger.py` for compliance tracking

**Validation**:
- Overdraft transfers prevented for both WND and USDB
- Economic compliance checks work (no harmful transfers, fair distribution)
- Transfer limits enforced correctly (daily/monthly caps)
- Error messages are clear and helpful with actionable guidance
- Balance validation uses real-time database queries

**Dependencies**: Tasks 1-5
**Estimated Effort**: 2 hours

### Task 7: Create USDB Distribution and Testing Infrastructure
**Description**: Set up USDB distribution mechanisms for testing and initial borg funding.

**Technical Details**:
- **Distribution Script**: Automated USDB distribution to test borgs
- **Faucet Alternative**: USDB distribution replaces WND faucet dependency
- **Testing Setup**: Pre-funded borgs for economic testing
- **Balance Monitoring**: Track USDB distribution and usage

**Implementation Steps**:
1. Create `scripts/usdb_distribution.py` for automated USDB distribution
2. Set up test borg funding mechanisms in `jam_mock/usdb_faucet.py`
3. Implement distribution tracking in Supabase
4. Create testing utilities for economic scenarios in `tests/test_economic_scenarios.py`
5. Add balance monitoring for USDB in health checks

**Validation**:
- USDB distribution works reliably
- Test borgs receive correct funding
- Distribution is tracked accurately
- Economic testing scenarios work

**Dependencies**: Tasks 1-6
**Estimated Effort**: 2 hours

### Task 8: Update UI for Fund Management
**Description**: Add fund management capabilities to the sponsor interface.

**Technical Details**:
- **Balance Display**: Show both WND and USDB balances
- **Transfer Interface**: UI for initiating borg-to-borg transfers
- **Transaction History**: Display transfer and economic transaction history
- **Fund Management**: Deposit/withdraw capabilities for sponsors

**Implementation Steps**:
1. Update `sponsor_ui.py` to show dual balances from Supabase queries
2. Add transfer initiation interface with borg selection and amount input
3. Implement transaction history display using transfer_transactions table
4. Create fund management controls for sponsor deposits/withdrawals
5. Add real-time balance updates via polling or websockets

**Integration Points**:
- Uses existing Streamlit-based sponsor UI in `sponsor_ui.py`
- Integrates with Supabase for balance and transaction queries
- Leverages existing borg selection and management interfaces

**Validation**:
- UI displays correct balances for both currencies
- Transfer interface works correctly
- Transaction history is accurate and up-to-date
- Fund management operations work

**Dependencies**: Tasks 1-7
**Estimated Effort**: 3 hours

### Task 9: Comprehensive Testing and Validation
**Description**: Test the complete fund holding and transfer system end-to-end.

**Technical Details**:
- **Integration Tests**: Full system testing with real blockchain operations
- **Economic Scenarios**: Test various economic interactions between borgs
- **Error Scenarios**: Test failure modes and recovery
- **Performance Testing**: Validate system performance under load

**Implementation Steps**:
1. Create comprehensive integration tests in `tests/test_phase2a_integration.py`
2. Test economic scenarios (transfers, balance checks) in `tests/test_economic_scenarios.py`
3. Validate error handling and recovery in `tests/test_transfer_failures.py`
4. Perform performance testing with `tests/test_performance.py`
5. Document test results and edge cases

**Integration Points**:
- Extends existing test infrastructure in `tests/` directory
- Uses existing test utilities and fixtures from `conftest.py`
- Follows existing testing patterns for blockchain operations

**Validation**:
- All integration tests pass
- Economic scenarios work correctly
- Error scenarios handled properly
- Performance meets requirements
- System is ready for production use

**Dependencies**: Tasks 1-8
**Estimated Effort**: 3 hours

## Validation Gates

### Gate 1: Asset Creation & Distribution
- [ ] USDB stablecoin created on Westend Asset Hub using Assets pallet
- [ ] Initial supply (1,000,000 USDB) minted to admin account
- [ ] Asset metadata correctly configured (name: "USDBorglifeStablecoin", symbol: "USDB", decimals: 12)
- [ ] Asset ID stored in configuration and retrievable
- [ ] Admin account balance verified on-chain via Subscan

### Gate 2: Address & Balance Management
- [ ] BorgAddressManager creates deterministic addresses from DNA hash
- [ ] Keypairs stored encrypted using existing SecureKeyStorage
- [ ] Supabase tables (borg_addresses, borg_balances) created and populated
- [ ] Balance synchronization works for both WND and USDB
- [ ] Address generation reproducible from DNA hash

### Gate 3: Transfer Functionality
- [ ] WestendAdapter.transfer_usdb() method works correctly
- [ ] Transfer validation prevents invalid operations (balance checks, address verification)
- [ ] Transaction confirmation monitoring functional with proper timeouts
- [ ] Error handling comprehensive with user-friendly messages
- [ ] Transfer transactions appear on-chain and are verifiable

### Gate 4: Economic Controls
- [ ] EconomicValidator prevents overdraft transfers for both currencies
- [ ] Transfer limits enforced (daily/monthly caps per borg)
- [ ] EthicalComplianceMonitor integrated for transfer validation (no harmful transfers)
- [ ] DemoCostController extended for dual-currency budgeting
- [ ] Cost separation between WND (operations) and USDB (wealth) clear

### Gate 5: UI & User Experience
- [ ] Sponsor UI displays both WND and USDB balances in real-time
- [ ] Transfer interface functional with borg selection and amount input
- [ ] Transaction history shows both currencies with proper formatting
- [ ] Real-time balance updates work after transfers
- [ ] Error messages user-friendly and actionable

### Gate 6: Testing & Reliability
- [ ] Integration tests pass for all dual-currency scenarios
- [ ] Economic testing scenarios validate (transfers, balance checks, limits)
- [ ] Error recovery mechanisms work (failed transfers, network issues)
- [ ] Performance meets requirements (<5s transfer completion)
- [ ] Audit logs capture all transfer activities with compliance context

## Success Definition

**Minimal Success**: Borgs can hold USDB balances and perform basic transfers between each other, with clear separation from WND operational costs.

**Full Success**: Complete dual-currency economic system with secure transfers, comprehensive validation, intuitive UI, and robust testing infrastructure enabling autonomous borg economic activities.

## Risk Assessment

### High Risk
- **Asset Creation Complexity**: Westend Asset Hub asset operations may have edge cases not covered in substrate-interface documentation
  - **Mitigation**: Thorough testing with small amounts first, comprehensive error handling, manual verification via Subscan, use existing kusama_adapter.py patterns

- **Dual-Currency State Management**: Managing two currencies with separate balance tracking increases complexity
  - **Mitigation**: Clear separation of concerns, comprehensive testing, database transaction atomicity, leverage existing wealth_cache patterns

### Medium Risk
- **Keypair Security**: Borg keypair management must be absolutely secure for fund holding
  - **Mitigation**: Use existing battle-tested `jam_mock/secure_key_storage.py`, audit all key operations, implement key rotation

- **Economic Edge Cases**: Complex transfer scenarios (concurrent transfers, network failures) may reveal race conditions
  - **Mitigation**: Comprehensive testing of edge cases, database-level constraints, gradual rollout with monitoring, use existing transaction_manager.py patterns

- **Substrate Interface Version Compatibility**: substrate-interface 1.7.0 may have limitations with Assets pallet
  - **Mitigation**: Test thoroughly with current version, maintain compatibility layer, research Assets pallet support in substrate-interface

### Low Risk
- **UI Integration**: Adding balance displays and transfer interfaces to existing sponsor_ui.py
  - **Mitigation**: Build on existing Streamlit UI patterns, user testing, progressive enhancement

- **Database Schema Changes**: Adding new tables for dual-currency support
  - **Mitigation**: Proper migration scripts, backup before changes, rollback procedures, follow existing Supabase patterns

## Timeline

**Total Effort**: 24 hours
**Due Date**: End of Week 3
**Dependencies**: Phase 1 completion

## Resources Required

- **Blockchain Access**: Westend Asset Hub RPC endpoint (`wss://westend-asset-hub-rpc.polkadot.io`)
- **Test Accounts**: Funded Westend accounts for asset creation and testing (WND required)
- **Database**: Supabase schema updates for dual-currency support (borg_addresses, borg_balances, transfer_transactions tables)
- **Security**: Existing `jam_mock/secure_key_storage.py` infrastructure with AES-256 encryption
- **Libraries**: substrate-interface>=1.7.0 (already in requirements.txt) with Assets pallet support
- **Testing**: Comprehensive test scenarios for economic operations and dual-currency edge cases
- **Existing Infrastructure**: All Phase 1 components (EthicalComplianceMonitor, DemoCostController, TransactionManager, etc.)
- **Documentation**: Substrate Assets pallet documentation for correct extrinsic usage

## Rollback Procedures

### Asset Creation Rollback
1. If asset creation fails: No action needed (asset doesn't exist)
2. If asset created but metadata wrong: Update metadata via `assets.setMetadata`
3. If asset needs deletion: Assets pallet doesn't support deletion - document and avoid reuse

### Database Rollback
1. **Schema Changes**: Use Supabase migration rollback if available
2. **Data Migration**: Restore from backup taken before Phase 2A deployment
3. **Failed Transactions**: Manual cleanup of incomplete transfer records

### Transfer Rollback
1. **Failed Transfers**: Automatic refund via `transfer_usdb()` in reverse
2. **Stuck Transactions**: Manual intervention with transaction manager cancellation
3. **Balance Inconsistencies**: Reconcile with on-chain state via `sync_balances()`

### Complete System Rollback
```bash
# 1. Stop all services
docker compose down

# 2. Restore database backup
# (Supabase backup restoration)

# 3. Revert code changes
git checkout PHASE_1_COMPLETION

# 4. Clear any cached state
rm -rf code/jam_mock/.budget.json
rm -rf code/jam_mock/budget_transactions.jsonl

# 5. Restart with Phase 1 configuration
docker compose up -d
```

## Post-Implementation

**Immediate Next Steps**:
1. Test economic scenarios with multiple borgs
2. Monitor system performance and reliability
3. Gather user feedback on fund management UI
4. Plan Phase 2B (mating markets and organ trading)

**Long-term Impact**:
- Enables true borg autonomy with persistent wealth
- Foundation for complex economic interactions
- Clear separation between operational and economic value
- Preparation for production deployment with real economic stakes

## Technical Architecture

### Currency Separation
```
WND (Westend Native)     USDB (BorgLife Stablecoin)
- Blockchain operations   - Borg wealth accumulation
- Gas fees                - Economic transfers
- Storage costs           - Off-chain payments
- Network fees            - Autonomous transactions
```

### Address Management
```
Borg DNA Hash → Deterministic Keypair → Substrate Address
    ↓              ↓                        ↓
Secure Storage  Encrypted Keys          On-Chain Balance
```

### Transfer Flow
```
Transfer Request → Balance Validation → Transaction Composition
       ↓                     ↓                    ↓
   Signing Keypair    →   Submit Extrinsic   →   Confirmation
       ↓                     ↓                    ↓
   Update Balances   →   Record Transaction  →   Audit Log

## Comprehensive Troubleshooting Guide

### Asset Creation Issues

#### Problem: Asset Creation Fails with "InsufficientBalance"
**Symptoms**: Transaction rejected with `DispatchError::Module { index: 6, error: 3 }`
**Root Cause**: Admin account lacks sufficient WND for existential deposit + fees
**Solution**:
1. Fund admin account with at least 0.1 WND via Westend faucet
2. Verify balance: `substrate.query('System', 'Account', [admin_address])`
3. Retry asset creation after funding

#### Problem: Metadata Setting Fails
**Symptoms**: Asset created but metadata not applied
**Root Cause**: Permission issues or invalid metadata format
**Solution**:
1. Verify admin account owns the asset
2. Check metadata format (name/symbol as bytes, valid decimals)
3. Use `assets.set_metadata` extrinsic with correct parameters

### Address Management Issues

#### Problem: Deterministic Address Generation Inconsistent
**Symptoms**: Same DNA hash produces different addresses
**Root Cause**: PBKDF2 parameters or salt generation issues
**Solution**:
1. Verify PBKDF2 parameters (iterations: 2048, hash: sha512)
2. Check salt format: `f"borglife-{borg_id}"`
3. Ensure consistent encoding (UTF-8) for inputs

### Transfer Protocol Issues

#### Problem: Transfer Validation Fails
**Symptoms**: Transfers rejected despite sufficient balance
**Root Cause**: Database balance inconsistency or validation logic errors
**Solution**:
1. Sync balances with on-chain state: `sync_borg_balance()`
2. Check database transaction isolation levels
3. Verify balance calculation logic (planck to token conversion)

## Best Practices Guide

### Development Best Practices
- Separate concerns: blockchain ops, database, business logic
- Use dependency injection for testability
- Implement comprehensive error handling
- Add detailed logging for debugging

### Security Practices
- Never log sensitive data (private keys, seeds)
- Use environment variables for configuration
- Implement least privilege access
- Regular security audits and penetration testing

### Operational Best Practices
- Monitor transaction success rates
- Alert on balance discrepancies
- Regular database backups
- Test backup restoration regularly

## Conclusion

This comprehensive PRP provides the technical foundation for BorgLife Phase 2A, enabling secure, scalable, and user-friendly fund holding and transfer capabilities. The detailed specifications, implementation guidance, and operational procedures ensure successful delivery of a production-ready economic system for autonomous borg interactions.
