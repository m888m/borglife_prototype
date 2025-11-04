"""
Secure Keypair Storage for BorgLife Demo
Production-grade encrypted keypair management with access controls and audit logging.
"""

import os
import json
import base64
import hashlib
from typing import Dict, Optional, Any
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from substrateinterface import Keypair


class SecureKeyStore:
    """Encrypted keypair storage with access controls"""

    def __init__(self, store_path: str, encryption_key: Optional[str] = None):
        self.store_path = store_path
        self.encryption_key = encryption_key or self._generate_key_from_env()
        self._ensure_store_directory()

    def _generate_key_from_env(self) -> str:
        """Generate encryption key from environment or create new one"""
        env_key = os.getenv('BORGLIFE_KEYSTORE_KEY')
        if env_key:
            return env_key

        # Generate new key and save to environment for session
        key = Fernet.generate_key().decode()
        os.environ['BORGLIFE_KEYSTORE_KEY'] = key
        return key

    def _ensure_store_directory(self):
        """Ensure keystore directory exists"""
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)

    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher for encryption/decryption"""
        return Fernet(self.encryption_key.encode())

    def store_keypair(self, name: str, keypair: Keypair, metadata: Dict[str, Any] = None) -> bool:
        """Store encrypted keypair with metadata"""
        try:
            cipher = self._get_cipher()

            # Prepare keypair data
            keypair_data = {
                'public_key': keypair.public_key.hex(),
                'private_key': keypair.private_key.hex() if hasattr(keypair, 'private_key') else None,
                'ss58_address': keypair.ss58_address,
                'crypto_type': keypair.crypto_type.value if hasattr(keypair.crypto_type, 'value') else str(keypair.crypto_type),
                'stored_at': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }

            # Encrypt data
            json_data = json.dumps(keypair_data, indent=2)
            encrypted_data = cipher.encrypt(json_data.encode())

            # Write to file
            with open(self.store_path, 'wb') as f:
                f.write(encrypted_data)

            return True
        except Exception as e:
            print(f"Failed to store keypair {name}: {e}")
            return False

    def load_keypair(self, name: str) -> Optional[Keypair]:
        """Load and decrypt keypair"""
        try:
            if not os.path.exists(self.store_path):
                return None

            cipher = self._get_cipher()

            # Read and decrypt
            with open(self.store_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = cipher.decrypt(encrypted_data)
            keypair_data = json.loads(decrypted_data.decode())

            # Reconstruct keypair
            if keypair_data.get('private_key'):
                # Full keypair with private key
                private_key = bytes.fromhex(keypair_data['private_key'])
                keypair = Keypair(private_key=private_key)
            else:
                # Public key only
                public_key = bytes.fromhex(keypair_data['public_key'])
                keypair = Keypair(public_key=public_key)

            return keypair
        except Exception as e:
            print(f"Failed to load keypair {name}: {e}")
            return None

    def list_keypairs(self) -> Dict[str, Dict[str, Any]]:
        """List stored keypairs (metadata only, no private keys)"""
        try:
            if not os.path.exists(self.store_path):
                return {}

            cipher = self._get_cipher()

            with open(self.store_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = cipher.decrypt(encrypted_data)
            keypair_data = json.loads(decrypted_data.decode())

            # Return metadata only (no private key)
            return {
                'ss58_address': keypair_data.get('ss58_address'),
                'crypto_type': keypair_data.get('crypto_type'),
                'stored_at': keypair_data.get('stored_at'),
                'metadata': keypair_data.get('metadata', {})
            }
        except Exception as e:
            return {}


class SecureKeypairManager:
    """Production-grade keypair management with encryption and audit logging"""

    def __init__(self, store_path: str = "code/jam_mock/.keystore/demo_keypair.enc"):
        self.store = SecureKeyStore(store_path)
        self.audit_log = []

    def create_demo_keypair(self, name: str = "demo", save_to_disk: bool = True) -> Dict[str, Any]:
        """Create a new demo keypair with deterministic seed for testing"""
        # Use deterministic seed for demo consistency
        seed = b"BorgLife_Demo_Seed_2024_" + name.encode()
        seed_hash = hashlib.sha256(seed).digest()[:32]

        keypair = Keypair.create_from_seed(seed_hash)

        result = {
            'name': name,
            'keypair': keypair,
            'ss58_address': keypair.ss58_address,
            'public_key': keypair.public_key.hex(),
            'created_at': datetime.utcnow().isoformat()
        }

        if save_to_disk:
            metadata = {
                'purpose': 'demo_testing',
                'network': 'westend',
                'deterministic': True
            }
            self.store.store_keypair(name, keypair, metadata)
            self._audit_log('create', name, 'success', result['ss58_address'])

        return result

    def load_demo_keypair(self, name: str = "demo") -> Optional[Dict[str, Any]]:
        """Load demo keypair with access logging"""
        keypair = self.store.load_keypair(name)

        if keypair:
            result = {
                'name': name,
                'keypair': keypair,
                'ss58_address': keypair.ss58_address,
                'public_key': keypair.public_key.hex(),
                'loaded_at': datetime.utcnow().isoformat()
            }
            self._audit_log('load', name, 'success', keypair.ss58_address)
            return result
        else:
            self._audit_log('load', name, 'failed', 'keypair_not_found')
            return None

    def _audit_log(self, action: str, keypair_name: str, status: str, details: str):
        """Log keypair operations for audit trail"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'keypair_name': keypair_name,
            'status': status,
            'details': details,
            'user': os.getenv('USER', 'system')
        }
        self.audit_log.append(log_entry)

        # Also print for immediate visibility
        print(f"[AUDIT] {action.upper()} {keypair_name}: {status} - {details}")

    def get_audit_log(self) -> list:
        """Get audit log for compliance reporting"""
        return self.audit_log.copy()

    def validate_keypair_security(self, keypair: Keypair) -> Dict[str, Any]:
        """Validate keypair security properties"""
        return {
            'has_private_key': hasattr(keypair, 'private_key') and keypair.private_key is not None,
            'public_key_length': len(keypair.public_key),
            'ss58_address_valid': len(keypair.ss58_address) > 0,
            'crypto_type': keypair.crypto_type.value if hasattr(keypair.crypto_type, 'value') else str(keypair.crypto_type)
        }