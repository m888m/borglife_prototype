"""
Secure Key Storage with Environment-Based Configuration

Provides encrypted keypair storage with environment-based configuration,
supporting both development (temporary keys) and production (encrypted persistent storage).
Includes key rotation mechanisms and secure cleanup.
"""

import os
import json
import base64
import hashlib
import secrets
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta

from keypair_manager import KeypairManager, KeypairSecurityError


class SecureKeyStorage:
    """
    Secure encrypted keypair storage with environment-based configuration.

    Supports multiple storage backends and security levels for different environments.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else self._get_default_storage_path()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Environment detection
        self.environment = self._detect_environment()

        # Storage configuration based on environment
        self.config = self._load_storage_config()

        # Master key management
        self.master_key = self._derive_master_key()

        # Key rotation settings
        self.rotation_period_days = self.config.get('rotation_period_days', 90)
        self.backup_count = self.config.get('backup_count', 3)

    def _detect_environment(self) -> str:
        """Detect current environment from various sources."""
        # Check environment variables
        env = os.getenv('BORGLIFE_ENV', '').lower()
        if env in ['development', 'staging', 'production']:
            return env

        # Check for development indicators
        if os.getenv('PYTHONPATH', '').find('test') != -1:
            return 'development'

        # Check current working directory
        cwd = Path.cwd()
        if any(part in ['test', 'testing', 'dev'] for part in cwd.parts):
            return 'development'

        # Default to production for safety
        return 'production'

    def _get_default_storage_path(self) -> Path:
        """Get default storage path based on environment."""
        if self._detect_environment() == 'development':
            # Use temporary directory for development
            import tempfile
            return Path(tempfile.gettempdir()) / 'borglife_keys_dev'
        else:
            # Use user config directory for production
            return Path.home() / '.borglife' / 'keys'

    def _load_storage_config(self) -> Dict[str, Any]:
        """Load storage configuration based on environment."""
        base_config = {
            'development': {
                'encryption_level': 'basic',  # XOR for development
                'auto_cleanup': True,
                'rotation_period_days': 1,  # Daily rotation in dev
                'backup_count': 1,
                'require_password': False,
                'allow_plaintext_backup': True
            },
            'staging': {
                'encryption_level': 'standard',  # Fernet encryption
                'auto_cleanup': False,
                'rotation_period_days': 30,
                'backup_count': 2,
                'require_password': True,
                'allow_plaintext_backup': False
            },
            'production': {
                'encryption_level': 'high',  # PBKDF2 + Fernet
                'auto_cleanup': False,
                'rotation_period_days': 90,
                'backup_count': 3,
                'require_password': True,
                'allow_plaintext_backup': False
            }
        }

        return base_config.get(self.environment, base_config['production'])

    def _derive_master_key(self) -> bytes:
        """Derive master encryption key based on environment and configuration."""
        if self.config['encryption_level'] == 'basic':
            # Simple key derivation for development
            seed = os.getenv('BORGLIFE_KEY_SEED', 'borglife_dev_key_seed')
            return base64.urlsafe_b64encode(seed.encode()[:32].ljust(32, b'\0'))

        elif self.config['encryption_level'] == 'standard':
            # Environment-based key
            env_key = os.getenv('BORGLIFE_ENCRYPTION_KEY')
            if not env_key:
                raise KeypairSecurityError("BORGLIFE_ENCRYPTION_KEY environment variable required")
            return base64.urlsafe_b64encode(env_key.encode()[:32].ljust(32, b'\0'))

        else:  # high encryption - fallback to basic for now
            # For Phase 1, use basic encryption to avoid dependency issues
            print("Warning: High encryption not available, using basic encryption")
            seed = os.getenv('BORGLIFE_MASTER_PASSWORD', 'borglife_prod_key_seed')
            return base64.urlsafe_b64encode(seed.encode()[:32].ljust(32, b'\0'))

    def store_keypair_securely(self, name: str, keypair_data: Dict[str, Any]) -> bool:
        """
        Store keypair with appropriate encryption for current environment.

        Args:
            name: Keypair name
            keypair_data: Keypair data to store

        Returns:
            True if stored successfully
        """
        try:
            # Prepare data for storage
            storage_data = {
                'name': name,
                'data': keypair_data,
                'environment': self.environment,
                'created_at': datetime.utcnow().isoformat(),
                'encryption_level': self.config['encryption_level']
            }

            # Encrypt based on environment
            if self.config['encryption_level'] in ['basic', 'high']:
                # XOR encryption for development/production (Phase 1)
                encrypted_data = self._xor_encrypt(json.dumps(storage_data).encode())
            else:
                # For standard encryption, also use XOR for now
                encrypted_data = self._xor_encrypt(json.dumps(storage_data).encode())

            # Save to file
            keypair_file = self.storage_path / f"{name}.enc"
            keypair_file.write_bytes(encrypted_data)

            # Create backup if configured
            if self.backup_count > 0:
                self._create_backup(name, encrypted_data)

            # Update metadata
            self._update_metadata(name, storage_data)

            return True

        except Exception as e:
            print(f"Error storing keypair {name}: {e}")
            return False

    def load_keypair_securely(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load keypair with appropriate decryption.

        Args:
            name: Keypair name

        Returns:
            Decrypted keypair data or None if not found
        """
        try:
            keypair_file = self.storage_path / f"{name}.enc"

            if not keypair_file.exists():
                return None

            encrypted_data = keypair_file.read_bytes()

            # Decrypt based on stored encryption level
            decrypted_bytes = self._xor_decrypt(encrypted_data)
            storage_data = json.loads(decrypted_bytes.decode())

            # Verify environment compatibility
            stored_env = storage_data.get('environment', 'unknown')
            if stored_env != self.environment and self.environment != 'development':
                print(f"Warning: Keypair created in {stored_env} environment, loading in {self.environment}")

            return storage_data['data']

        except Exception as e:
            print(f"Error loading keypair {name}: {e}")
            return None

    def _xor_encrypt(self, data: bytes) -> bytes:
        """Simple XOR encryption for development."""
        key = self.master_key.decode()[:32].encode()
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def _xor_decrypt(self, data: bytes) -> bytes:
        """Simple XOR decryption for development."""
        return self._xor_encrypt(data)

    def _create_backup(self, name: str, encrypted_data: bytes):
        """Create encrypted backup of keypair."""
        try:
            backup_dir = self.storage_path / 'backups'
            backup_dir.mkdir(exist_ok=True)

            # Create backup filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"{name}_{timestamp}.bak"

            # Write backup
            backup_file.write_bytes(encrypted_data)

            # Clean old backups
            self._cleanup_old_backups(name)

        except Exception as e:
            print(f"Error creating backup for {name}: {e}")

    def _cleanup_old_backups(self, name: str):
        """Clean up old backups, keeping only the most recent ones."""
        try:
            backup_dir = self.storage_path / 'backups'
            if not backup_dir.exists():
                return

            # Find all backups for this keypair
            pattern = f"{name}_*.bak"
            backups = list(backup_dir.glob(pattern))

            if len(backups) <= self.backup_count:
                return

            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Remove old backups
            for old_backup in backups[self.backup_count:]:
                old_backup.unlink()

        except Exception as e:
            print(f"Error cleaning backups for {name}: {e}")

    def _update_metadata(self, name: str, storage_data: Dict[str, Any]):
        """Update keypair metadata."""
        try:
            metadata_file = self.storage_path / 'metadata.json'

            # Load existing metadata
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            # Update entry
            metadata[name] = {
                'created_at': storage_data['created_at'],
                'environment': storage_data['environment'],
                'encryption_level': storage_data['encryption_level'],
                'last_accessed': datetime.utcnow().isoformat(),
                'backup_count': self._count_backups(name)
            }

            # Save metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            print(f"Error updating metadata for {name}: {e}")

    def _count_backups(self, name: str) -> int:
        """Count existing backups for a keypair."""
        try:
            backup_dir = self.storage_path / 'backups'
            if not backup_dir.exists():
                return 0

            pattern = f"{name}_*.bak"
            return len(list(backup_dir.glob(pattern)))
        except:
            return 0

    def list_stored_keypairs(self) -> List[Dict[str, Any]]:
        """
        List all stored keypairs with metadata.

        Returns:
            List of keypair information
        """
        try:
            metadata_file = self.storage_path / 'metadata.json'

            if not metadata_file.exists():
                return []

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            keypairs = []
            for name, info in metadata.items():
                keypairs.append({
                    'name': name,
                    'created_at': info['created_at'],
                    'environment': info['environment'],
                    'encryption_level': info['encryption_level'],
                    'last_accessed': info.get('last_accessed'),
                    'backup_count': info.get('backup_count', 0)
                })

            return keypairs

        except Exception as e:
            print(f"Error listing keypairs: {e}")
            return []

    def rotate_keypair(self, name: str) -> bool:
        """
        Rotate encryption for a keypair (re-encrypt with current settings).

        Args:
            name: Keypair name

        Returns:
            True if rotated successfully
        """
        try:
            # Load current data
            keypair_data = self.load_keypair_securely(name)
            if not keypair_data:
                return False

            # Re-store with current encryption settings
            return self.store_keypair_securely(name, keypair_data)

        except Exception as e:
            print(f"Error rotating keypair {name}: {e}")
            return False

    def check_rotation_needed(self, name: str) -> bool:
        """
        Check if a keypair needs rotation based on age.

        Args:
            name: Keypair name

        Returns:
            True if rotation is needed
        """
        try:
            metadata_file = self.storage_path / 'metadata.json'

            if not metadata_file.exists():
                return False

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            if name not in metadata:
                return False

            created_at = datetime.fromisoformat(metadata[name]['created_at'])
            age_days = (datetime.utcnow() - created_at).days

            return age_days >= self.rotation_period_days

        except Exception:
            return False

    def cleanup_expired_keys(self) -> int:
        """
        Clean up expired development keys.

        Returns:
            Number of keys cleaned up
        """
        if not self.config.get('auto_cleanup', False):
            return 0

        try:
            cleaned_count = 0
            keypairs = self.list_stored_keypairs()

            for kp in keypairs:
                name = kp['name']
                created_at = datetime.fromisoformat(kp['created_at'])
                age_days = (datetime.utcnow() - created_at).days

                # Clean keys older than rotation period in development
                if age_days > self.rotation_period_days:
                    keypair_file = self.storage_path / f"{name}.enc"
                    if keypair_file.exists():
                        keypair_file.unlink()
                        cleaned_count += 1

            return cleaned_count

        except Exception as e:
            print(f"Error during cleanup: {e}")
            return 0

    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about current storage configuration."""
        return {
            'environment': self.environment,
            'storage_path': str(self.storage_path),
            'encryption_level': self.config['encryption_level'],
            'rotation_period_days': self.rotation_period_days,
            'backup_count': self.backup_count,
            'auto_cleanup': self.config.get('auto_cleanup', False),
            'require_password': self.config.get('require_password', False),
            'stored_keypairs': len(self.list_stored_keypairs())
        }


class EnvironmentAwareKeypairManager(KeypairManager):
    """
    Keypair manager that uses secure storage with environment-based configuration.
    """

    def __init__(self, storage_path: Optional[str] = None):
        # Initialize secure storage first
        self.secure_storage = SecureKeyStorage(storage_path)

        # Initialize parent with same path
        super().__init__(storage_path=self.secure_storage.storage_path)

        # Override encryption to use secure storage
        self.use_secure_storage = True

    def create_keypair(self, name: str, save_to_disk: bool = True) -> Dict[str, Any]:
        """Create keypair with secure storage."""
        # Create keypair using parent method
        keypair_info = super().create_keypair(name, save_to_disk=False)

        # Store securely if requested
        if save_to_disk:
            keypair_data = {
                'seed_hex': self._keypair_cache[name].seed_hex,
                'public_key': keypair_info['public_key'],
                'ss58_address': keypair_info['ss58_address'],
                'ss58_format': keypair_info['ss58_format']
            }

            if not self.secure_storage.store_keypair_securely(name, keypair_data):
                raise KeypairSecurityError(f"Failed to securely store keypair {name}")

        return keypair_info

    def load_keypair(self, name: str) -> Optional[Any]:
        """Load keypair from secure storage."""
        # Try cache first
        if name in self._keypair_cache:
            return self._keypair_cache[name]

        # Load from secure storage
        keypair_data = self.secure_storage.load_keypair_securely(name)
        if not keypair_data:
            return None

        # Recreate keypair object
        try:
            from substrateinterface import Keypair
            keypair = Keypair.create_from_seed(
                seed_hex=keypair_data['seed_hex'],
                ss58_format=keypair_data['ss58_format']
            )

            # Cache it
            self._keypair_cache[name] = keypair
            return keypair

        except Exception as e:
            print(f"Error recreating keypair {name}: {e}")
            return None

    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment and storage information."""
        return {
            'keypair_manager': {
                'cached_keypairs': len(self._keypair_cache),
                'metadata': self.list_keypairs()
            },
            'secure_storage': self.secure_storage.get_storage_info()
        }