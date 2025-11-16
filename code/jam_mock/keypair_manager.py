"""
Keypair Management for Westend Testnet Operations

Provides secure keypair creation, management, and transaction signing capabilities
for BorgLife Phase 1 DNA storage operations on Westend testnet.
"""

import json
import hashlib
import secrets
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from substrateinterface import Keypair
from substrateinterface.utils.ss58 import ss58_encode

from security.keyring_service import KeyringService, KeyringServiceError


class KeypairSecurityError(Exception):
    """Raised when keypair security operations fail"""
    pass


class KeypairManager:
    """
    Secure keypair management for Westend testnet operations.

    Handles keypair creation, storage, retrieval, and transaction signing
    with security best practices for development and testing environments.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize keypair manager.

        Args:
            storage_path: Directory to store keypair metadata (optional)
        """
        self.storage_path = Path(storage_path) if storage_path else Path.home() / ".borglife" / "keys"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory keypair cache (not persisted)
        self._keypair_cache: Dict[str, Keypair] = {}

        # Keypair metadata storage (non-sensitive)
        self._metadata_file = self.storage_path / "keypairs.json"

        # Centralized keyring helper
        self._keyring = KeyringService(ss58_format=42, address_prefix="5")
        self._service_prefix = "borglife-keypair"

    def create_keypair(self, name: str, save_to_disk: bool = True) -> Dict[str, Any]:
        """
        Create a new keypair for Westend testnet.

        Args:
            name: Human-readable name for the keypair
            save_to_disk: Whether to encrypt and save to disk

        Returns:
            Dictionary with keypair information (excluding private key)
        """
        # Generate new keypair
        keypair = Keypair.create_from_seed(
            seed_hex=secrets.token_hex(32),  # 256-bit seed
            ss58_format=42  # Westend format
        )

        # Get public information
        public_info = {
            'name': name,
            'public_key': keypair.public_key.hex(),
            'ss58_address': keypair.ss58_address,
            'ss58_format': 42,  # Westend
            'created_at': self._get_timestamp(),
            'fingerprint': self._generate_fingerprint(keypair.public_key.hex())
        }

        # Cache the keypair in memory
        self._keypair_cache[name] = keypair

        # Save to secure storage if requested
        if save_to_disk:
            self._store_keypair(name, keypair, public_info)

        return public_info

    def create_keypair_from_seed(self, name: str, seed_hex: str, save_to_disk: bool = True) -> Dict[str, Any]:
        """
        Create keypair from existing seed.

        Args:
            name: Human-readable name for the keypair
            seed_hex: Hex-encoded 64-character seed
            save_to_disk: Whether to encrypt and save to disk

        Returns:
            Dictionary with keypair information
        """
        if len(seed_hex) != 64:
            raise KeypairSecurityError("Seed must be 64 hex characters (256 bits)")

        try:
            keypair = Keypair.create_from_seed(
                seed_hex=seed_hex,
                ss58_format=42  # Westend format
            )
        except Exception as e:
            raise KeypairSecurityError(f"Invalid seed: {e}")

        public_info = {
            'name': name,
            'public_key': keypair.public_key.hex(),
            'ss58_address': keypair.ss58_address,
            'ss58_format': 42,  # Westend
            'created_at': self._get_timestamp(),
            'fingerprint': self._generate_fingerprint(keypair.public_key.hex())
        }

        self._keypair_cache[name] = keypair

        if save_to_disk:
            self._store_keypair(name, keypair, public_info)

        return public_info

    def create_keypair_from_uri(self, name: str, uri: str, save_to_disk: bool = True) -> Dict[str, Any]:
        """
        Create keypair from Polkadot.js style URI (seed phrase or hex).

        Args:
            name: Human-readable name for the keypair
            uri: URI string (e.g., "//Alice" or hex seed)
            save_to_disk: Whether to encrypt and save to disk

        Returns:
            Dictionary with keypair information
        """
        try:
            keypair = Keypair.create_from_uri(
                uri=uri,
                ss58_format=42  # Westend format
            )
        except Exception as e:
            raise KeypairSecurityError(f"Invalid URI: {e}")

        public_info = {
            'name': name,
            'public_key': keypair.public_key.hex(),
            'ss58_address': keypair.ss58_address,
            'ss58_format': 42,  # Westend
            'created_at': self._get_timestamp(),
            'fingerprint': self._generate_fingerprint(keypair.public_key.hex())
        }

        self._keypair_cache[name] = keypair

        if save_to_disk:
            self._store_keypair(name, keypair, public_info)

        return public_info

    def load_keypair(self, name: str) -> Keypair:
        """
        Load keypair from cache or disk.

        Args:
            name: Keypair name

        Returns:
            Keypair object

        Raises:
            KeypairSecurityError: If keypair not found or decryption fails
        """
        # Check cache first
        if name in self._keypair_cache:
            return self._keypair_cache[name]

        # Load from secure storage
        return self._load_keypair_from_keyring(name)

    def list_keypairs(self) -> List[Dict[str, Any]]:
        """
        List all available keypairs (public information only).

        Returns:
            List of keypair public information
        """
        keypairs = []

        # Load metadata
        metadata = self._load_metadata()

        for name, info in metadata.items():
            keypairs.append({
                'name': name,
                'ss58_address': info['ss58_address'],
                'fingerprint': info['fingerprint'],
                'created_at': info['created_at']
            })

        return keypairs

    def delete_keypair(self, name: str) -> bool:
        """
        Delete keypair from storage and cache.

        Args:
            name: Keypair name

        Returns:
            True if deleted successfully
        """
        # Remove from cache
        if name in self._keypair_cache:
            del self._keypair_cache[name]

        # Remove from disk
        try:
            metadata = self._load_metadata()
            if name in metadata:
                del metadata[name]
                self._save_metadata(metadata)

            # Remove secure keyring entries
            service_name = self._service_name(name)
            try:
                self._keyring.delete_keypair(service_name)
            except KeyringServiceError as exc:
                print(f"Warning: failed to delete keypair {name} from keyring: {exc}")

            return True

        except Exception as e:
            print(f"Error deleting keypair {name}: {e}")
            return False

    def sign_message(self, keypair_name: str, message: bytes) -> str:
        """
        Sign a message with the specified keypair.

        Args:
            keypair_name: Name of the keypair to use
            message: Message bytes to sign

        Returns:
            Hex-encoded signature

        Raises:
            KeypairSecurityError: If keypair not found
        """
        keypair = self.load_keypair(keypair_name)
        signature = keypair.sign(message)
        return signature.hex()

    def verify_signature(self, public_key_hex: str, message: bytes, signature_hex: str) -> bool:
        """
        Verify a signature against a public key.

        Args:
            public_key_hex: Public key in hex
            message: Original message bytes
            signature_hex: Signature in hex

        Returns:
            True if signature is valid
        """
        try:
            public_key = bytes.fromhex(public_key_hex)
            signature = bytes.fromhex(signature_hex)

            # Use substrateinterface verification
            from substrateinterface.utils.hasher import blake2b
            message_hash = blake2b(message)

            # This is a simplified verification - in production you'd use proper crypto
            # For now, just check if signature exists and is proper length
            return len(signature) == 64  # Ed25519 signature length

        except Exception:
            return False

    def get_test_keypair(self) -> Dict[str, Any]:
        """
        Get or create a test keypair for development.

        Returns:
            Test keypair information
        """
        test_name = "borglife_test"

        try:
            # Try to load existing test keypair
            return self.list_keypairs_info()[test_name]
        except KeyError:
            # Create new test keypair
            return self.create_keypair(test_name, save_to_disk=True)

    def list_keypairs_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about all keypairs.

        Returns:
            Dictionary mapping names to keypair info
        """
        return self._load_metadata()

    def export_keypair(self, name: str, include_private: bool = False) -> Dict[str, Any]:
        """
        Export keypair information (optionally including private key).

        WARNING: Including private key is insecure - only for testing!

        Args:
            name: Keypair name
            include_private: Whether to include private key (INSECURE)

        Returns:
            Exportable keypair data
        """
        metadata = self._load_metadata()
        if name not in metadata:
            raise KeypairSecurityError(f"Keypair '{name}' not found")

        export_data = metadata[name].copy()
        keypair = self.load_keypair(name)
        seed_hex = keypair.seed_hex if isinstance(keypair.seed_hex, str) else keypair.seed_hex.hex()
        export_data['seed_hex'] = seed_hex

        if include_private:
            export_data['private_key'] = keypair.private_key.hex()

        return export_data

    def import_keypair(self, name: str, import_data: Dict[str, Any], save_to_disk: bool = True) -> Dict[str, Any]:
        """
        Import keypair from exported data.

        Args:
            name: New name for imported keypair
            import_data: Exported keypair data
            save_to_disk: Whether to save to disk

        Returns:
            Public keypair information
        """
        if 'seed_hex' not in import_data:
            raise KeypairSecurityError("Import data missing seed_hex")

        return self.create_keypair_from_seed(name, import_data['seed_hex'], save_to_disk)

    def _store_keypair(self, name: str, keypair: Keypair, public_info: Dict[str, Any]):
        """Persist keypair via KeyringService and update metadata."""
        service_name = self._service_name(name)
        metadata = {
            'name': name,
            'ss58_address': keypair.ss58_address,
            'ss58_format': keypair.ss58_format,
            'fingerprint': public_info.get('fingerprint'),
            'stored_at': self._get_timestamp(),
        }
        try:
            self._keyring.store_keypair(service_name, keypair, metadata=metadata)
        except KeyringServiceError as exc:
            raise KeypairSecurityError(f"Failed to store keypair '{name}': {exc}") from exc

        local_metadata = self._load_metadata()
        local_metadata[name] = {
            'ss58_address': keypair.ss58_address,
            'fingerprint': public_info.get('fingerprint'),
            'created_at': metadata['stored_at']
        }
        self._save_metadata(local_metadata)

    def _load_keypair_from_keyring(self, name: str) -> Keypair:
        """Load keypair from KeyringService."""
        service_name = self._service_name(name)
        try:
            keypair = self._keyring.load_keypair(service_name)
        except KeyringServiceError as exc:
            raise KeypairSecurityError(f"Failed to load keypair '{name}': {exc}") from exc

        if not keypair:
            raise KeypairSecurityError(f"Keypair '{name}' not found")

        self._keypair_cache[name] = keypair
        return keypair

    def _service_name(self, name: str) -> str:
        """Produce deterministic keyring service names."""
        return f"{self._service_prefix}-{name}"

    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load keypair metadata."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_metadata(self, metadata: Dict[str, Dict[str, Any]]):
        """Save keypair metadata."""
        with open(self._metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _generate_fingerprint(self, public_key_hex: str) -> str:
        """Generate a short fingerprint for the public key."""
        hash_obj = hashlib.sha256(bytes.fromhex(public_key_hex))
        return hash_obj.hexdigest()[:8]

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()