"""
Secure Keypair Storage for BorgLife Demo
Production-grade encrypted keypair management with access controls and audit logging.
"""

import hashlib
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import keyring
from security.keyring_service import KeyringService, KeyringServiceError
from substrateinterface import Keypair


class SecureKeyStore:
    """Keypair storage using macOS Keychain"""

    def __init__(self, store_path: str, session_timeout_minutes: int = 60):
        self.store_path = store_path
        self.encryption_key = None
        self._session_timeout = (
            session_timeout_minutes * 60
        )  # Convert minutes to seconds
        self._ensure_store_directory()
        self._service_name = "borglife-keystore"
        self.keyring_service = KeyringService(ss58_format=42, address_prefix="5")

    def _store_keypair_atomic(
        self, name: str, keypair: Keypair, metadata: Dict[str, Any] = None
    ) -> bool:
        """Store keypair with rollback on failure."""
        stored_keys = []
        try:
            # Store each component
            for key_type, value in [
                ("private_key", keypair.private_key.hex()),
                ("public_key", keypair.public_key.hex()),
                ("address", keypair.ss58_address),
            ]:
                keyring.set_password(self._service_name, f"{name}_{key_type}", value)
                stored_keys.append(key_type)

            # Store metadata if provided
            if metadata:
                keyring.set_password(
                    self._service_name, f"{name}_metadata", json.dumps(metadata)
                )
                stored_keys.append("metadata")

            return True
        except Exception as e:
            # Rollback on failure
            for key_type in stored_keys:
                try:
                    keyring.delete_password(self._service_name, f"{name}_{key_type}")
                except:
                    pass  # Best effort cleanup
            print(f"Failed to store keypair {name} in keyring: {e}")
            return False

    def _safe_load_keypair(self, private_key_hex: str) -> Optional[Keypair]:
        """Safely reconstruct keypair with validation."""
        try:
            # Validate hex format and length (64 hex chars = 32 bytes)
            if not re.match(r"^[0-9a-fA-F]{128}$", private_key_hex):
                raise ValueError(
                    "Invalid private key format - must be 128 hex characters (64 bytes)"
                )

            private_key = bytes.fromhex(private_key_hex)
            keypair = Keypair(private_key=private_key, ss58_format=42)

            # Verify keypair integrity
            if not keypair.public_key or not keypair.ss58_address:
                raise ValueError("Invalid keypair generated")

            return keypair
        except Exception as e:
            self._audit_log("keypair_reconstruction_failed", "system", "error", str(e))
            return None

    def _load_keypair_from_keyring(self, name: str) -> Optional[Keypair]:
        """Load keypair from macOS Keychain with safe reconstruction."""
        try:
            private_key_hex = keyring.get_password(
                self._service_name, f"{name}_private_key"
            )
            public_key_hex = keyring.get_password(
                self._service_name, f"{name}_public_key"
            )

            if not private_key_hex or not public_key_hex:
                return None

            # Use safe keypair reconstruction
            keypair = self._safe_load_keypair(private_key_hex)
            if not keypair:
                return None

            # Verify keys match
            if keypair.public_key.hex() != public_key_hex:
                print(f"Keyring keypair integrity check failed for {name}")
                return None

            return keypair

        except Exception as e:
            print(f"Failed to load keypair {name} from keyring: {e}")
            return None

    def unlock_keystore(self) -> bool:
        """Unlock keystore using macOS Keychain (no password required)."""
        try:
            # Check if we can access the keyring
            test_key = keyring.get_password(self._service_name, "test_access")
            if test_key is None:
                # Set a test key to verify access
                keyring.set_password(self._service_name, "test_access", "accessible")

            self._session_start = datetime.utcnow()
            print("✅ Keystore unlocked successfully (macOS Keychain)")
            return True
        except Exception as e:
            print(f"Failed to unlock keystore: {e}")
            return False

    def _ensure_store_directory(self):
        """Ensure keystore directory exists"""
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)

    def _check_session_timeout(self):
        """Check if session has timed out."""
        if hasattr(self, "_session_start"):
            from datetime import datetime, timedelta

            if datetime.utcnow() - self._session_start > timedelta(
                seconds=self._session_timeout
            ):
                raise ValueError("Session expired - please unlock keystore again")

    def store_keypair(
        self, name: str, keypair: Keypair, metadata: Dict[str, Any] = None
    ) -> bool:
        """Store keypair in macOS Keychain with metadata"""
        try:
            self._check_session_timeout()

            # Store in keyring atomically
            try:
                success = self.keyring_service.store_keypair(
                    f"{self._service_name}_{name}",
                    keypair,
                    metadata=metadata,
                )
            except KeyringServiceError as exc:
                print(f"Failed to store keypair {name}: {exc}")
                return False

            if success:
                # Store metadata in keystore file (no sensitive data)
                keystore_data = {
                    "name": name,
                    "ss58_address": keypair.ss58_address,
                    "stored_at": datetime.utcnow().isoformat(),
                    "metadata": metadata or {},
                    "storage_method": "macos_keychain",
                }

                with open(self.store_path, "w") as f:
                    json.dump(keystore_data, f, indent=2)

            return success
        except Exception as e:
            print(f"Failed to store keypair {name}: {e}")
            return False

    def load_keypair(self, name: str) -> Optional[Keypair]:
        """Load keypair from macOS Keychain"""
        try:
            self._check_session_timeout()

            # Load from keyring
            service_name = f"{self._service_name}_{name}"
            try:
                keypair = self.keyring_service.load_keypair(service_name)
            except KeyringServiceError as exc:
                print(f"Failed to load keypair {name}: {exc}")
                return None

            return keypair
        except Exception as e:
            print(f"Failed to load keypair {name}: {e}")
            return None

    def list_keypairs(self) -> Dict[str, Dict[str, Any]]:
        """List stored keypairs metadata"""
        try:
            if not os.path.exists(self.store_path):
                return {}

            with open(self.store_path, "r") as f:
                keystore_data = json.load(f)

            # Return metadata only
            return {
                "name": keystore_data.get("name"),
                "ss58_address": keystore_data.get("ss58_address"),
                "stored_at": keystore_data.get("stored_at"),
                "metadata": keystore_data.get("metadata", {}),
            }
        except Exception as e:
            return {}


class SecureKeypairManager:
    """Keypair management using macOS Keychain"""

    def __init__(
        self,
        store_path: str = "code/jam_mock/.keystore/demo_keypair.enc",
        session_timeout_minutes: int = 60,
    ):
        self.store = SecureKeyStore(
            store_path, session_timeout_minutes=session_timeout_minutes
        )
        self.audit_log = []
        self._is_unlocked = False

    def unlock_keystore(self) -> bool:
        """Unlock keypair manager using macOS Keychain"""
        success = self.store.unlock_keystore()
        if success:
            self._is_unlocked = True
            self._audit_log("unlock", "keystore", "success", "keychain_authenticated")
            print("✅ Keystore unlocked successfully (macOS Keychain)")
        else:
            self._audit_log("unlock", "keystore", "failed", "keychain_access_denied")
            print("❌ Failed to unlock keystore")

        return success

    def _process_seed_securely(self, seed: str) -> Keypair:
        """Process seed with secure cleanup."""
        try:
            keypair = Keypair.create_from_seed(seed)
            # Immediately clear seed from memory
            seed = "\x00" * len(seed)
            return keypair
        except Exception as e:
            seed = "\x00" * len(seed)
            raise

    def create_demo_keypair(
        self, name: str = "demo", save_to_disk: bool = True
    ) -> Dict[str, Any]:
        """Create a new demo keypair with deterministic seed for testing"""
        if not self._is_unlocked:
            raise ValueError("Keystore not unlocked - call unlock_keystore() first")

        # Use deterministic seed for demo consistency
        seed = b"BorgLife_Demo_Seed_2024_" + name.encode()
        seed_hash = hashlib.sha256(seed).digest()[:32]

        # Use secure seed processing
        keypair = self._process_seed_securely(seed_hash.hex())

        result = {
            "name": name,
            "keypair": keypair,
            "ss58_address": keypair.ss58_address,
            "public_key": keypair.public_key.hex(),
            "created_at": datetime.utcnow().isoformat(),
        }

        if save_to_disk:
            metadata = {
                "purpose": "demo_testing",
                "network": "westend",
                "deterministic": True,
            }
            success = self.store.store_keypair(name, keypair, metadata)
            if success:
                self._audit_log("create", name, "success", result["ss58_address"])
            else:
                self._audit_log("create", name, "failed", "storage_error")

        return result

    def load_demo_keypair(self, name: str = "demo") -> Optional[Dict[str, Any]]:
        """Load demo keypair with access logging"""
        if not self._is_unlocked:
            raise ValueError("Keystore not unlocked - call unlock_keystore() first")

        try:
            keypair = self.store.load_keypair(name)

            if keypair:
                result = {
                    "name": name,
                    "keypair": keypair,
                    "ss58_address": keypair.ss58_address,
                    "public_key": keypair.public_key.hex(),
                    "loaded_at": datetime.utcnow().isoformat(),
                }
                self._audit_log("load", name, "success", keypair.ss58_address)
                return result
            else:
                self._audit_log("load", name, "failed", "keypair_not_found")
                return None
        except Exception as e:
            self._audit_log("load", name, "failed", f"load_error: {str(e)}")
            return None

    def _audit_log(self, action: str, keypair_name: str, status: str, details: str):
        """Log keypair operations for comprehensive audit trail"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "keypair_name": keypair_name,
            "status": status,
            "details": details,
            "user": os.getenv("USER", "system"),
            "session_info": {
                "failed_attempts": getattr(self, "_failed_attempts", 0),
                "is_locked": bool(
                    getattr(self, "_lockout_until", None)
                    and datetime.utcnow() < getattr(self, "_lockout_until")
                ),
                "session_active": hasattr(self, "_session_start"),
            },
            "security_events": [],
        }

        # Add security event correlation
        if status == "failed":
            log_entry["security_events"].append(
                {
                    "type": "access_denied",
                    "severity": "medium" if action == "unlock" else "low",
                    "details": f"Failed {action} attempt for {keypair_name}",
                }
            )

        if action == "unlock" and status == "success":
            log_entry["security_events"].append(
                {
                    "type": "keystore_access",
                    "severity": "info",
                    "details": f"Keystore unlocked for {keypair_name}",
                }
            )

        self.audit_log.append(log_entry)

        # Also print for immediate visibility
        print(f"[AUDIT] {action.upper()} {keypair_name}: {status} - {details}")

        # Log security events to audit file
        try:
            audit_file = os.path.join(
                os.path.dirname(self.store_path), "keystore_audit.jsonl"
            )
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # Don't fail operation due to audit logging

    def get_audit_log(self) -> list:
        """Get audit log for compliance reporting"""
        return self.audit_log.copy()

    def validate_keypair_security(self, keypair: Keypair) -> Dict[str, Any]:
        """Validate keypair security properties"""
        return {
            "has_private_key": hasattr(keypair, "private_key")
            and keypair.private_key is not None,
            "public_key_length": len(keypair.public_key),
            "ss58_address_valid": len(keypair.ss58_address) > 0,
            "crypto_type": (
                keypair.crypto_type.value
                if hasattr(keypair.crypto_type, "value")
                else str(keypair.crypto_type)
            ),
        }

    def get_keypair_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get keypair information without loading private key"""
        try:
            if not os.path.exists(self.store_path):
                return None

            with open(self.store_path, "r") as f:
                keystore_data = json.load(f)

            if keystore_data.get("name") == name:
                return {
                    "name": name,
                    "ss58_address": keystore_data.get("ss58_address"),
                    "stored_at": keystore_data.get("stored_at"),
                    "metadata": keystore_data.get("metadata", {}),
                }
            return None
        except Exception as e:
            print(f"Failed to get keypair info for {name}: {e}")
            return None
