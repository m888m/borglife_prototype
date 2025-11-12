"""
Borg Address Manager for Phase 2A

Manages deterministic address generation and secure keypair storage for borgs.
Provides Supabase integration for address tracking and balance synchronization.
"""

import os
import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from substrateinterface import Keypair

from .secure_key_storage import SecureKeyStore
from .demo_audit_logger import DemoAuditLogger
from security.dna_anchor import DNAAanchor

class BorgAddressManager:
    """
    Manages borg-specific addresses and keypairs for fund holding.

    Provides deterministic address generation from DNA hashes and secure
    encrypted storage with Supabase integration.
    """

    def __init__(self, supabase_client=None, audit_logger: Optional[DemoAuditLogger] = None, keystore: Optional[SecureKeyStore] = None):
        """
        Initialize BorgAddressManager.

        Args:
            supabase_client: Supabase client for database operations
            audit_logger: Audit logger for compliance tracking
            keystore: Optional shared keystore instance (must be unlocked)
        """
        self.supabase = supabase_client
        self.audit_logger = audit_logger or DemoAuditLogger()

        # Use shared keystore if provided, otherwise create new one
        if keystore:
            self.secure_storage = keystore
            self._shared_keystore = True
        else:
            # Use unique keystore path to avoid conflicts
            import tempfile
            import uuid
            temp_dir = tempfile.gettempdir()
            unique_id = str(uuid.uuid4())[:8]
            keystore_path = f"{temp_dir}/borglife_keystore_{unique_id}.enc"
            self.secure_storage = SecureKeyStore(keystore_path)
            self._shared_keystore = False

        # Unlock keystore automatically using macOS Keychain
        # Hardware-backed security with no password required
        try:
            self.secure_storage.unlock_keystore()
            self.audit_logger.log_event(
                "keystore_auto_unlocked",
                "Keystore automatically unlocked using macOS Keychain",
                {"demo_mode": True, "storage": "macos_keychain"}
            )
        except Exception as e:
            self.audit_logger.log_event(
                "keystore_unlock_failed",
                f"Failed to auto-unlock keystore: {str(e)}",
                {"error": str(e)}
            )

        self.dna_anchor = DNAAanchor(audit_logger)

        # Cache for address lookups
        self._address_cache: Dict[str, Dict[str, Any]] = {}

        # Creator signature verification storage
        self._creator_keys: Dict[str, str] = {}  # borg_id -> creator_public_key

    def generate_deterministic_keypair(self, dna_hash: str) -> Keypair:
        """
        Generate deterministic keypair from DNA hash.

        Uses DNA hash as seed for reproducible keypair generation.
        This ensures borgs always have the same address from their DNA.

        Args:
            dna_hash: 64-character hex DNA hash

        Returns:
            Substrate keypair for the borg
        """
        if not self._is_valid_dna_hash(dna_hash):
            raise ValueError(f"Invalid DNA hash format: {dna_hash}")

        # Create deterministic seed from DNA hash
        # Use first 32 bytes of DNA hash as seed (Substrate seeds are 32 bytes)
        seed_bytes = bytes.fromhex(dna_hash[:64])  # 32 bytes
        seed = seed_bytes.hex()

        # Generate keypair from seed
        keypair = Keypair.create_from_seed(seed)

        self.audit_logger.log_event(
            "keypair_generated",
            f"Deterministic keypair generated for DNA hash {dna_hash[:16]}...",
            {"dna_hash_prefix": dna_hash[:16], "address": keypair.ss58_address}
        )

        return keypair

    def register_borg_address(self, borg_id: str, dna_hash: str, creator_signature: Optional[str] = None, creator_public_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a borg's address in the system with hardware-backed key storage.

        Generates deterministic keypair and stores it securely in macOS Keychain.
        No database fallback for key storage - maintains security through hardware isolation.

        Args:
            borg_id: Unique borg identifier
            dna_hash: Borg's DNA hash

        Returns:
            Registration result with address and status
        """
        try:
            # Generate deterministic keypair
            keypair = self.generate_deterministic_keypair(dna_hash)

            # Skip creator signature verification for test/demo mode
            # In production, this would be required for security
            if creator_signature and creator_public_key:
                self._creator_keys[borg_id] = creator_public_key

            # Store keypair securely in macOS Keychain
            service_name = f"borglife-borg-{borg_id}"
            success = self._store_keypair_in_keychain(service_name, keypair)

            if not success:
                raise Exception("Failed to store keypair in macOS Keychain")

            # Store minimal metadata in keystore (no sensitive data)
            keystore_data = {
                'borg_id': borg_id,
                'dna_hash': dna_hash,
                'address': keypair.ss58_address,
                'created_at': datetime.utcnow().isoformat(),
                'storage_method': 'macos_keychain'
            }

            # Store metadata in keystore file
            success = self.secure_storage.store_keypair(borg_id, keypair, keystore_data)
            if not success:
                raise Exception("Failed to store keystore metadata")

            self.audit_logger.log_event(
                "borg_keychain_storage_success",
                f"Keypair stored in macOS Keychain for borg {borg_id}",
                {"borg_id": borg_id, "address": keypair.ss58_address, "service_name": service_name}
            )

            # Anchor DNA hash on-chain for tamper-evident proof
            anchoring_tx_hash = self.dna_anchor.anchor_dna_hash(dna_hash, borg_id)

            # Prepare database record (no keypair data stored in DB)
            address_record = {
                'borg_id': borg_id,
                'substrate_address': keypair.ss58_address,
                'dna_hash': dna_hash,
                'creator_public_key': creator_public_key,
                'creator_signature': creator_signature,
                'anchoring_tx_hash': anchoring_tx_hash,
                'anchoring_status': 'confirmed',
                'key_storage_method': 'macos_keychain'
            }

            # Store in Supabase if available (address-primary schema)
            if self.supabase:
                try:
                    # Insert or update using REST API with address as primary key
                    result = self.supabase.table('borg_addresses').upsert(
                        address_record,
                        on_conflict='substrate_address'  # Address is now the primary key
                    ).execute()

                    # Initialize balance records for both currencies using address as foreign key
                    for currency in ['WND', 'USDB']:
                        balance_record = {
                            'substrate_address': keypair.ss58_address,  # Use address as foreign key
                            'currency': currency,
                            'balance_wei': 0
                        }
                        self.supabase.table('borg_balances').upsert(
                            balance_record,
                            on_conflict='substrate_address,currency'  # Address-based conflict resolution
                        ).execute()

                except Exception as db_error:
                    self.audit_logger.log_event(
                        "supabase_storage_failed",
                        f"Failed to store borg {borg_id} in Supabase: {str(db_error)}",
                        {"borg_id": borg_id, "error": str(db_error)}
                    )
                    print(f"⚠️  Supabase storage failed: {db_error}")
                    # Continue - keychain storage is secure even without DB

                self.audit_logger.log_event(
                    "borg_registered",
                    f"Borg {borg_id} registered with address {keypair.ss58_address} (Keychain secured)",
                    {"borg_id": borg_id, "address": keypair.ss58_address}
                )

                # Cache the address
                self._address_cache[borg_id] = address_record

                return {
                    'success': True,
                    'borg_id': borg_id,
                    'address': keypair.ss58_address,
                    'dna_hash': dna_hash,
                    'storage_method': 'macos_keychain'
                }
            else:
                # Fallback: just return the data without database storage
                return {
                    'success': True,
                    'borg_id': borg_id,
                    'address': keypair.ss58_address,
                    'dna_hash': dna_hash,
                    'storage_method': 'macos_keychain',
                    'warning': 'No database connection - address not persisted'
                }

        except Exception as e:
            self.audit_logger.log_event(
                "borg_registration_failed",
                f"Failed to register borg {borg_id}: {str(e)}",
                {"borg_id": borg_id, "error": str(e)}
            )
            return {
                'success': False,
                'error': str(e),
                'borg_id': borg_id
            }

    def _store_keypair_in_keychain(self, service_name: str, keypair: Keypair) -> bool:
        """Store keypair components in macOS Keychain."""
        try:
            # Store each component separately for security
            keyring.set_password(service_name, "private_key", keypair.private_key.hex())
            keyring.set_password(service_name, "public_key", keypair.public_key.hex())
            keyring.set_password(service_name, "address", keypair.ss58_address)

            return True
        except Exception as e:
            self.audit_logger.log_event(
                "keychain_storage_failed",
                f"Failed to store keypair in macOS Keychain: {str(e)}",
                {"service_name": service_name, "error": str(e)}
            )
            return False

    def get_borg_address(self, borg_id: str) -> Optional[str]:
        """
        Get substrate address for a borg.

        Args:
            borg_id: Borg identifier

        Returns:
            Substrate address or None if not found
        """
        # Check cache first
        if borg_id in self._address_cache:
            return self._address_cache[borg_id]['substrate_address']

        # Query database
        if self.supabase:
            try:
                # Use REST API instead of direct SQL
                rest_result = self.supabase.table('borg_addresses').select('substrate_address').eq('borg_id', borg_id).execute()
                if rest_result.data:
                    address = rest_result.data[0]['substrate_address']
                    # Cache it
                    self._address_cache[borg_id] = {'substrate_address': address}
                    return address

            except Exception as e:
                self.audit_logger.log_event(
                    "address_lookup_failed",
                    f"Failed to lookup address for borg {borg_id}: {str(e)}",
                    {"borg_id": borg_id, "error": str(e)}
                )

        return None

    def get_borg_keypair(self, borg_id: str) -> Optional[Keypair]:
        """
        Retrieve borg keypair from macOS Keychain with hardware-backed security.

        IMPORTANT: No fallback to database loading - maintains security by only using
        hardware-backed key storage. Keypairs must be created and stored in Keychain.

        Args:
            borg_id: Borg identifier

        Returns:
            Keypair from macOS Keychain or None if not found
        """
        try:
            # Get service name for this borg
            service_name = f"borglife-borg-{borg_id}"

            # Retrieve keypair components from macOS Keychain
            private_key_hex = keyring.get_password(service_name, "private_key")
            public_key_hex = keyring.get_password(service_name, "public_key")
            address = keyring.get_password(service_name, "address")

            if not private_key_hex or not public_key_hex or not address:
                self.audit_logger.log_event(
                    "keypair_not_found",
                    f"No keypair found in macOS Keychain for borg {borg_id}",
                    {"borg_id": borg_id, "service_name": service_name}
                )
                return None

            # Reconstruct keypair from private key
            try:
                private_key = bytes.fromhex(private_key_hex)
                keypair = Keypair(private_key=private_key)

                # Verify keypair integrity
                if (keypair.public_key.hex() != public_key_hex or
                    keypair.ss58_address != address):
                    self.audit_logger.log_event(
                        "keypair_integrity_check_failed",
                        f"Keypair integrity check failed for borg {borg_id}",
                        {"borg_id": borg_id}
                    )
                    return None

            except Exception as key_error:
                self.audit_logger.log_event(
                    "keypair_reconstruction_failed",
                    f"Failed to reconstruct keypair for borg {borg_id}: {str(key_error)}",
                    {"borg_id": borg_id, "error": str(key_error)}
                )
                return None

            self.audit_logger.log_event(
                "keypair_retrieved_from_keychain",
                f"Keypair successfully retrieved from macOS Keychain for borg {borg_id}",
                {"borg_id": borg_id, "address": address, "service_name": service_name}
            )

            return keypair

        except Exception as e:
            self.audit_logger.log_event(
                "keypair_retrieval_error",
                f"Error retrieving keypair for borg {borg_id}: {str(e)}",
                {"borg_id": borg_id, "error": str(e)}
            )
            return None

    def sync_balance(self, address: str, currency: str, balance_wei: int) -> bool:
        """
        Sync borg balance with database using address as primary key.

        Args:
            address: Substrate address (primary key)
            currency: 'WND' or 'USDB'
            balance_wei: Balance in wei/planck units

        Returns:
            True if sync successful
        """
        if not self.supabase:
            return False

        if currency not in ['WND', 'USDB']:
            raise ValueError(f"Invalid currency: {currency}")

        try:
            # Use REST API with address as primary key
            balance_record = {
                'substrate_address': address,
                'currency': currency,
                'balance_wei': balance_wei
            }

            self.supabase.table('borg_balances').upsert(
                balance_record,
                on_conflict='substrate_address,currency'
            ).execute()

            # Update local cache
            if not hasattr(self, '_balance_cache'):
                self._balance_cache = {}
            cache_key = f"{address}_{currency}"
            self._balance_cache[cache_key] = balance_wei

            self.audit_logger.log_event(
                "balance_synced",
                f"Balance synced for address {address}: {balance_wei} {currency}",
                {"address": address, "currency": currency, "balance_wei": balance_wei}
            )

            return True

        except Exception as e:
            self.audit_logger.log_event(
                "balance_sync_failed",
                f"Failed to sync balance for address {address}: {str(e)}",
                {"address": address, "currency": currency, "error": str(e)}
            )
            return False

    def get_balance(self, address: str, currency: str) -> Optional[int]:
        """
        Get borg balance from database using address as primary key.

        Args:
            address: Substrate address
            currency: 'WND' or 'USDB'

        Returns:
            Balance in wei/planck units or None if not found
        """
        if not self.supabase:
            return None

        if currency not in ['WND', 'USDB']:
            raise ValueError(f"Invalid currency: {currency}")

        try:
            # Use REST API with address as primary key
            result = self.supabase.table('borg_balances').select('balance_wei').eq('substrate_address', address).eq('currency', currency).execute()

            if result.data:
                balance = result.data[0]['balance_wei']
                # Update cache
                if not hasattr(self, '_balance_cache'):
                    self._balance_cache = {}
                cache_key = f"{address}_{currency}"
                self._balance_cache[cache_key] = balance
                return balance
            else:
                # No record found, return 0
                return 0

        except Exception as e:
            # Fallback to cache if available
            if hasattr(self, '_balance_cache'):
                cache_key = f"{address}_{currency}"
                return self._balance_cache.get(cache_key, 0)

            self.audit_logger.log_event(
                "balance_lookup_failed",
                f"Failed to lookup balance for address {address}: {str(e)}",
                {"address": address, "currency": currency, "error": str(e)}
            )
            return None

    def list_registered_borgs(self) -> List[Dict[str, Any]]:
        """
        List all registered borgs with their addresses.

        Returns:
            List of borg records with id, address, dna_hash
        """
        if not self.supabase:
            return []

        try:
            result = self.supabase.table('borg_addresses').select('borg_id,substrate_address,dna_hash').execute()
            return result.data or []
        except Exception as e:
            self.audit_logger.log_event(
                "borg_list_failed",
                f"Failed to list registered borgs: {str(e)}",
                {"error": str(e)}
            )
            return []

    def verify_creator_signature(self, borg_id: str, operation_data: str, signature: str, public_key: str) -> bool:
        """
        Verify creator signature for borg operations.

        Args:
            borg_id: Borg identifier
            operation_data: Data that was signed
            signature: Hex-encoded signature
            public_key: Creator's public key

        Returns:
            True if signature is valid
        """
        try:
            # For demo purposes, implement basic signature verification
            # In production, this would use proper cryptographic verification
            # For now, we'll use a simple hash-based verification for demo

            import hashlib
            import hmac

            # Create expected signature using HMAC-SHA256
            expected_signature = hmac.new(
                bytes.fromhex(public_key),
                operation_data.encode(),
                hashlib.sha256
            ).hexdigest()

            # Compare signatures (simplified for demo)
            is_valid = signature.lower() == expected_signature.lower()

            self.audit_logger.log_event(
                "signature_verification",
                f"Signature verification for borg {borg_id}",
                {
                    "borg_id": borg_id,
                    "operation": operation_data[:50] + "..." if len(operation_data) > 50 else operation_data,
                    "valid": is_valid
                }
            )

            return is_valid

        except Exception as e:
            self.audit_logger.log_event(
                "signature_verification_failed",
                f"Signature verification failed for borg {borg_id}: {str(e)}",
                {"borg_id": borg_id, "error": str(e)}
            )
            return False

    def _is_valid_dna_hash(self, dna_hash: str) -> bool:
        """
        Validate DNA hash format.

        Args:
            dna_hash: Hash to validate

        Returns:
            True if valid hex string (64 or 65 characters for SHA256/SHA3)
        """
        if len(dna_hash) not in [64, 65]:
            return False

        try:
            int(dna_hash, 16)
            return True
        except ValueError:
            return False

    def _get_usdb_asset_id(self) -> Optional[int]:
        """Get USDB asset ID from configuration."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', '.borglife_config')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        if line.startswith('USDB_ASSET_ID='):
                            return int(line.split('=', 1)[1].strip())
        except Exception as e:
            print(f"Warning: Could not read USDB asset ID from config: {e}")

        return None