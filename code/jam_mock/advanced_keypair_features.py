"""
Advanced Keypair Features for Westend Testnet Operations

Extends basic keypair management with secure key derivation, address generation,
transaction validation, and development mode features.
"""

import binascii
import hashlib
import os
import re
import secrets
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import base58
from substrateinterface import Keypair, KeypairType
from substrateinterface.utils.ss58 import ss58_decode, ss58_encode

from .keypair_manager import KeypairManager, KeypairSecurityError


class AdvancedKeypairManager(KeypairManager):
    """
    Extended keypair manager with advanced features for Westend operations.

    Adds secure key derivation, transaction validation, fee estimation,
    and development mode capabilities.
    """

    def __init__(self, storage_path: Optional[str] = None):
        super().__init__(storage_path)

        # Development mode settings
        self.development_mode = (
            os.getenv("BORGLIFE_ENV", "development").lower() == "development"
        )
        self.temp_keys_created = []

        # Transaction settings
        self.default_priority = "normal"  # low, normal, high
        self.max_transaction_fee = Decimal("0.1")  # Max 0.1 WND per transaction

        # Network parameters
        self.network_prefix = 42  # Westend SS58 prefix (testnet)
        self.keypair_type = KeypairType.SR25519

    def create_keypair_from_mnemonic(
        self, name: str, mnemonic: str, save_to_disk: bool = True
    ) -> Dict[str, Any]:
        """
        Create keypair from BIP39 mnemonic phrase.

        Args:
            name: Keypair name
            mnemonic: 12 or 24 word mnemonic phrase
            save_to_disk: Whether to save to disk

        Returns:
            Keypair information
        """
        try:
            # Validate mnemonic format
            self._validate_mnemonic(mnemonic)

            # Create keypair from mnemonic
            keypair = Keypair.create_from_mnemonic(
                mnemonic=mnemonic, ss58_format=self.network_prefix
            )

            public_info = {
                "name": name,
                "public_key": keypair.public_key.hex(),
                "ss58_address": keypair.ss58_address,
                "ss58_format": self.network_prefix,
                "created_at": self._get_timestamp(),
                "fingerprint": self._generate_fingerprint(keypair.public_key.hex()),
                "derivation_method": "mnemonic",
                "mnemonic_words": len(mnemonic.split()),
            }

            self._keypair_cache[name] = keypair

            if save_to_disk:
                self._save_keypair_to_disk(name, keypair, public_info)

            return public_info

        except Exception as e:
            raise KeypairSecurityError(f"Invalid mnemonic: {e}")

    def create_keypair_from_uri(
        self, name: str, uri: str, save_to_disk: bool = True
    ) -> Dict[str, Any]:
        """
        Create keypair from Polkadot.js style URI with derivation path support.

        Args:
            name: Keypair name
            uri: URI string (e.g., "mnemonic///password", "//Alice", "0x...")
            save_to_disk: Whether to save to disk

        Returns:
            Keypair information
        """
        try:
            # Parse URI components
            uri_parts = self._parse_uri(uri)

            # Create keypair based on URI type
            if uri_parts["type"] == "hex":
                keypair = Keypair.create_from_seed(
                    seed_hex=uri_parts["seed"], ss58_format=self.network_prefix
                )
            elif uri_parts["type"] == "mnemonic":
                keypair = Keypair.create_from_mnemonic(
                    mnemonic=uri_parts["mnemonic"],
                    passphrase=uri_parts.get("password", ""),
                    ss58_format=self.network_prefix,
                )
            else:
                raise ValueError(f"Unsupported URI type: {uri_parts['type']}")

            public_info = {
                "name": name,
                "public_key": keypair.public_key.hex(),
                "ss58_address": keypair.ss58_address,
                "ss58_format": self.network_prefix,
                "created_at": self._get_timestamp(),
                "fingerprint": self._generate_fingerprint(keypair.public_key.hex()),
                "derivation_method": uri_parts["type"],
                "uri_components": {
                    k: v for k, v in uri_parts.items() if k != "password"
                },  # Don't store password
            }

            self._keypair_cache[name] = keypair

            if save_to_disk:
                self._save_keypair_to_disk(name, keypair, public_info)

            return public_info

        except Exception as e:
            raise KeypairSecurityError(f"Invalid URI: {e}")

    def validate_address(self, address: str) -> Tuple[bool, str]:
        """
        Validate Westend SS58 address format and checksum.

        Args:
            address: SS58 address to validate

        Returns:
            (is_valid, error_message)
        """
        try:
            # Decode address
            public_key_bytes, ss58_format = ss58_decode(address)

            # Check network prefix
            if ss58_format != self.network_prefix:
                return (
                    False,
                    f"Invalid network prefix: {ss58_format}, expected {self.network_prefix} (Westend)",
                )

            # Verify length (32 bytes for public key)
            if len(public_key_bytes) != 32:
                return (
                    False,
                    f"Invalid public key length: {len(public_key_bytes)} bytes",
                )

            return True, "Valid Westend address"

        except Exception as e:
            return False, f"Invalid address format: {e}"

    def estimate_transaction_fee(
        self, keypair_name: str, transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate transaction fee for a Westend transaction.

        Args:
            keypair_name: Keypair to use for estimation
            transaction_data: Transaction details

        Returns:
            Fee estimation details
        """
        try:
            keypair = self.load_keypair(keypair_name)

            # Base fee calculation (simplified for Phase 1)
            base_fee = Decimal("0.0001")  # Base fee in WND

            # Size-based fee
            tx_size = self._estimate_transaction_size(transaction_data)
            size_fee = Decimal(str(tx_size)) * Decimal("0.000001")  # Per byte fee

            # Priority multiplier
            priority_multiplier = {
                "low": Decimal("0.8"),
                "normal": Decimal("1.0"),
                "high": Decimal("1.5"),
            }.get(self.default_priority, Decimal("1.0"))

            total_fee = (base_fee + size_fee) * priority_multiplier

            # Check against maximum
            if total_fee > self.max_transaction_fee:
                total_fee = self.max_transaction_fee

            return {
                "estimated_fee": total_fee,
                "base_fee": base_fee,
                "size_fee": size_fee,
                "priority_multiplier": priority_multiplier,
                "priority": self.default_priority,
                "max_fee": self.max_transaction_fee,
                "currency": "WND",
            }

        except Exception as e:
            return {
                "error": f"Fee estimation failed: {e}",
                "estimated_fee": Decimal("0"),
                "currency": "WND",
            }

    def validate_transaction(
        self, keypair_name: str, transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate transaction before signing and submission.

        Args:
            keypair_name: Keypair name
            transaction_data: Transaction to validate

        Returns:
            Validation results
        """
        validation_results = {"valid": True, "warnings": [], "errors": []}

        try:
            keypair = self.load_keypair(keypair_name)

            # Check keypair validity
            if not keypair.public_key:
                validation_results["errors"].append("Invalid keypair")

            # Validate transaction structure
            required_fields = ["borg_id", "dna_hash"]
            for field in required_fields:
                if field not in transaction_data:
                    validation_results["errors"].append(
                        f"Missing required field: {field}"
                    )

            # Validate DNA hash format
            dna_hash = transaction_data.get("dna_hash", "")
            if not self._is_valid_hash(dna_hash):
                validation_results["errors"].append("Invalid DNA hash format")

            # Check borg_id format
            borg_id = transaction_data.get("borg_id", "")
            if not self._is_valid_borg_id(borg_id):
                validation_results["errors"].append("Invalid borg ID format")

            # Fee estimation and validation
            fee_info = self.estimate_transaction_fee(keypair_name, transaction_data)
            if "error" in fee_info:
                validation_results["warnings"].append(
                    f"Fee estimation failed: {fee_info['error']}"
                )
            elif fee_info["estimated_fee"] > self.max_transaction_fee:
                validation_results["warnings"].append(
                    f"High fee: {fee_info['estimated_fee']} WND"
                )

            # Development mode warnings
            if self.development_mode:
                validation_results["warnings"].append(
                    "Development mode: Using test keys"
                )

            validation_results["valid"] = len(validation_results["errors"]) == 0

        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Validation failed: {e}")

        return validation_results

    def create_development_keypair(self, name: str = None) -> Dict[str, Any]:
        """
        Create a temporary keypair for development/testing purposes.

        WARNING: These keys are not secure and should never be used with real funds!
        """
        if not self.development_mode:
            raise KeypairSecurityError(
                "Development keypairs only available in development mode"
            )

        if name is None:
            name = f"dev_{secrets.token_hex(4)}"

        # Create keypair with warning
        print("⚠️  WARNING: Creating development keypair - NOT SECURE FOR PRODUCTION!")
        print("   This keypair should NEVER be used with real funds!")

        info = self.create_keypair(name, save_to_disk=False)
        info["development_only"] = True
        info["security_warning"] = (
            "This is a development keypair - not secure for production"
        )

        self.temp_keys_created.append(name)

        return info

    def cleanup_development_keys(self):
        """Clean up temporary development keypairs."""
        for name in self.temp_keys_created:
            if name in self._keypair_cache:
                del self._keypair_cache[name]

        self.temp_keys_created.clear()
        print("✅ Development keypairs cleaned up")

    def get_network_info(self) -> Dict[str, Any]:
        """Get current network configuration."""
        return {
            "network": "Westend",
            "ss58_prefix": self.network_prefix,
            "keypair_type": self.keypair_type.value,
            "development_mode": self.development_mode,
            "max_transaction_fee": self.max_transaction_fee,
            "default_priority": self.default_priority,
        }

    def _validate_mnemonic(self, mnemonic: str):
        """Validate BIP39 mnemonic format."""
        words = mnemonic.strip().split()

        # Check word count (12 or 24 words)
        if len(words) not in [12, 24]:
            raise ValueError(
                f"Invalid mnemonic length: {len(words)} words (must be 12 or 24)"
            )

        # Basic word validation (could be enhanced with wordlist check)
        for word in words:
            if not re.match(r"^[a-z]+$", word):
                raise ValueError(f"Invalid mnemonic word: {word}")

    def _parse_uri(self, uri: str) -> Dict[str, Any]:
        """Parse Polkadot.js style URI."""
        uri_parts = {}

        # Handle hex seed
        if uri.startswith("0x"):
            if len(uri) != 66:  # 0x + 64 hex chars
                raise ValueError("Invalid hex seed length")
            uri_parts["type"] = "hex"
            uri_parts["seed"] = uri[2:]  # Remove 0x prefix
            return uri_parts

        # Handle mnemonic with password
        if "///" in uri:
            parts = uri.split("///", 1)
            uri_parts["mnemonic"] = parts[0]
            uri_parts["password"] = parts[1]
        else:
            uri_parts["mnemonic"] = uri

        uri_parts["type"] = "mnemonic"
        self._validate_mnemonic(uri_parts["mnemonic"])

        return uri_parts

    def _estimate_transaction_size(self, transaction_data: Dict[str, Any]) -> int:
        """Estimate transaction size in bytes."""
        # Rough estimation for system.remark extrinsic
        base_size = 100  # Base extrinsic size
        data_size = len(str(transaction_data).encode("utf-8"))
        return base_size + data_size

    def _is_valid_hash(self, hash_str: str) -> bool:
        """Validate hash format (64 hex characters)."""
        if len(hash_str) != 64:
            return False
        try:
            int(hash_str, 16)
            return True
        except ValueError:
            return False

    def _is_valid_borg_id(self, borg_id: str) -> bool:
        """Validate borg ID format."""
        # Borg IDs should be alphanumeric with hyphens
        return bool(re.match(r"^[a-zA-Z0-9\-_]+$", borg_id) and len(borg_id) <= 50)

    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, "temp_keys_created"):
            self.cleanup_development_keys()


class TransactionSigner:
    """
    Handles transaction signing and submission for Westend operations.
    """

    def __init__(self, keypair_manager: AdvancedKeypairManager):
        self.keypair_manager = keypair_manager

    async def sign_and_submit_transaction(
        self, keypair_name: str, transaction_data: Dict[str, Any], westend_adapter
    ) -> Dict[str, Any]:
        """
        Sign and submit a transaction to Westend.

        Args:
            keypair_name: Keypair to use for signing
            transaction_data: Transaction details
            westend_adapter: WestendAdapter instance

        Returns:
            Transaction result
        """
        # Validate transaction first
        validation = self.keypair_manager.validate_transaction(
            keypair_name, transaction_data
        )
        if not validation["valid"]:
            return {
                "success": False,
                "error": "Validation failed",
                "validation_errors": validation["errors"],
                "validation_warnings": validation["warnings"],
            }

        # Get fee estimate
        fee_info = self.keypair_manager.estimate_transaction_fee(
            keypair_name, transaction_data
        )

        # Submit transaction via adapter
        try:
            result = await westend_adapter.store_dna_hash(
                borg_id=transaction_data["borg_id"],
                dna_hash=transaction_data["dna_hash"],
                metadata=transaction_data.get("metadata"),
            )

            # Add fee information to result
            result["fee_info"] = fee_info
            result["validation_warnings"] = validation["warnings"]

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Transaction failed: {e}",
                "fee_info": fee_info,
            }
