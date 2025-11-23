"""
Borg Address Manager - Address Primary Key Version
Refactored to use blockchain addresses as primary database key instead of borg_id.

This version maintains all functionality while using substrate_address as the primary key
for better alignment with blockchain-native operations.
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from security.dna_anchor import DNAAanchor
from substrateinterface import Keypair

from .demo_audit_logger import DemoAuditLogger
from .secure_key_storage import SecureKeyStore


class BorgAddressManagerAddressPrimary:
    """
    Address-Primary Borg Address Manager for Phase 2A

    Uses blockchain addresses as primary database key instead of borg_id.
    Provides deterministic address generation and secure keypair storage.
    """

    def __init__(
        self,
        supabase_client=None,
        audit_logger: Optional[DemoAuditLogger] = None,
        keystore: Optional[SecureKeyStore] = None,
    ):
        """
        Initialize Address-Primary BorgAddressManager.

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
        try:
            self.secure_storage.unlock_keystore()
            self.audit_logger.log_event(
                "keystore_auto_unlocked",
                "Keystore automatically unlocked using macOS Keychain",
                {"demo_mode": True, "storage": "macos_keychain"},
            )
        except Exception as e:
            self.audit_logger.log_event(
                "keystore_unlock_failed",
                f"Failed to auto-unlock keystore: {str(e)}",
                {"error": str(e)},
            )

        self.dna_anchor = DNAAanchor(audit_logger)

        # Cache for lookups: address -> borg_data and borg_id -> address
        self._address_cache: Dict[str, Dict[str, Any]] = {}  # address -> full record
        self._borg_id_cache: Dict[str, str] = {}  # borg_id -> address

        # Creator signature verification storage
        self._creator_keys: Dict[str, str] = {}  # address -> creator_public_key

    def generate_deterministic_keypair(self, dna_hash: str) -> Keypair:
        """
        Generate deterministic keypair from DNA hash.

        Args:
            dna_hash: 64-character hex DNA hash

        Returns:
            Substrate keypair for the borg
        """
        if not self._is_valid_dna_hash(dna_hash):
            raise ValueError(f"Invalid DNA hash format: {dna_hash}")

        # Create deterministic seed from DNA hash
        seed_bytes = bytes.fromhex(dna_hash[:64])  # 32 bytes
        seed = seed_bytes.hex()

        # Generate keypair from seed
        keypair = Keypair.create_from_seed(seed)

        self.audit_logger.log_event(
            "keypair_generated",
            f"Deterministic keypair generated for DNA hash {dna_hash[:16]}...",
            {"dna_hash_prefix": dna_hash[:16], "address": keypair.ss58_address},
        )

        return keypair

    def register_borg_address(
        self,
        borg_id: str,
        dna_hash: str,
        creator_signature: Optional[str] = None,
        creator_public_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a borg's address using address as primary key.

        Args:
            borg_id: Unique borg identifier
            dna_hash: Borg's DNA hash
            creator_signature: Optional creator signature
            creator_public_key: Optional creator public key

        Returns:
            Registration result with address and status
        """
        try:
            # Generate deterministic keypair
            keypair = self.generate_deterministic_keypair(dna_hash)
            address = keypair.ss58_address

            # Store keypair securely in macOS Keychain using address-based service name
            service_name = f"borglife-address-{address}"
            success = self._store_keypair_in_keychain(service_name, keypair)

            if not success:
                raise Exception("Failed to store keypair in macOS Keychain")

            # Store minimal metadata in keystore
            keystore_data = {
                "borg_id": borg_id,
                "dna_hash": dna_hash,
                "address": address,
                "created_at": datetime.utcnow().isoformat(),
                "storage_method": "macos_keychain_address_primary",
            }

            # Store metadata in keystore file using address as key
            success = self.secure_storage.store_keypair(address, keypair, keystore_data)
            if not success:
                raise Exception("Failed to store keystore metadata")

            self.audit_logger.log_event(
                "borg_keychain_storage_success",
                f"Keypair stored in macOS Keychain for address {address}",
                {"borg_id": borg_id, "address": address, "service_name": service_name},
            )

            # Anchor DNA hash on-chain
            anchoring_tx_hash = self.dna_anchor.anchor_dna_hash(dna_hash, borg_id)

            # Prepare database record with address as primary key
            address_record = {
                "substrate_address": address,  # PRIMARY KEY
                "borg_id": borg_id,  # Now a regular field
                "dna_hash": dna_hash,
                "creator_public_key": creator_public_key,
                "creator_signature": creator_signature,
                "anchoring_tx_hash": anchoring_tx_hash,
                "anchoring_status": "confirmed",
                "key_storage_method": "macos_keychain_address_primary",
                "created_at": datetime.utcnow().isoformat(),
                "last_sync": datetime.utcnow().isoformat(),
            }

            # Store in Supabase if available
            if self.supabase:
                try:
                    # Insert or update using address as primary key
                    result = (
                        self.supabase.table("borg_addresses")
                        .upsert(
                            address_record,
                            on_conflict="substrate_address",  # Address is now primary key
                        )
                        .execute()
                    )

                    # Initialize balance records for both currencies
                    for currency in ["WND", "USDB"]:
                        balance_record = {
                            "substrate_address": address,  # Reference address instead of borg_id
                            "currency": currency,
                            "balance_wei": 0,
                            "last_updated": datetime.utcnow().isoformat(),
                        }
                        self.supabase.table("borg_balances").upsert(
                            balance_record,
                            on_conflict="substrate_address,currency",  # Composite key with address
                        ).execute()

                except Exception as db_error:
                    self.audit_logger.log_event(
                        "supabase_storage_failed",
                        f"Failed to store borg {borg_id} in Supabase: {str(db_error)}",
                        {
                            "borg_id": borg_id,
                            "address": address,
                            "error": str(db_error),
                        },
                    )
                    print(f"⚠️  Supabase storage failed: {db_error}")

                self.audit_logger.log_event(
                    "borg_registered_address_primary",
                    f"Borg {borg_id} registered with address {address} (Address-Primary Keychain)",
                    {"borg_id": borg_id, "address": address},
                )

                # Update caches
                self._address_cache[address] = address_record
                self._borg_id_cache[borg_id] = address

                return {
                    "success": True,
                    "borg_id": borg_id,
                    "address": address,
                    "dna_hash": dna_hash,
                    "storage_method": "macos_keychain_address_primary",
                }
            else:
                # Fallback without database
                return {
                    "success": True,
                    "borg_id": borg_id,
                    "address": address,
                    "dna_hash": dna_hash,
                    "storage_method": "macos_keychain_address_primary",
                    "warning": "No database connection - address not persisted",
                }

        except Exception as e:
            self.audit_logger.log_event(
                "borg_registration_failed",
                f"Failed to register borg {borg_id}: {str(e)}",
                {"borg_id": borg_id, "error": str(e)},
            )
            return {"success": False, "error": str(e), "borg_id": borg_id}

    def _store_keypair_in_keychain(self, service_name: str, keypair: Keypair) -> bool:
        """Store keypair components in macOS Keychain."""
        try:
            import keyring

            # Store each component separately for security
            keyring.set_password(service_name, "private_key", keypair.private_key.hex())
            keyring.set_password(service_name, "public_key", keypair.public_key.hex())
            keyring.set_password(service_name, "address", keypair.ss58_address)
            keyring.set_password(service_name, "borg_id", "")  # Placeholder for borg_id

            return True
        except Exception as e:
            self.audit_logger.log_event(
                "keychain_storage_failed",
                f"Failed to store keypair in macOS Keychain: {str(e)}",
                {"service_name": service_name, "error": str(e)},
            )
            return False

    def get_borg_address(self, borg_id: str) -> Optional[str]:
        """
        Get substrate address for a borg (lookup by borg_id).

        Args:
            borg_id: Borg identifier

        Returns:
            Substrate address or None if not found
        """
        # Check cache first
        if borg_id in self._borg_id_cache:
            return self._borg_id_cache[borg_id]

        # Query database
        if self.supabase:
            try:
                rest_result = (
                    self.supabase.table("borg_addresses")
                    .select("substrate_address")
                    .eq("borg_id", borg_id)
                    .execute()
                )
                if rest_result.data:
                    address = rest_result.data[0]["substrate_address"]
                    # Update caches
                    self._borg_id_cache[borg_id] = address
                    return address

            except Exception as e:
                self.audit_logger.log_event(
                    "address_lookup_failed",
                    f"Failed to lookup address for borg {borg_id}: {str(e)}",
                    {"borg_id": borg_id, "error": str(e)},
                )

        return None

    def get_borg_id(self, address: str) -> Optional[str]:
        """
        Get borg_id for an address (lookup by address).

        Args:
            address: Substrate address

        Returns:
            Borg ID or None if not found
        """
        # Check cache first
        if address in self._address_cache:
            return self._address_cache[address].get("borg_id")

        # Query database
        if self.supabase:
            try:
                rest_result = (
                    self.supabase.table("borg_addresses")
                    .select("borg_id")
                    .eq("substrate_address", address)
                    .execute()
                )
                if rest_result.data:
                    borg_id = rest_result.data[0]["borg_id"]
                    # Update cache if we have full record
                    if address not in self._address_cache:
                        # Fetch full record for cache
                        full_result = (
                            self.supabase.table("borg_addresses")
                            .select("*")
                            .eq("substrate_address", address)
                            .execute()
                        )
                        if full_result.data:
                            self._address_cache[address] = full_result.data[0]
                            self._borg_id_cache[borg_id] = address
                    return borg_id

            except Exception as e:
                self.audit_logger.log_event(
                    "borg_id_lookup_failed",
                    f"Failed to lookup borg_id for address {address}: {str(e)}",
                    {"address": address, "error": str(e)},
                )

        return None

    def get_borg_keypair(self, identifier: str) -> Optional[Keypair]:
        """
        Retrieve borg keypair using address-based keyring service.

        Can accept either borg_id or address as identifier.

        Args:
            identifier: Borg ID or substrate address

        Returns:
            Keypair from macOS Keychain or None if not found
        """
        try:
            # Determine if identifier is address or borg_id
            address = None
            borg_id = None

            if identifier.startswith("5"):  # SS58 address format
                address = identifier
                borg_id = self.get_borg_id(address)
            else:
                # Assume it's a borg_id
                borg_id = identifier
                address = self.get_borg_address(borg_id)

            if not address:
                self.audit_logger.log_event(
                    "keypair_lookup_failed",
                    f"Could not resolve address for identifier {identifier}",
                    {"identifier": identifier},
                )
                return None

            # Use address-based service name
            service_name = f"borglife-address-{address}"

            # Retrieve keypair components from macOS Keychain
            import keyring

            private_key_hex = keyring.get_password(service_name, "private_key")
            public_key_hex = keyring.get_password(service_name, "public_key")
            stored_address = keyring.get_password(service_name, "address")

            if not private_key_hex or not public_key_hex or not stored_address:
                self.audit_logger.log_event(
                    "keypair_not_found",
                    f"No keypair found in macOS Keychain for {identifier}",
                    {"identifier": identifier, "service_name": service_name},
                )
                return None

            # Verify address matches
            if stored_address != address:
                self.audit_logger.log_event(
                    "keypair_address_mismatch",
                    f"Keyring address mismatch for {identifier}: expected {address}, got {stored_address}",
                    {
                        "identifier": identifier,
                        "expected": address,
                        "stored": stored_address,
                    },
                )
                return None

            # Reconstruct keypair from private key
            try:
                private_key = bytes.fromhex(private_key_hex)
                keypair = Keypair(private_key=private_key)

                # Verify keypair integrity
                if (
                    keypair.public_key.hex() != public_key_hex
                    or keypair.ss58_address != address
                ):
                    self.audit_logger.log_event(
                        "keypair_integrity_check_failed",
                        f"Keypair integrity check failed for {identifier}",
                        {"identifier": identifier},
                    )
                    return None

            except Exception as key_error:
                self.audit_logger.log_event(
                    "keypair_reconstruction_failed",
                    f"Failed to reconstruct keypair for {identifier}: {str(key_error)}",
                    {"identifier": identifier, "error": str(key_error)},
                )
                return None

            self.audit_logger.log_event(
                "keypair_retrieved_from_keychain",
                f"Keypair successfully retrieved from macOS Keychain for {identifier}",
                {
                    "identifier": identifier,
                    "address": address,
                    "service_name": service_name,
                },
            )

            return keypair

        except Exception as e:
            self.audit_logger.log_event(
                "keypair_retrieval_error",
                f"Error retrieving keypair for {identifier}: {str(e)}",
                {"identifier": identifier, "error": str(e)},
            )
            return None

    def sync_balance(self, identifier: str, currency: str, balance_wei: int) -> bool:
        """
        Sync borg balance with database using address as primary key.

        Args:
            identifier: Borg ID or address
            currency: 'WND' or 'USDB'
            balance_wei: Balance in wei/planck units

        Returns:
            True if sync successful
        """
        if not self.supabase:
            return False

        if currency not in ["WND", "USDB"]:
            raise ValueError(f"Invalid currency: {currency}")

        # Resolve address
        address = (
            identifier
            if identifier.startswith("5")
            else self.get_borg_address(identifier)
        )
        if not address:
            return False

        try:
            balance_record = {
                "substrate_address": address,
                "currency": currency,
                "balance_wei": balance_wei,
                "last_updated": datetime.utcnow().isoformat(),
            }

            self.supabase.table("borg_balances").upsert(
                balance_record, on_conflict="substrate_address,currency"
            ).execute()

            self.audit_logger.log_event(
                "balance_synced",
                f"Balance synced for {identifier}: {balance_wei} {currency}",
                {
                    "identifier": identifier,
                    "address": address,
                    "currency": currency,
                    "balance_wei": balance_wei,
                },
            )

            return True

        except Exception as e:
            self.audit_logger.log_event(
                "balance_sync_failed",
                f"Failed to sync balance for {identifier}: {str(e)}",
                {"identifier": identifier, "currency": currency, "error": str(e)},
            )
            return False

    def get_balance(self, identifier: str, currency: str) -> Optional[int]:
        """
        Get borg balance from database using address as primary key.

        Args:
            identifier: Borg ID or address
            currency: 'WND' or 'USDB'

        Returns:
            Balance in wei/planck units or None if not found
        """
        if not self.supabase:
            return None

        if currency not in ["WND", "USDB"]:
            raise ValueError(f"Invalid currency: {currency}")

        # Resolve address
        address = (
            identifier
            if identifier.startswith("5")
            else self.get_borg_address(identifier)
        )
        if not address:
            return None

        try:
            result = (
                self.supabase.table("borg_balances")
                .select("balance_wei")
                .eq("substrate_address", address)
                .eq("currency", currency)
                .execute()
            )

            if result.data:
                balance = result.data[0]["balance_wei"]
                return balance
            else:
                return 0

        except Exception as e:
            self.audit_logger.log_event(
                "balance_lookup_failed",
                f"Failed to lookup balance for {identifier}: {str(e)}",
                {"identifier": identifier, "currency": currency, "error": str(e)},
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
            result = (
                self.supabase.table("borg_addresses")
                .select("borg_id,substrate_address,dna_hash")
                .execute()
            )
            return result.data or []
        except Exception as e:
            self.audit_logger.log_event(
                "borg_list_failed",
                f"Failed to list registered borgs: {str(e)}",
                {"error": str(e)},
            )
            return []

    def _is_valid_dna_hash(self, dna_hash: str) -> bool:
        """Validate DNA hash format."""
        if len(dna_hash) not in [64, 65]:
            return False

        try:
            int(dna_hash, 16)
            return True
        except ValueError:
            return False

    # Legacy compatibility methods
    def get_borg_keypair_by_id(self, borg_id: str) -> Optional[Keypair]:
        """Legacy method for backward compatibility."""
        return self.get_borg_keypair(borg_id)

    def get_borg_keypair_by_address(self, address: str) -> Optional[Keypair]:
        """Get keypair by address."""
        return self.get_borg_keypair(address)
