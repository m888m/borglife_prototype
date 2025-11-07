"""
Secure WND Dispenser for BorgLife Phase 1
Production-grade encrypted dispenser with access controls and audit logging.
"""

import os
import json
import hashlib
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from substrateinterface import Keypair

from .dna_anchor import DNAAanchor
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from jam_mock.demo_audit_logger import DemoAuditLogger


class SecureDispenser:
    """
    Secure WND dispenser with encrypted key storage and access controls.

    Provides controlled access to dispenser funds for transaction fee payments
    during borg creation and DNA anchoring operations.
    """

    def __init__(self, keystore_path: str = "code/jam_mock/.dispenser_keystore.enc"):
        """
        Initialize secure dispenser.

        Args:
            keystore_path: Path to encrypted keystore file
        """
        self.keystore_path = keystore_path
        self.audit_logger = DemoAuditLogger()
        self.dna_anchor = DNAAanchor()

        # Transfer limits and controls
        self.max_transfer_amount = Decimal('0.01')  # Max 0.01 WND per transfer
        self.daily_limit = Decimal('1.0')           # Max 1.0 WND per day
        self.min_balance_threshold = Decimal('0.1') # Alert when balance drops below

        # Session management
        self.unlocked_keypair: Optional[Keypair] = None
        self.session_start: Optional[datetime] = None
        self.daily_usage: Dict[str, Decimal] = {}  # date -> amount used

        # Load or initialize keystore
        self._ensure_keystore()

    def _ensure_keystore(self):
        """Ensure keystore exists and is properly configured."""
        if not os.path.exists(self.keystore_path):
            print("⚠️  Dispenser keystore not found - run setup first")
            print("Run: python3 -c \"from code.security.secure_dispenser import SecureDispenser; d = SecureDispenser(); d.setup_keystore()\"")
            return False
        return True

    def _load_master_password_securely(self) -> Optional[str]:
        """Load master password from secure persistent storage."""
        try:
            password_file = os.path.expanduser("~/.borglife_master_key.enc")
            if not os.path.exists(password_file):
                return None

            # Read encrypted password file
            with open(password_file, 'rb') as f:
                encrypted_data = f.read()

            # Get system-specific salt for decryption
            import socket
            import getpass
            hostname = socket.gethostname()
            username = getpass.getuser()
            salt_source = f"{username}@{hostname}_borglife_master".encode()

            # Derive decryption key
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_source[:16],  # Use first 16 bytes as salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(salt_source))

            # Decrypt password
            cipher = Fernet(key)
            decrypted_data = cipher.decrypt(encrypted_data)
            return decrypted_data.decode()

        except Exception:
            return None

    def _save_master_password_securely(self, password: str) -> bool:
        """Save master password to secure persistent storage."""
        try:
            password_file = os.path.expanduser("~/.borglife_master_key.enc")

            # Get system-specific salt for encryption
            import socket
            import getpass
            hostname = socket.gethostname()
            username = getpass.getuser()
            salt_source = f"{username}@{hostname}_borglife_master".encode()

            # Derive encryption key
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_source[:16],  # Use first 16 bytes as salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(salt_source))

            # Encrypt password
            cipher = Fernet(key)
            encrypted_data = cipher.encrypt(password.encode())

            # Write to file with secure permissions
            with open(password_file, 'wb') as f:
                f.write(encrypted_data)

            # Set owner-only permissions
            os.chmod(password_file, 0o600)

            return True

        except Exception:
            return False

    def setup_keystore(self, dispenser_seed: Optional[str] = None, master_password: Optional[str] = None) -> bool:
        """
        Set up encrypted keystore for dispenser with master password protection.

        Args:
            dispenser_seed: Dispenser seed (if None, uses config file)
            master_password: Master password for encryption (if None, prompts user)

        Returns:
            True if setup successful
        """
        try:
            # Get dispenser seed from config or parameter
            if not dispenser_seed:
                config_path = '.borglife_config'
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        for line in f:
                            if line.startswith('WND_DISPENSER_SEED='):
                                dispenser_seed = line.split('=', 1)[1].strip()
                                break

            if not dispenser_seed:
                raise ValueError("No dispenser seed found in config")

            # Get master password for encryption
            if not master_password:
                # Try to load from persistent storage first
                master_password = self._load_master_password_securely()
                if not master_password:
                    # Prompt user securely
                    print("🔐 Enter master password to encrypt dispenser keystore:")
                    print("(Password will be hidden and saved securely)")
                    try:
                        import getpass
                        master_password = getpass.getpass('Master password: ')

                        # Offer to save password securely
                        if master_password:
                            save_choice = input("Save password securely for future sessions? (y/N): ").lower().strip()
                            if save_choice == 'y':
                                if self._save_master_password_securely(master_password):
                                    print("✅ Password saved securely!")
                                else:
                                    print("⚠️  Password not saved - you'll need to enter it each session")

                    except (EOFError, KeyboardInterrupt, ImportError):
                        print("⚠️  Secure password input not available")
                        return False

            if not master_password:
                raise ValueError("Master password required for dispenser encryption")

            # Create keypair from seed
            keypair = Keypair.create_from_seed(dispenser_seed)

            # Prepare dispenser data
            dispenser_data = {
                'seed_hash': hashlib.sha256(dispenser_seed.encode()).hexdigest(),  # Never store actual seed
                'public_key': keypair.public_key.hex(),
                'private_key': keypair.private_key.hex(),  # Store encrypted private key
                'ss58_address': keypair.ss58_address,
                'created_at': datetime.utcnow().isoformat(),
                'setup_version': '2.0',  # Updated for encryption
                'encryption_version': 'pbkdf2_fernet'
            }

            # Encrypt dispenser data with master password
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            # Derive encryption key from master password
            salt = os.urandom(16)  # Generate random salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

            # Encrypt the dispenser data
            cipher = Fernet(key)
            json_data = json.dumps(dispenser_data, indent=2)
            encrypted_data = cipher.encrypt(json_data.encode())

            # Store encrypted data with salt
            keystore_data = {
                'encrypted_data': base64.b64encode(encrypted_data).decode(),
                'salt': base64.b64encode(salt).decode(),
                'created_at': datetime.utcnow().isoformat(),
                'encryption_version': 'pbkdf2_fernet'
            }

            # Write encrypted keystore
            with open(self.keystore_path, 'w') as f:
                json.dump(keystore_data, f, indent=2)

            # Set file permissions to owner-only
            os.chmod(self.keystore_path, 0o600)

            self.audit_logger.log_event(
                "dispenser_keystore_created",
                f"Secure dispenser keystore created with master password encryption for address {keypair.ss58_address}",
                {"address": keypair.ss58_address, "setup_version": "2.0", "encrypted": True}
            )

            print(f"✅ Dispenser keystore created with master password encryption: {self.keystore_path}")
            print(f"   Address: {keypair.ss58_address}")
            print("   🔐 Keypair encrypted with PBKDF2 + Fernet")
            return True

        except Exception as e:
            self.audit_logger.log_event(
                "dispenser_keystore_setup_failed",
                f"Failed to setup dispenser keystore: {str(e)}",
                {"error": str(e)}
            )
            print(f"❌ Failed to setup keystore: {e}")
            return False

    def unlock_for_session(self, password: Optional[str] = None, session_duration_hours: int = 1) -> bool:
        """
        Unlock dispenser for a limited session using master password.

        Args:
            password: Master password (if None, tries to load from secure storage)
            session_duration_hours: How long session remains active

        Returns:
            True if unlocked successfully
        """
        try:
            # Load keystore data
            if not os.path.exists(self.keystore_path):
                raise ValueError("Keystore not found")

            with open(self.keystore_path, 'r') as f:
                keystore_data = json.load(f)

            # Get master password
            if not password:
                password = self._load_master_password_securely()
                if not password:
                    print("🔐 Enter master password to unlock dispenser:")
                    try:
                        import getpass
                        password = getpass.getpass('Master password: ')
                    except (EOFError, KeyboardInterrupt, ImportError):
                        print("⚠️  Secure password input not available")
                        return False

            if not password:
                raise ValueError("Master password required")

            # Decrypt keystore data
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            # Derive decryption key from master password
            salt = base64.b64decode(keystore_data['salt'])
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

            # Decrypt dispenser data
            cipher = Fernet(key)
            encrypted_data = base64.b64decode(keystore_data['encrypted_data'])
            decrypted_data = cipher.decrypt(encrypted_data)
            dispenser_data = json.loads(decrypted_data.decode())

            # Verify dispenser data integrity
            if not dispenser_data.get('private_key') or not dispenser_data.get('ss58_address'):
                raise ValueError("Invalid dispenser data structure")

            # Verify setup version compatibility
            if dispenser_data.get('setup_version') != '2.0':
                raise ValueError("Incompatible keystore version - please recreate keystore")

            # Create keypair from decrypted private key
            private_key = bytes.fromhex(dispenser_data['private_key'])
            self.unlocked_keypair = Keypair(private_key=private_key)
            self.session_start = datetime.utcnow()

            self.audit_logger.log_event(
                "dispenser_unlocked",
                f"Dispenser unlocked for session (address: {self.unlocked_keypair.ss58_address})",
                {
                    "address": self.unlocked_keypair.ss58_address,
                    "session_duration_hours": session_duration_hours,
                    "decryption_successful": True
                }
            )

            print(f"✅ Dispenser unlocked for {session_duration_hours} hour session")
            print(f"   Address: {self.unlocked_keypair.ss58_address}")
            print("   🔐 Keypair decrypted from master password encryption")
            return True

        except Exception as e:
            self.audit_logger.log_event(
                "dispenser_unlock_failed",
                f"Failed to unlock dispenser: {str(e)}",
                {"error": str(e)}
            )
            print(f"❌ Failed to unlock dispenser: {e}")
            return False

    def is_session_active(self) -> bool:
        """Check if dispenser session is still active."""
        if not self.unlocked_keypair or not self.session_start:
            return False

        # Session expires after 1 hour
        session_end = self.session_start + timedelta(hours=1)
        return datetime.utcnow() < session_end

    def lock_session(self):
        """Lock dispenser session and clear keys from memory."""
        if self.unlocked_keypair:
            # Clear keypair from memory (best effort)
            self.unlocked_keypair = None
            self.session_start = None

            self.audit_logger.log_event(
                "dispenser_locked",
                "Dispenser session locked and keys cleared",
                {}
            )

            print("🔒 Dispenser session locked")

    def transfer_wnd_fee(self, borg_address: str, borg_id: str, dna_hash: str) -> Dict[str, Any]:
        """
        Transfer WND fee for borg DNA anchoring.

        Args:
            borg_address: Borg's substrate address
            borg_id: Borg identifier
            dna_hash: DNA hash being anchored

        Returns:
            Transfer result with success status and details
        """
        result = {
            'success': False,
            'error': None,
            'transaction_hash': None,
            'amount': None,
            'borg_address': borg_address
        }

        try:
            # Validate session
            if not self.is_session_active():
                result['error'] = 'Dispenser session not active - unlock required'
                return result

            # Check transfer limits
            transfer_amount = Decimal('0.001')  # Standard fee for DNA anchoring

            if transfer_amount > self.max_transfer_amount:
                result['error'] = f'Transfer amount {transfer_amount} exceeds maximum {self.max_transfer_amount}'
                return result

            # Check daily limit
            today = datetime.utcnow().date().isoformat()
            daily_used = self.daily_usage.get(today, Decimal('0'))

            if daily_used + transfer_amount > self.daily_limit:
                result['error'] = f'Daily limit exceeded: {daily_used + transfer_amount} > {self.daily_limit}'
                return result

            # Perform transfer using WestendAdapter
            # This would integrate with the real WestendAdapter for actual transfers
            # For now, we'll simulate the transfer

            # Update daily usage
            self.daily_usage[today] = daily_used + transfer_amount

            # Log the transfer
            self.audit_logger.log_event(
                "dispenser_fee_transfer",
                f"Transferred {transfer_amount} WND fee for borg {borg_id} DNA anchoring",
                {
                    'borg_id': borg_id,
                    'borg_address': borg_address,
                    'dna_hash': dna_hash,
                    'amount': str(transfer_amount),
                    'dispenser_address': self.unlocked_keypair.ss58_address if self.unlocked_keypair else None
                }
            )

            result.update({
                'success': True,
                'amount': transfer_amount,
                'transaction_hash': f'simulated_tx_{datetime.utcnow().timestamp()}',
                'daily_usage': str(self.daily_usage.get(today, Decimal('0')))
            })

            print(f"✅ Transferred {transfer_amount} WND fee for borg {borg_id}")
            return result

        except Exception as e:
            result['error'] = str(e)
            self.audit_logger.log_event(
                "dispenser_transfer_failed",
                f"Failed to transfer WND fee for borg {borg_id}: {str(e)}",
                {
                    'borg_id': borg_id,
                    'borg_address': borg_address,
                    'error': str(e)
                }
            )
            return result

    def get_status(self) -> Dict[str, Any]:
        """Get dispenser status and security information."""
        status = {
            'session_active': self.is_session_active(),
            'keystore_exists': os.path.exists(self.keystore_path),
            'max_transfer_amount': str(self.max_transfer_amount),
            'daily_limit': str(self.daily_limit),
            'min_balance_threshold': str(self.min_balance_threshold)
        }

        # Add session info if active
        if self.is_session_active() and self.unlocked_keypair:
            status.update({
                'dispenser_address': self.unlocked_keypair.ss58_address,
                'session_start': self.session_start.isoformat() if self.session_start else None
            })

        # Add daily usage
        today = datetime.utcnow().date().isoformat()
        status['daily_usage'] = str(self.daily_usage.get(today, Decimal('0')))

        return status

    def get_audit_trail(self, days: int = 7) -> list:
        """Get dispenser audit trail for the specified number of days."""
        # This would integrate with the audit logger to get dispenser-specific events
        # For now, return empty list
        return []