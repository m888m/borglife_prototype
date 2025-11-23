from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import keyring
from substrateinterface import Keypair


class KeyringServiceError(Exception):
    """Raised when keyring operations fail or produce inconsistent data."""


class KeyringService:
    """Centralized helper for storing and loading keypairs via macOS Keychain."""

    _PRIVATE_KEY_PATTERN = re.compile(r"^[0-9a-fA-F]{128}$")

    def __init__(self, ss58_format: int = 42, address_prefix: str = "5"):
        """
        Args:
            ss58_format: Network identifier (Westend defaults to 42).
            address_prefix: Expected prefix for addresses stored in the keyring.
        """
        self.ss58_format = ss58_format
        self.address_prefix = address_prefix

    def store_keypair(
        self,
        service_name: str,
        keypair: Keypair,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Persist keypair components atomically with optional metadata."""
        stored_keys = []
        try:
            for key_type, value in (
                ("private_key", keypair.private_key.hex()),
                ("public_key", keypair.public_key.hex()),
                ("address", keypair.ss58_address),
            ):
                keyring.set_password(service_name, key_type, value)
                stored_keys.append(key_type)

            if metadata:
                keyring.set_password(service_name, "metadata", json.dumps(metadata))
                stored_keys.append("metadata")

            return True
        except (
            Exception
        ) as exc:  # pragma: no cover - keyring failures not deterministic
            self._rollback(service_name, stored_keys)
            raise KeyringServiceError(
                f"Failed to store keypair for {service_name}: {exc}"
            ) from exc

    def load_keypair(self, service_name: str) -> Optional[Keypair]:
        """Reconstruct keypair from keyring, validating integrity."""
        private_key_hex = keyring.get_password(service_name, "private_key")
        public_key_hex = keyring.get_password(service_name, "public_key")
        address = keyring.get_password(service_name, "address")

        if not all([private_key_hex, public_key_hex, address]):
            return None

        try:
            keypair = self._safe_load_keypair(private_key_hex)
        except KeyringServiceError:
            raise
        except Exception as exc:
            raise KeyringServiceError(
                f"Failed to reconstruct keypair for {service_name}: {exc}"
            ) from exc

        if keypair.public_key.hex() != public_key_hex:
            raise KeyringServiceError(
                f"Public key mismatch for keyring service {service_name}"
            )

        if keypair.ss58_address != address:
            raise KeyringServiceError(
                f"Address mismatch for keyring service {service_name}"
            )

        if not address.startswith(self.address_prefix):
            raise KeyringServiceError(
                f"Unexpected address prefix for {service_name}: {address}"
            )

        return keypair

    def delete_keypair(self, service_name: str) -> None:
        """Remove all stored entries for a service."""
        for key_type in ("private_key", "public_key", "address", "metadata"):
            try:
                keyring.delete_password(service_name, key_type)
            except keyring.errors.PasswordDeleteError:
                # Already removed; nothing else to do
                continue

    def load_metadata(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Return stored metadata payload if present."""
        metadata_raw = keyring.get_password(service_name, "metadata")
        if not metadata_raw:
            return None

        try:
            return json.loads(metadata_raw)
        except json.JSONDecodeError:
            return None

    def _rollback(self, service_name: str, stored_keys: list[str]) -> None:
        for key_type in stored_keys:
            try:
                keyring.delete_password(service_name, key_type)
            except Exception:
                continue

    def _safe_load_keypair(self, private_key_hex: str) -> Keypair:
        if not private_key_hex or not self._PRIVATE_KEY_PATTERN.match(private_key_hex):
            raise KeyringServiceError("Invalid private key format")

        private_key = bytes.fromhex(private_key_hex)
        keypair = Keypair(private_key=private_key, ss58_format=self.ss58_format)

        if not keypair.public_key or not keypair.ss58_address:
            raise KeyringServiceError("Keypair reconstruction produced invalid state")

        return keypair
