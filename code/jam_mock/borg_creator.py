#!/usr/bin/env python3
"""
Borg Creator - Unified Borg Creation Module
Provides secure, production-ready borg creation with keyring storage and Supabase metadata.
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from substrateinterface import Keypair

from .borg_address_manager_address_primary import BorgAddressManagerAddressPrimary
from .demo_audit_logger import DemoAuditLogger


class BorgCreator:
    """
    Unified borg creation with enterprise-grade security.

    Handles:
    - Deterministic keypair generation from DNA hash
    - Secure keyring storage (address-based service names)
    - Supabase metadata storage (address as primary key)
    - Balance initialization
    - Keypair verification and retrieval
    """

    def __init__(self, supabase_client=None, audit_logger: Optional[DemoAuditLogger] = None):
        """
        Initialize BorgCreator.

        Args:
            supabase_client: Supabase client for metadata storage
            audit_logger: Optional audit logger
        """
        self.supabase = supabase_client
        self.audit_logger = audit_logger or DemoAuditLogger()
        self.manager = BorgAddressManagerAddressPrimary(
            supabase_client=supabase_client,
            audit_logger=self.audit_logger
        )

    def create_borg(
        self,
        borg_id: Optional[str] = None,
        dna_hash: Optional[str] = None,
        dna_content: Optional[str] = None,
        creator_signature: Optional[str] = None,
        creator_public_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new borg with full security pipeline.

        Args:
            borg_id: Optional custom borg ID (auto-generated if None)
            dna_hash: Optional DNA hash (computed from dna_content if None)
            dna_content: Optional DNA content to hash
            creator_signature: Optional creator signature
            creator_public_key: Optional creator public key

        Returns:
            Creation result with success status and borg details
        """
        try:
            # Generate identifiers
            if not borg_id:
                timestamp = int(time.time())
                borg_id = f"borg_{timestamp}"

            if not dna_hash:
                if dna_content:
                    dna_hash = hashlib.sha256(dna_content.encode()).hexdigest()
                else:
                    # Default DNA content
                    dna_hash = hashlib.sha256(f"default_dna_{borg_id}".encode()).hexdigest()

            # Validate DNA hash
            if not self._is_valid_dna_hash(dna_hash):
                return {
                    "success": False,
                    "error": f"Invalid DNA hash format: {dna_hash}"
                }

            self.audit_logger.log_event(
                "borg_creation_started",
                f"Starting borg creation for {borg_id}",
                {"borg_id": borg_id, "dna_hash": dna_hash[:16]}
            )

            # Register borg using manager (handles keypair gen, keyring storage, DB insert)
            result = self.manager.register_borg_address(
                borg_id=borg_id,
                dna_hash=dna_hash,
                creator_signature=creator_signature,
                creator_public_key=creator_public_key
            )

            if not result.get("success"):
                return result

            address = result["address"]

            # Verify keypair access
            verification = self.verify_keypair_access(address)
            if not verification["success"]:
                return {
                    "success": False,
                    "error": f"Keypair verification failed: {verification['error']}",
                    "borg_id": borg_id,
                    "address": address
                }

            # Confirm Supabase storage
            db_verification = self._verify_supabase_storage(address)
            if not db_verification["success"]:
                self.audit_logger.log_event(
                    "supabase_verification_warning",
                    f"Supabase verification failed for {borg_id}: {db_verification['error']}",
                    {"borg_id": borg_id, "address": address}
                )

            self.audit_logger.log_event(
                "borg_creation_completed",
                f"Borg {borg_id} created successfully",
                {
                    "borg_id": borg_id,
                    "address": address,
                    "dna_hash": dna_hash[:16],
                    "storage_method": result.get("storage_method")
                }
            )

            return {
                "success": True,
                "borg_id": borg_id,
                "address": address,
                "dna_hash": dna_hash,
                "storage_method": result.get("storage_method"),
                "keypair_verified": True,
                "supabase_verified": db_verification["success"]
            }

        except Exception as e:
            self.audit_logger.log_event(
                "borg_creation_failed",
                f"Borg creation failed: {str(e)}",
                {"borg_id": borg_id, "error": str(e)}
            )
            return {"success": False, "error": str(e), "borg_id": borg_id}

    def verify_keypair_access(self, identifier: str) -> Dict[str, Any]:
        """
        Verify that keypair can be retrieved from keyring.

        Args:
            identifier: Borg ID or address

        Returns:
            Verification result
        """
        try:
            keypair = self.manager.get_borg_keypair(identifier)
            if not keypair:
                return {"success": False, "error": "Keypair not found in keyring"}

            # Verify integrity
            expected_address = (
                identifier if identifier.startswith("5") else
                self.manager.get_borg_address(identifier)
            )

            if keypair.ss58_address != expected_address:
                return {"success": False, "error": "Address mismatch"}

            return {
                "success": True,
                "address": keypair.ss58_address,
                "public_key_prefix": keypair.public_key.hex()[:16],
                "private_key_prefix": keypair.private_key.hex()[:16]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_borg_keypair(self, identifier: str) -> Optional[Keypair]:
        """
        Retrieve borg keypair from keyring.

        Args:
            identifier: Borg ID or address

        Returns:
            Keypair or None if not found
        """
        return self.manager.get_borg_keypair(identifier)

    def get_borg_info(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get borg information from database.

        Args:
            identifier: Borg ID or address

        Returns:
            Borg info dict or None
        """
        if not self.supabase:
            return None

        try:
            address = (
                identifier if identifier.startswith("5") else
                self.manager.get_borg_address(identifier)
            )
            if not address:
                return None

            result = self.supabase.table("borg_addresses").select("*").eq("substrate_address", address).execute()
            return result.data[0] if result.data else None

        except Exception:
            return None

    def _verify_supabase_storage(self, address: str) -> Dict[str, Any]:
        """Verify borg metadata exists in Supabase."""
        try:
            if not self.supabase:
                return {"success": False, "error": "No Supabase client"}

            result = self.supabase.table("borg_addresses").select("*").eq("substrate_address", address).execute()
            if not result.data:
                return {"success": False, "error": "No record found"}

            record = result.data[0]
            return {
                "success": True,
                "borg_id": record.get("borg_id"),
                "dna_hash": record.get("dna_hash")
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _is_valid_dna_hash(self, dna_hash: str) -> bool:
        """Validate DNA hash format."""
        if len(dna_hash) not in [64, 65]:
            return False
        try:
            int(dna_hash, 16)
            return True
        except ValueError:
            return False