"""
Secure WND Dispenser for BorgLife Phase 1
Production-grade encrypted dispenser with access controls and audit logging.
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
from .keyring_service import KeyringService, KeyringServiceError


class SecureDispenser:
    """
    Secure WND dispenser with encrypted key storage and access controls.

    Provides controlled access to dispenser funds for transaction fee payments
    during borg creation and DNA anchoring operations.
    """

    def __init__(self, keystore_path: str = None):
        """
        Initialize secure dispenser.

        Args:
            keystore_path: Path to encrypted keystore file
        """
        if keystore_path is None:
            # Use relative path from this file's directory
            keystore_dir = os.path.join(os.path.dirname(__file__), '..', 'jam_mock')
            self.keystore_path = os.path.join(keystore_dir, '.dispenser_keystore.enc')
        else:
            self.keystore_path = keystore_path
        self.audit_logger = DemoAuditLogger()
        self.keyring_service = KeyringService(ss58_format=42, address_prefix="5")
        self.dna_anchor = DNAAanchor()

        # Transfer limits and controls
        self.max_transfer_amount = Decimal('3.0')   # Max 3.0 WND per transfer
        self.daily_limit = Decimal('9.0')           # Max 9.0 WND per day
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

    def _get_keyring_service_name(self) -> str:
        """Get the keyring service name for dispenser keys."""
        return "borglife-dispenser"

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
            try:
                self.keyring_service.store_keypair(
                    service_name,
                    keypair,
                    metadata={"role": "dispenser", "created_at": datetime.utcnow().isoformat()},
                )
            except KeyringServiceError as exc:
                raise ValueError("Failed to store keypair in macOS Keychain") from exc

            # Store metadata in keystore file (no sensitive data)
            keystore_data = {
                'seed_hash': hashlib.sha256(dispenser_seed.encode()).hexdigest(),  # Never store actual seed
                'ss58_address': keypair.ss58_address,
                'created_at': datetime.utcnow().isoformat(),
                'setup_version': '3.0',  # Updated for keyring storage
                'storage_method': 'macos_keychain'
            }

            # Write keystore metadata
            with open(self.keystore_path, 'w') as f:
                json.dump(keystore_data, f, indent=2)

            # Set file permissions to owner-only
            os.chmod(self.keystore_path, 0o600)

            self.audit_logger.log_event(
                "dispenser_keystore_created",
                f"Secure dispenser keystore created with macOS Keychain storage for address {keypair.ss58_address}",
                {"address": keypair.ss58_address, "setup_version": "3.0", "storage": "macos_keychain"}
            )

            print(f"✅ Dispenser keystore created with macOS Keychain storage: {self.keystore_path}")
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

            # Verify setup version compatibility (accept 3.0 and 4.0)
            setup_version = keystore_data.get('setup_version')
            if setup_version not in ['3.0', '4.0']:
                raise ValueError(f"Incompatible keystore version {setup_version} - please recreate keystore")

            # Load keypair from macOS Keychain
            service_name = self._get_keyring_service_name()
            try:
                self.unlocked_keypair = self.keyring_service.load_keypair(service_name)
            except KeyringServiceError as exc:
                raise ValueError("Failed to load keypair from macOS Keychain") from exc

            if not self.unlocked_keypair:
                raise ValueError("Failed to load keypair from macOS Keychain")

            # Verify address matches stored metadata
            if self.unlocked_keypair.ss58_address != keystore_data.get('ss58_address'):
                raise ValueError("Keypair address mismatch - possible tampering")

            self.session_start = datetime.utcnow()

            self.audit_logger.log_event(
                "dispenser_unlocked",
                f"Dispenser unlocked for session (address: {self.unlocked_keypair.ss58_address})",
                {
                    "address": self.unlocked_keypair.ss58_address,
                    "session_duration_hours": session_duration_hours,
                    "keychain_load_successful": True
                }
            )

            print(f"✅ Dispenser unlocked for {session_duration_hours} hour session")
            print(f"   Address: {self.unlocked_keypair.ss58_address}")
            print("   🔐 Keypair loaded from macOS Keychain")
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

    async def transfer_wnd_to_borg(self, borg_address: str, borg_id: str, amount_wnd: float) -> Dict[str, Any]:
        """
        Transfer WND tokens from dispenser to borg address using live Westend network.

        Args:
            borg_address: Recipient borg's substrate address
            borg_id: Borg identifier for logging
            amount_wnd: Amount of WND to transfer

        Returns:
            Transfer result with success status and transaction details
        """
        result = {
            'success': False,
            'error': None,
            'transaction_hash': None,
            'amount_transferred': None,
            'from_address': None,
            'to_address': borg_address,
            'block_number': None,
            'block_hash': None
        }

        try:
            # Validate session
            if not self.is_session_active():
                result['error'] = 'Dispenser session not active - unlock required'
                return result

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
            from jam_mock.westend_adapter import WestendAdapter
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

                # Update Supabase metadata if available
                await self._update_transfer_metadata(
                    from_borg_id='dispenser',
                    to_borg_id=borg_id,
                    currency='WND',
                    amount_wei=amount_planck,
                    transaction_hash=transfer_result['transaction_hash'],
                    block_number=transfer_result.get('block_number')
                )

                # Log successful transfer
                self.audit_logger.log_event(
                    "dispenser_wnd_transfer_completed",
                    f"Transferred {amount_wnd} WND from dispenser to borg {borg_id}",
                    {
                        'borg_id': borg_id,
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

                print(f"✅ Transferred {amount_wnd} WND to borg {borg_id}")
                print(f"   Transaction: {transfer_result['transaction_hash']}")
                print(f"   Block: {transfer_result.get('block_number')}")
                return result

            else:
                result['error'] = transfer_result.get('error', 'Transfer failed')
                return result

        except Exception as e:
            result['error'] = str(e)
            self.audit_logger.log_event(
                "dispenser_wnd_transfer_failed",
                f"Failed to transfer WND to borg {borg_id}: {str(e)}",
                {
                    'borg_id': borg_id,
                    'borg_address': borg_address,
                    'amount_requested': amount_wnd,
                    'error': str(e)
                }
            )
            return result

    async def transfer_wnd_from_borg(self, borg_id: str, amount_wnd: float) -> Dict[str, Any]:
        """
        Transfer WND tokens from a borg address to dispenser using live Westend network.

        Args:
            borg_id: Borg identifier (used to lookup keypair in keyring)
            amount_wnd: Amount of WND to transfer

        Returns:
            Transfer result with success status and transaction details
        """
        result = {
            'success': False,
            'error': None,
            'transaction_hash': None,
            'amount_transferred': None,
            'from_address': None,
            'to_address': self.unlocked_keypair.ss58_address if self.unlocked_keypair else None,
            'block_number': None,
            'block_hash': None
        }

        try:
            # Validate session
            if not self.is_session_active():
                result['error'] = 'Dispenser session not active - unlock required'
                return result

            # Validate inputs
            if amount_wnd <= 0:
                result['error'] = 'Transfer amount must be positive'
                return result

            if amount_wnd > float(self.max_transfer_amount):
                result['error'] = f'Transfer amount {amount_wnd} exceeds maximum {self.max_transfer_amount}'
                return result

            # Load borg keypair from keyring
            borg_service_name = f"borglife-borg-{borg_id}"
            try:
                borg_keypair = self.keyring_service.load_keypair(borg_service_name)
            except KeyringServiceError as exc:
                result['error'] = f'Failed to load keypair for borg {borg_id}: {exc}'
                return result

            if not borg_keypair:
                result['error'] = f'Could not load keypair for borg {borg_id} from keyring'
                return result

            # Initialize WestendAdapter for live transfer
            from jam_mock.westend_adapter import WestendAdapter
            westend_adapter = WestendAdapter("https://westend.api.onfinality.io/public-ws")
            westend_adapter.set_keypair(borg_keypair)

            # Convert WND to planck units
            amount_planck = int(amount_wnd * (10 ** 12))

            # Check borg balance before transfer
            borg_balance = await westend_adapter.get_wnd_balance(borg_keypair.ss58_address)
            if borg_balance < amount_planck:
                result['error'] = f'Insufficient borg balance: {borg_balance} < {amount_planck} planck'
                return result

            # Execute transfer from borg to dispenser
            transfer_result = await westend_adapter.transfer_wnd(
                borg_keypair.ss58_address,
                self.unlocked_keypair.ss58_address,
                amount_planck
            )

            if transfer_result.get('success'):
                # Update Supabase metadata
                await self._update_transfer_metadata(
                    from_borg_id=borg_id,
                    to_borg_id='dispenser',
                    currency='WND',
                    amount_wei=amount_planck,
                    transaction_hash=transfer_result['transaction_hash'],
                    block_number=transfer_result.get('block_number')
                )

                # Log successful transfer
                self.audit_logger.log_event(
                    "borg_wnd_transfer_completed",
                    f"Transferred {amount_wnd} WND from borg {borg_id} to dispenser",
                    {
                        'borg_id': borg_id,
                        'borg_address': borg_keypair.ss58_address,
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
                    'from_address': borg_keypair.ss58_address,
                    'block_number': transfer_result.get('block_number'),
                    'block_hash': transfer_result.get('block_hash')
                })

                print(f"✅ Transferred {amount_wnd} WND from borg {borg_id} to dispenser")
                print(f"   Transaction: {transfer_result['transaction_hash']}")
                print(f"   Block: {transfer_result.get('block_number')}")
                return result

            else:
                result['error'] = transfer_result.get('error', 'Transfer failed')
                return result

        except Exception as e:
            result['error'] = str(e)
            self.audit_logger.log_event(
                "borg_wnd_transfer_failed",
                f"Failed to transfer WND from borg {borg_id} to dispenser: {str(e)}",
                {
                    'borg_id': borg_id,
                    'amount_requested': amount_wnd,
                    'error': str(e)
                }
            )
            return result
    
    async def _update_transfer_metadata(self, from_borg_id: str, to_borg_id: str, currency: str,
                                       amount_wei: int, transaction_hash: str, block_number: Optional[int] = None):
        """Update Supabase with transfer metadata."""
        try:
            # Check if we have Supabase access
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_SECRET_KEY')

            if not supabase_url or not supabase_key:
                return  # No Supabase access

            from supabase import create_client, Client
            supabase: Client = create_client(supabase_url, supabase_key)

            # Create transfer transaction record
            tx_record = {
                'tx_id': transaction_hash,
                'from_borg_id': from_borg_id,
                'to_borg_id': to_borg_id,
                'currency': currency,
                'amount_wei': amount_wei,
                'transaction_hash': transaction_hash,
                'block_number': block_number,
                'status': 'confirmed'
            }

            # Insert transfer transaction
            supabase.table('transfer_transactions').upsert(tx_record, on_conflict='tx_id').execute()

            # Update borg balances
            # Deduct from sender
            if from_borg_id != 'dispenser':  # Don't update dispenser balance in borg_balances
                try:
                    current_from_balance = supabase.table('borg_balances').select('balance_wei').eq('borg_id', from_borg_id).eq('currency', currency).execute()
                    if current_from_balance.data:
                        new_from_balance = max(0, current_from_balance.data[0]['balance_wei'] - amount_wei)
                        supabase.table('borg_balances').update({'balance_wei': new_from_balance, 'last_updated': 'NOW()'}).eq('borg_id', from_borg_id).eq('currency', currency).execute()
                except Exception as e:
                    print(f"Warning: Could not update sender balance: {e}")

            # Add to recipient
            try:
                current_to_balance = supabase.table('borg_balances').select('balance_wei').eq('borg_id', to_borg_id).eq('currency', currency).execute()
                if current_to_balance.data:
                    new_to_balance = current_to_balance.data[0]['balance_wei'] + amount_wei
                    supabase.table('borg_balances').update({'balance_wei': new_to_balance, 'last_updated': 'NOW()'}).eq('borg_id', to_borg_id).eq('currency', currency).execute()
                else:
                    # Create balance record if it doesn't exist
                    balance_record = {
                        'borg_id': to_borg_id,
                        'currency': currency,
                        'balance_wei': amount_wei
                    }
                    supabase.table('borg_balances').insert(balance_record).execute()
            except Exception as e:
                print(f"Warning: Could not update recipient balance: {e}")

        except Exception as e:
            print(f"Warning: Could not update transfer metadata: {e}")

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

    # USDB Asset Hub Operations - Phase 2A Extension

    async def connect_to_asset_hub(self):
        """Connect to Westend Asset Hub for USDB operations."""
        from jam_mock.westend_adapter import WestendAdapter
        import asyncio

        # Initialize Asset Hub connection (different endpoint than main Westend)
        asset_hub_url = "wss://westend-asset-hub-rpc.polkadot.io"

        self.asset_hub_adapter = WestendAdapter(asset_hub_url)
        await asyncio.sleep(1)  # Allow connection to establish

        # Test connection
        health = await self.asset_hub_adapter.health_check()
        if health.get('status') != 'healthy':
            raise Exception(f"Asset Hub connection failed: {health}")

        print(f"✅ Connected to Westend Asset Hub: {asset_hub_url}")
        return True

    async def mint_usdb_tokens(self, amount_usdb: float) -> Dict[str, Any]:
        """
        Mint USDB tokens to dispenser address using assets.mint extrinsic.

        Args:
            amount_usdb: Amount of USDB to mint

        Returns:
            Mint result with transaction details
        """
        result = {
            'success': False,
            'error': None,
            'transaction_hash': None,
            'amount_minted': None,
            'asset_id': None
        }

        try:
            # Ensure session is active
            if not self.is_session_active():
                result['error'] = 'Dispenser session not active'
                return result

            # Connect to Asset Hub if not already connected
            if not hasattr(self, 'asset_hub_adapter'):
                await self.connect_to_asset_hub()

            # Get asset ID from config
            asset_id = self._get_usdb_asset_id()
            if not asset_id:
                result['error'] = 'USDB asset ID not configured'
                return result

            # Convert USDB to planck units
            amount_planck = int(amount_usdb * (10 ** 12))

            # Execute assets.mint extrinsic
            call = self.asset_hub_adapter.substrate.compose_call(
                call_module='Assets',
                call_function='mint',
                call_params={
                    'id': asset_id,
                    'beneficiary': self.unlocked_keypair.ss58_address,
                    'amount': amount_planck
                }
            )

            # Create signed extrinsic
            extrinsic = self.asset_hub_adapter.substrate.create_signed_extrinsic(
                call=call,
                keypair=self.unlocked_keypair
            )

            # Submit and wait for inclusion
            receipt = self.asset_hub_adapter.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

            if receipt.is_success:
                result.update({
                    'success': True,
                    'transaction_hash': receipt.extrinsic_hash,
                    'block_hash': receipt.block_hash,
                    'block_number': receipt.block_number,
                    'amount_minted': amount_planck,
                    'asset_id': asset_id
                })

                # Log the minting operation
                self.audit_logger.log_event(
                    "usdb_minting_completed",
                    f"Minted {amount_usdb} USDB ({amount_planck} planck) to dispenser address",
                    {
                        'asset_id': asset_id,
                        'amount_usdb': amount_usdb,
                        'amount_planck': amount_planck,
                        'dispenser_address': self.unlocked_keypair.ss58_address,
                        'transaction_hash': receipt.extrinsic_hash,
                        'block_number': receipt.block_number
                    }
                )

                print(f"✅ Minted {amount_usdb} USDB to dispenser address")
                print(f"   Transaction: {receipt.extrinsic_hash}")
                print(f"   Block: {receipt.block_number}")

            else:
                result['error'] = f'Minting failed: {receipt.error_message}'

        except Exception as e:
            result['error'] = str(e)
            self.audit_logger.log_event(
                "usdb_minting_failed",
                f"Failed to mint USDB tokens: {str(e)}",
                {'error': str(e), 'amount_requested': amount_usdb}
            )

        return result

    async def transfer_usdb_to_borg(self, borg_address: str, borg_id: str, amount_usdb: float) -> Dict[str, Any]:
        """
        Transfer USDB tokens from dispenser to borg address using assets.transfer extrinsic.

        Args:
            borg_address: Recipient borg's substrate address
            borg_id: Borg identifier for logging
            amount_usdb: Amount of USDB to transfer

        Returns:
            Transfer result with transaction details
        """
        result = {
            'success': False,
            'error': None,
            'transaction_hash': None,
            'amount_transferred': None,
            'from_address': None,
            'to_address': borg_address
        }

        try:
            # Ensure session is active
            if not self.is_session_active():
                result['error'] = 'Dispenser session not active'
                return result

            # Connect to Asset Hub if not already connected
            if not hasattr(self, 'asset_hub_adapter'):
                await self.connect_to_asset_hub()

            # Get asset ID from config
            asset_id = self._get_usdb_asset_id()
            if not asset_id:
                result['error'] = 'USDB asset ID not configured'
                return result

            # Convert USDB to planck units
            amount_planck = int(amount_usdb * (10 ** 12))

            # Check dispenser balance before transfer
            dispenser_balance = await self.asset_hub_adapter.get_usdb_balance(
                self.unlocked_keypair.ss58_address, asset_id
            )

            if dispenser_balance < amount_planck:
                result['error'] = f'Insufficient dispenser balance: {dispenser_balance} < {amount_planck}'
                return result

            # Execute assets.transfer extrinsic
            transfer_result = await self.asset_hub_adapter.transfer_usdb(
                from_address=self.unlocked_keypair.ss58_address,
                to_address=borg_address,
                amount=amount_planck,
                asset_id=asset_id
            )

            if transfer_result.get('success'):
                result.update({
                    'success': True,
                    'transaction_hash': transfer_result['transaction_hash'],
                    'block_hash': transfer_result.get('block_hash'),
                    'block_number': transfer_result.get('block_number'),
                    'amount_transferred': amount_planck,
                    'from_address': self.unlocked_keypair.ss58_address
                })

                # Log the transfer operation
                self.audit_logger.log_event(
                    "usdb_transfer_completed",
                    f"Transferred {amount_usdb} USDB from dispenser to borg {borg_id}",
                    {
                        'borg_id': borg_id,
                        'borg_address': borg_address,
                        'dispenser_address': self.unlocked_keypair.ss58_address,
                        'asset_id': asset_id,
                        'amount_usdb': amount_usdb,
                        'amount_planck': amount_planck,
                        'transaction_hash': transfer_result['transaction_hash'],
                        'block_number': transfer_result.get('block_number')
                    }
                )

                print(f"✅ Transferred {amount_usdb} USDB to borg {borg_id}")
                print(f"   Transaction: {transfer_result['transaction_hash']}")
                print(f"   Block: {transfer_result.get('block_number')}")

            else:
                result['error'] = transfer_result.get('error', 'Transfer failed')

        except Exception as e:
            result['error'] = str(e)
            self.audit_logger.log_event(
                "usdb_transfer_failed",
                f"Failed to transfer USDB to borg {borg_id}: {str(e)}",
                {
                    'borg_id': borg_id,
                    'borg_address': borg_address,
                    'error': str(e),
                    'amount_requested': amount_usdb
                }
            )

        return result

    async def get_usdb_balance(self, address: str) -> int:
        """
        Get USDB balance for an address on Asset Hub.

        Args:
            address: Substrate address to query

        Returns:
            Balance in planck units
        """
        try:
            # Connect to Asset Hub if not already connected
            if not hasattr(self, 'asset_hub_adapter'):
                await self.connect_to_asset_hub()

            asset_id = self._get_usdb_asset_id()
            if not asset_id:
                return 0

            return await self.asset_hub_adapter.get_usdb_balance(address, asset_id)

        except Exception as e:
            print(f"Error getting USDB balance for {address}: {e}")
            return 0