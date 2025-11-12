"""
Secure WND Dispenser - Address Primary Compatible Version
Updated to work with address-based borg identification system.

This version maintains dispenser functionality while being compatible with
the new address-primary borg management system.
"""

import os
import json
import hashlib
import re
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from substrateinterface import Keypair
import keyring

from .dna_anchor import DNAAanchor
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from jam_mock.demo_audit_logger import DemoAuditLogger

# Load Supabase credentials for dispenser
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.borglife'))
    import os
    from supabase import create_client

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SECRET_KEY')

    if supabase_url and supabase_key:
        dispenser_supabase_client = create_client(supabase_url, supabase_key)
    else:
        dispenser_supabase_client = None
        print("⚠️  Dispenser: Supabase credentials not found in .env.borglife")
except ImportError:
    dispenser_supabase_client = None
    print("⚠️  Dispenser: python-dotenv not available, Supabase integration disabled")
except Exception as e:
    dispenser_supabase_client = None
    print(f"⚠️  Dispenser: Failed to initialize Supabase client: {e}")


class SecureDispenserAddressPrimary:
    """
    Secure WND dispenser compatible with address-based borg identification.

    Maintains dispenser functionality while working with the new address-primary
    borg management system for enhanced blockchain alignment.
    """

    def __init__(self, keystore_path: str = "code/jam_mock/.dispenser_keystore.enc"):
        """
        Initialize address-primary compatible dispenser.

        Args:
            keystore_path: Path to encrypted keystore file
        """
        self.keystore_path = keystore_path
        self.audit_logger = DemoAuditLogger()
        self.dna_anchor = DNAAanchor()

        # Transfer limits and controls
        self.max_transfer_amount = Decimal('3.0')   # Max 3.0 WND per transfer
        self.daily_limit = Decimal('9.0')           # Max 9.0 WND per day
        self.min_balance_threshold = Decimal('0.1') # Alert when balance drops below

        # Session management
        self.unlocked_keypair: Optional[Keypair] = None
        self.session_start: Optional[datetime] = None
        self.daily_usage: Dict[str, Decimal] = {}  # date -> amount used

        # Address cache for borg lookups (to avoid repeated DB queries)
        self._borg_address_cache: Dict[str, str] = {}  # borg_id -> address

        # Load or initialize keystore
        self._ensure_keystore()

    def _ensure_keystore(self):
        """Ensure keystore exists and is properly configured."""
        if not os.path.exists(self.keystore_path):
            print("⚠️  Dispenser keystore not found - run setup first")
            print("Run: python3 -c \"from code.security.secure_dispenser_address_primary import SecureDispenserAddressPrimary; d = SecureDispenserAddressPrimary(); d.setup_keystore()\"")
            return False
        return True

    def _get_keyring_service_name(self) -> str:
        """Get the keyring service name for dispenser keys."""
        # Dispenser uses its own service name (not address-based since it's not a borg)
        return "borglife-dispenser"

    def _store_keypair_atomic(self, keypair: Keypair, service_name: str) -> bool:
        """Store keypair with rollback on failure."""
        stored_keys = []
        try:
            # Store each component
            for key_type, value in [
                ('private_key', keypair.private_key.hex()),
                ('public_key', keypair.public_key.hex()),
                ('address', keypair.ss58_address)
            ]:
                keyring.set_password(service_name, key_type, value)
                stored_keys.append(key_type)

            return True
        except Exception as e:
            # Rollback on failure
            for key_type in stored_keys:
                try:
                    keyring.delete_password(service_name, key_type)
                except:
                    pass  # Best effort cleanup
            print(f"Failed to store keypair in keyring: {e}")
            return False

    def _safe_load_keypair(self, private_key_hex: str) -> Optional[Keypair]:
        """Safely reconstruct keypair with validation."""
        try:
            # Validate hex format and length (64 hex chars = 32 bytes)
            if not re.match(r'^[0-9a-fA-F]{128}$', private_key_hex):
                raise ValueError("Invalid private key format - must be 128 hex characters (64 bytes)")

            private_key = bytes.fromhex(private_key_hex)
            keypair = Keypair(private_key=private_key, ss58_format=42)

            # Verify keypair integrity
            if not keypair.public_key or not keypair.ss58_address:
                raise ValueError("Invalid keypair generated")

            return keypair
        except Exception as e:
            self.audit_logger.log_event(
                "keypair_reconstruction_failed",
                f"Failed to reconstruct dispenser keypair: {str(e)}",
                {"error": str(e)}
            )
            return None

    def _load_keypair_from_keyring(self, service_name: str) -> Optional[Keypair]:
        """Load keypair from macOS Keychain with safe reconstruction."""
        try:
            private_key_hex = keyring.get_password(service_name, "private_key")
            public_key_hex = keyring.get_password(service_name, "public_key")

            if not private_key_hex or not public_key_hex:
                return None

            # Use safe keypair reconstruction
            keypair = self._safe_load_keypair(private_key_hex)
            if not keypair:
                return None

            # Verify keys match
            if keypair.public_key.hex() != public_key_hex:
                print("Keyring keypair integrity check failed")
                return None

            return keypair

        except Exception as e:
            print(f"Failed to load keypair from keyring: {e}")
            return None

    def _resolve_borg_address(self, borg_identifier: str) -> Optional[str]:
        """
        Resolve borg address from identifier (works with both borg_id and address).

        This method provides compatibility with both old borg_id and new address-based systems.

        Args:
            borg_identifier: Either a borg_id (string) or substrate address

        Returns:
            Substrate address or None if not found
        """
        # Check if it's already an address (SS58 format)
        if borg_identifier.startswith('5') and len(borg_identifier) == 48:
            return borg_identifier

        # Check cache first
        if borg_identifier in self._borg_address_cache:
            return self._borg_address_cache[borg_identifier]

        # Try to resolve via database (address-primary system)
        try:
            # Import here to avoid circular imports
            from jam_mock.borg_address_manager_address_primary import BorgAddressManagerAddressPrimary

            # Try to get a manager instance (this is a simplified approach)
            # In production, this would be injected as a dependency
            manager = BorgAddressManagerAddressPrimary()

            address = manager.get_borg_address(borg_identifier)
            if address:
                self._borg_address_cache[borg_identifier] = address
                return address

        except Exception as e:
            self.audit_logger.log_event(
                "borg_address_resolution_failed",
                f"Failed to resolve address for {borg_identifier}: {str(e)}",
                {"borg_identifier": borg_identifier, "error": str(e)}
            )

        return None

    def setup_keystore(self, dispenser_seed: Optional[str] = None) -> bool:
        """
        Set up dispenser keypair stored securely in macOS Keychain.

        Args:
            dispenser_seed: Dispenser seed (if None, uses config file)

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

            # Create keypair from seed with secure cleanup
            keypair = self._process_seed_securely(dispenser_seed)

            # Store keypair in macOS Keychain atomically
            service_name = self._get_keyring_service_name()
            if not self._store_keypair_atomic(keypair, service_name):
                raise ValueError("Failed to store keypair in macOS Keychain")

            # Store metadata in keystore file (no sensitive data)
            keystore_data = {
                'seed_hash': hashlib.sha256(dispenser_seed.encode()).hexdigest(),  # Never store actual seed
                'ss58_address': keypair.ss58_address,
                'created_at': datetime.utcnow().isoformat(),
                'setup_version': '4.0',  # Updated for address-primary compatibility
                'storage_method': 'macos_keychain_address_primary_compatible'
            }

            # Write keystore metadata
            with open(self.keystore_path, 'w') as f:
                json.dump(keystore_data, f, indent=2)

            # Set file permissions to owner-only
            os.chmod(self.keystore_path, 0o600)

            self.audit_logger.log_event(
                "dispenser_keystore_created_address_primary",
                f"Secure dispenser keystore created with address-primary compatibility for address {keypair.ss58_address}",
                {"address": keypair.ss58_address, "setup_version": "4.0", "storage": "macos_keychain"}
            )

            print(f"✅ Dispenser keystore created with address-primary compatibility: {self.keystore_path}")
            print(f"   Address: {keypair.ss58_address}")
            print("   🔐 Keypair stored securely in macOS Keychain")
            return True

        except Exception as e:
            self.audit_logger.log_event(
                "dispenser_keystore_setup_failed",
                f"Failed to setup dispenser keystore: {str(e)}",
                {"error": str(e)}
            )
            print(f"❌ Failed to setup keystore: {e}")
            return False

    def unlock_for_session(self, session_duration_hours: int = 1) -> bool:
        """
        Unlock dispenser for a limited session using macOS Keychain.

        Args:
            session_duration_hours: How long session remains active

        Returns:
            True if unlocked successfully
        """
        try:
            # Load keystore metadata
            if not os.path.exists(self.keystore_path):
                raise ValueError("Keystore not found")

            with open(self.keystore_path, 'r') as f:
                keystore_data = json.load(f)

            # Verify setup version compatibility
            if keystore_data.get('setup_version') not in ['3.0', '4.0']:
                raise ValueError("Incompatible keystore version - please recreate keystore")

            # Load keypair from macOS Keychain
            service_name = self._get_keyring_service_name()
            self.unlocked_keypair = self._load_keypair_from_keyring(service_name)

            if not self.unlocked_keypair:
                raise ValueError("Failed to load keypair from macOS Keychain")

            # Verify address matches stored metadata
            if self.unlocked_keypair.ss58_address != keystore_data.get('ss58_address'):
                raise ValueError("Keypair address mismatch - possible tampering")

            self.session_start = datetime.utcnow()

            self.audit_logger.log_event(
                "dispenser_unlocked_address_primary",
                f"Dispenser unlocked for session with address-primary compatibility (address: {self.unlocked_keypair.ss58_address})",
                {
                    "address": self.unlocked_keypair.ss58_address,
                    "session_duration_hours": session_duration_hours,
                    "keychain_load_successful": True
                }
            )

            print(f"✅ Dispenser unlocked for {session_duration_hours} hour session")
            print(f"   Address: {self.unlocked_keypair.ss58_address}")
            print("   🔐 Keypair loaded from macOS Keychain")
            print("   📍 Address-primary compatible")
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

    async def transfer_wnd_to_borg(self, borg_identifier: str, amount_wnd: float, borg_id_for_logging: Optional[str] = None) -> Dict[str, Any]:
        """
        Transfer WND tokens from dispenser to borg address using live Westend network.

        Enhanced for address-primary compatibility - accepts both borg_id and address.

        Args:
            borg_identifier: Borg identifier (either borg_id or substrate address)
            amount_wnd: Amount of WND to transfer
            borg_id_for_logging: Optional borg_id for logging (if different from identifier)

        Returns:
            Transfer result with success status and transaction details
        """
        result = {
            'success': False,
            'error': None,
            'transaction_hash': None,
            'amount_transferred': None,
            'from_address': None,
            'to_address': None,
            'borg_identifier': borg_identifier,
            'block_number': None,
            'block_hash': None
        }

        try:
            # Validate session
            if not self.is_session_active():
                result['error'] = 'Dispenser session not active - unlock required'
                return result

            # Resolve borg address from identifier
            borg_address = self._resolve_borg_address(borg_identifier)
            if not borg_address:
                result['error'] = f'Could not resolve address for borg identifier: {borg_identifier}'
                return result

            result['to_address'] = borg_address

            # Validate inputs
            if amount_wnd <= 0:
                result['error'] = 'Transfer amount must be positive'
                return result

            if amount_wnd > float(self.max_transfer_amount):
                result['error'] = f'Transfer amount {amount_wnd} exceeds maximum {self.max_transfer_amount}'
                return result

            # Check daily limit
            today = datetime.utcnow().date().isoformat()
            daily_used = self.daily_usage.get(today, Decimal('0'))
            amount_decimal = Decimal(str(amount_wnd))

            if daily_used + amount_decimal > self.daily_limit:
                result['error'] = f'Daily limit exceeded: {daily_used + amount_decimal} > {self.daily_limit}'
                return result

            # Initialize WestendAdapter for live transfer
            from jam_mock.kusama_adapter import WestendAdapter
            westend_adapter = WestendAdapter("https://westend.api.onfinality.io/public-ws")
            westend_adapter.set_keypair(self.unlocked_keypair)

            # Convert WND to planck units
            amount_planck = int(amount_wnd * (10 ** 12))

            # Check dispenser balance before transfer
            dispenser_balance = await westend_adapter.get_wnd_balance(self.unlocked_keypair.ss58_address)
            if dispenser_balance < amount_planck:
                result['error'] = f'Insufficient dispenser balance: {dispenser_balance} < {amount_planck} planck'
                return result

            # Execute transfer
            transfer_result = await westend_adapter.transfer_wnd(
                self.unlocked_keypair.ss58_address,
                borg_address,
                amount_planck
            )

            if transfer_result.get('success'):
                # Update daily usage
                self.daily_usage[today] = daily_used + amount_decimal

                # Determine borg_id for logging
                log_borg_id = borg_id_for_logging or borg_identifier
                if borg_address != borg_identifier:
                    log_borg_id = f"{borg_identifier} ({borg_address})"

                # Log successful transfer
                self.audit_logger.log_event(
                    "dispenser_wnd_transfer_completed_address_primary",
                    f"Transferred {amount_wnd} WND from dispenser to borg {log_borg_id} (address-primary compatible)",
                    {
                        'borg_identifier': borg_identifier,
                        'borg_address': borg_address,
                        'dispenser_address': self.unlocked_keypair.ss58_address,
                        'amount_wnd': amount_wnd,
                        'amount_planck': amount_planck,
                        'transaction_hash': transfer_result['transaction_hash'],
                        'block_number': transfer_result.get('block_number'),
                        'block_hash': transfer_result.get('block_hash')
                    }
                )

                result.update({
                    'success': True,
                    'transaction_hash': transfer_result['transaction_hash'],
                    'amount_transferred': amount_planck,
                    'from_address': self.unlocked_keypair.ss58_address,
                    'block_number': transfer_result.get('block_number'),
                    'block_hash': transfer_result.get('block_hash')
                })

                print(f"✅ Transferred {amount_wnd} WND to borg {log_borg_id}")
                print(f"   Transaction: {transfer_result['transaction_hash']}")
                print(f"   Block: {transfer_result.get('block_number')}")
                return result

            else:
                result['error'] = transfer_result.get('error', 'Transfer failed')
                return result

        except Exception as e:
            result['error'] = str(e)
            log_borg_id = borg_id_for_logging or borg_identifier
            self.audit_logger.log_event(
                "dispenser_wnd_transfer_failed",
                f"Failed to transfer WND to borg {log_borg_id}: {str(e)}",
                {
                    'borg_identifier': borg_identifier,
                    'amount_requested': amount_wnd,
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
            'min_balance_threshold': str(self.min_balance_threshold),
            'address_primary_compatible': True
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

        # Add cache info
        status['borg_address_cache_size'] = len(self._borg_address_cache)

        return status

    def _process_seed_securely(self, seed: str) -> Keypair:
        """Process seed with secure cleanup."""
        try:
            keypair = Keypair.create_from_seed(seed)
            # Immediately clear seed from memory
            seed = '\x00' * len(seed)
            return keypair
        except Exception as e:
            seed = '\x00' * len(seed)
            raise

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


# Backward compatibility alias
SecureDispenser = SecureDispenserAddressPrimary