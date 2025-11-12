"""
Borg Address Manager - Robust Keypair Reconstruction
Enhanced version with comprehensive error handling for keypair reconstruction.

This version prevents None comparison errors and provides detailed error messages
for all failure scenarios in keypair reconstruction.
"""

import os
import hashlib
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from substrateinterface import Keypair

from .secure_key_storage import SecureKeyStore
from .demo_audit_logger import DemoAuditLogger
from security.dna_anchor import DNAAanchor


class KeypairReconstructionError(Exception):
    """Custom exception for keypair reconstruction failures."""

    def __init__(self, message: str, identifier: str = None, error_code: str = None, details: Dict[str, Any] = None):
        self.identifier = identifier
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class BorgAddressManagerRobust:
    """
    Borg Address Manager with robust keypair reconstruction error handling.

    Enhanced version that prevents None comparison errors and provides
    comprehensive validation and error reporting.
    """

    def __init__(self, supabase_client=None, audit_logger: Optional[DemoAuditLogger] = None, keystore: Optional[SecureKeyStore] = None):
        """
        Initialize robust BorgAddressManager.

        Args:
            supabase_client: Supabase client for database operations
            audit_logger: Audit logger for compliance tracking
            keystore: Optional shared keystore instance (must be unlocked)
        """
        self.supabase = supabase_client
        self.audit_logger = audit_logger or DemoAuditLogger()

        # Use shared keystore if provided, otherwise create new one
        if keystore:
            self.secure_storage = keystore
            self._shared_keystore = True
        else:
            # Use unique keystore path to avoid conflicts
            import tempfile
            import uuid
            temp_dir = tempfile.gettempdir()
            unique_id = str(uuid.uuid4())[:8]
            keystore_path = f"{temp_dir}/borglife_keystore_{unique_id}.enc"
            self.secure_storage = SecureKeyStore(keystore_path)
            self._shared_keystore = False

        # Unlock keystore automatically using macOS Keychain
        try:
            self.secure_storage.unlock_keystore()
            self.audit_logger.log_event(
                "keystore_auto_unlocked",
                "Keystore automatically unlocked using macOS Keychain",
                {"demo_mode": True, "storage": "macos_keychain"}
            )
        except Exception as e:
            self.audit_logger.log_event(
                "keystore_unlock_failed",
                f"Failed to auto-unlock keystore: {str(e)}",
                {"error": str(e)}
            )

        self.dna_anchor = DNAAanchor(audit_logger)

        # Cache for lookups
        self._address_cache: Dict[str, Dict[str, Any]] = {}
        self._borg_id_cache: Dict[str, str] = {}

    def get_borg_keypair_robust(self, identifier: str) -> Keypair:
        """
        Retrieve borg keypair with comprehensive error handling.

        Args:
            identifier: Borg ID or substrate address

        Returns:
            Keypair object

        Raises:
            KeypairReconstructionError: If keypair cannot be reconstructed
        """
        if not identifier:
            raise KeypairReconstructionError(
                "Identifier cannot be None or empty",
                error_code="INVALID_IDENTIFIER"
            )

        try:
            # Determine service name based on identifier type
            service_name = self._resolve_service_name(identifier)
            if not service_name:
                raise KeypairReconstructionError(
                    f"Could not resolve service name for identifier: {identifier}",
                    identifier=identifier,
                    error_code="SERVICE_NAME_RESOLUTION_FAILED"
                )

            # Retrieve and validate keypair components
            keypair_data = self._retrieve_keypair_data(service_name, identifier)
            if not keypair_data:
                raise KeypairReconstructionError(
                    f"No keypair data found for identifier: {identifier}",
                    identifier=identifier,
                    error_code="KEYPAIR_DATA_NOT_FOUND"
                )

            # Reconstruct and validate keypair
            keypair = self._reconstruct_keypair(keypair_data, identifier)
            if not keypair:
                raise KeypairReconstructionError(
                    f"Keypair reconstruction failed for identifier: {identifier}",
                    identifier=identifier,
                    error_code="KEYPAIR_RECONSTRUCTION_FAILED"
                )

            # Final validation
            self._validate_final_keypair(keypair, identifier)

            self.audit_logger.log_event(
                "keypair_retrieved_robust",
                f"Keypair successfully retrieved with robust error handling for {identifier}",
                {"identifier": identifier, "service_name": service_name}
            )

            return keypair

        except KeypairReconstructionError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise KeypairReconstructionError(
                f"Unexpected error retrieving keypair for {identifier}: {str(e)}",
                identifier=identifier,
                error_code="UNEXPECTED_ERROR",
                details={"original_error": str(e), "error_type": type(e).__name__}
            ) from e

    def _resolve_service_name(self, identifier: str) -> Optional[str]:
        """
        Resolve the keyring service name for an identifier.

        Supports both borg_id and address-based lookups with fallback.
        """
        # Check if it's an SS58 address
        if identifier.startswith('5') and len(identifier) == 48:
            # Address-based service (new format)
            return f"borglife-address-{identifier}"
        else:
            # Borg ID - need to look up address first
            address = self.get_borg_address(identifier)
            if address:
                return f"borglife-address-{address}"

            # Fallback to old service name for backward compatibility
            return f"borglife-borg-{identifier}"

    def _retrieve_keypair_data(self, service_name: str, identifier: str) -> Optional[Dict[str, str]]:
        """
        Retrieve keypair data from keyring with validation.

        Returns:
            Dict with private_key, public_key, address, or None if not found
        """
        import keyring

        keypair_data = {}
        required_keys = ['private_key', 'public_key', 'address']

        for key_type in required_keys:
            try:
                value = keyring.get_password(service_name, key_type)
                if value is None:
                    self.audit_logger.log_event(
                        "keyring_key_missing",
                        f"Key {key_type} not found in service {service_name} for {identifier}",
                        {"service_name": service_name, "key_type": key_type, "identifier": identifier}
                    )
                    return None

                # Basic validation
                if key_type == 'private_key' and len(value) != 128:
                    raise KeypairReconstructionError(
                        f"Invalid private key length: expected 128 chars, got {len(value)}",
                        identifier=identifier,
                        error_code="INVALID_PRIVATE_KEY_LENGTH"
                    )

                if key_type == 'public_key' and len(value) != 64:
                    raise KeypairReconstructionError(
                        f"Invalid public key length: expected 64 chars, got {len(value)}",
                        identifier=identifier,
                        error_code="INVALID_PUBLIC_KEY_LENGTH"
                    )

                if key_type == 'address' and not value.startswith('5'):
                    raise KeypairReconstructionError(
                        f"Invalid address format: expected SS58 address starting with '5', got {value[:10]}...",
                        identifier=identifier,
                        error_code="INVALID_ADDRESS_FORMAT"
                    )

                keypair_data[key_type] = value

            except keyring.errors.KeyringError as e:
                raise KeypairReconstructionError(
                    f"Keyring access error for {key_type} in {service_name}: {str(e)}",
                    identifier=identifier,
                    error_code="KEYRING_ACCESS_ERROR",
                    details={"key_type": key_type, "service_name": service_name}
                ) from e

        return keypair_data

    def _reconstruct_keypair(self, keypair_data: Dict[str, str], identifier: str) -> Optional[Keypair]:
        """
        Reconstruct keypair from hex data with comprehensive validation.

        Returns:
            Keypair object or None if reconstruction fails
        """
        try:
            private_key_hex = keypair_data['private_key']
            public_key_hex = keypair_data['public_key']
            address = keypair_data['address']

            # Convert private key from hex
            try:
                private_key_bytes = bytes.fromhex(private_key_hex)
            except ValueError as e:
                raise KeypairReconstructionError(
                    f"Invalid private key hex format: {str(e)}",
                    identifier=identifier,
                    error_code="INVALID_PRIVATE_KEY_HEX"
                ) from e

            # Validate private key length (should be 64 bytes for ed25519)
            if len(private_key_bytes) != 64:
                raise KeypairReconstructionError(
                    f"Invalid private key byte length: expected 64, got {len(private_key_bytes)}",
                    identifier=identifier,
                    error_code="INVALID_PRIVATE_KEY_BYTES"
                )

            # Reconstruct keypair
            try:
                keypair = Keypair(private_key=private_key_bytes, ss58_format=42)
            except Exception as e:
                raise KeypairReconstructionError(
                    f"Keypair creation failed: {str(e)}",
                    identifier=identifier,
                    error_code="KEYPAIR_CREATION_FAILED",
                    details={"error_type": type(e).__name__}
                ) from e

            # Validate reconstructed keypair
            if not hasattr(keypair, 'private_key') or keypair.private_key is None:
                raise KeypairReconstructionError(
                    "Reconstructed keypair missing private key",
                    identifier=identifier,
                    error_code="MISSING_PRIVATE_KEY"
                )

            if not hasattr(keypair, 'public_key') or keypair.public_key is None:
                raise KeypairReconstructionError(
                    "Reconstructed keypair missing public key",
                    identifier=identifier,
                    error_code="MISSING_PUBLIC_KEY"
                )

            if not hasattr(keypair, 'ss58_address') or not keypair.ss58_address:
                raise KeypairReconstructionError(
                    "Reconstructed keypair missing SS58 address",
                    identifier=identifier,
                    error_code="MISSING_SS58_ADDRESS"
                )

            # Verify public key matches expected
            reconstructed_public_hex = keypair.public_key.hex()
            if reconstructed_public_hex != public_key_hex:
                raise KeypairReconstructionError(
                    "Public key mismatch during reconstruction",
                    identifier=identifier,
                    error_code="PUBLIC_KEY_MISMATCH",
                    details={
                        "expected": public_key_hex,
                        "reconstructed": reconstructed_public_hex
                    }
                )

            # Verify address matches expected
            if keypair.ss58_address != address:
                raise KeypairReconstructionError(
                    "Address mismatch during reconstruction",
                    identifier=identifier,
                    error_code="ADDRESS_MISMATCH",
                    details={
                        "expected": address,
                        "reconstructed": keypair.ss58_address
                    }
                )

            return keypair

        except KeypairReconstructionError:
            raise
        except Exception as e:
            raise KeypairReconstructionError(
                f"Unexpected error during keypair reconstruction: {str(e)}",
                identifier=identifier,
                error_code="UNEXPECTED_RECONSTRUCTION_ERROR",
                details={"error_type": type(e).__name__}
            ) from e

    def _validate_final_keypair(self, keypair: Keypair, identifier: str) -> None:
        """
        Perform final validation on reconstructed keypair.

        Tests signing capability and overall integrity.
        """
        try:
            # Test signing capability
            test_message = b"BorgLife keypair validation test"
            signature = keypair.sign(test_message)

            if not signature:
                raise KeypairReconstructionError(
                    "Keypair signing test failed - no signature produced",
                    identifier=identifier,
                    error_code="SIGNING_TEST_FAILED"
                )

            # Test signature verification
            is_valid = keypair.verify(test_message, signature)

            if not is_valid:
                raise KeypairReconstructionError(
                    "Keypair signature verification failed",
                    identifier=identifier,
                    error_code="SIGNATURE_VERIFICATION_FAILED"
                )

            # Additional validation: ensure address is valid SS58
            if not (keypair.ss58_address.startswith('5') and len(keypair.ss58_address) == 48):
                raise KeypairReconstructionError(
                    f"Invalid SS58 address format: {keypair.ss58_address}",
                    identifier=identifier,
                    error_code="INVALID_SS58_FORMAT"
                )

        except KeypairReconstructionError:
            raise
        except Exception as e:
            raise KeypairReconstructionError(
                f"Final keypair validation failed: {str(e)}",
                identifier=identifier,
                error_code="FINAL_VALIDATION_FAILED",
                details={"error_type": type(e).__name__}
            ) from e

    # Legacy methods for backward compatibility
    def get_borg_address(self, borg_id: str) -> Optional[str]:
        """Get substrate address for a borg (legacy method)."""
        if borg_id in self._borg_id_cache:
            return self._borg_id_cache[borg_id]

        if self.supabase:
            try:
                rest_result = self.supabase.table('borg_addresses').select('substrate_address').eq('borg_id', borg_id).execute()
                if rest_result.data:
                    address = rest_result.data[0]['substrate_address']
                    self._borg_id_cache[borg_id] = address
                    return address
            except Exception as e:
                self.audit_logger.log_event(
                    "address_lookup_failed",
                    f"Failed to lookup address for borg {borg_id}: {str(e)}",
                    {"borg_id": borg_id, "error": str(e)}
                )

        return None

    def get_borg_keypair(self, identifier: str) -> Optional[Keypair]:
        """Legacy method - wraps robust version."""
        try:
            return self.get_borg_keypair_robust(identifier)
        except KeypairReconstructionError as e:
            self.audit_logger.log_event(
                "keypair_reconstruction_error",
                f"Keypair reconstruction failed for {identifier}: {str(e)}",
                {
                    "identifier": identifier,
                    "error_code": e.error_code,
                    "details": e.details
                }
            )
            return None

    # Additional utility methods
    def validate_keypair_access(self, identifier: str) -> Dict[str, Any]:
        """
        Validate keypair access and return detailed status.

        Returns:
            Dict with validation results and any error details
        """
        result = {
            'identifier': identifier,
            'accessible': False,
            'service_name': None,
            'error': None,
            'error_code': None
        }

        try:
            service_name = self._resolve_service_name(identifier)
            result['service_name'] = service_name

            if not service_name:
                result['error'] = "Could not resolve service name"
                result['error_code'] = "SERVICE_NAME_RESOLUTION_FAILED"
                return result

            # Try to access keypair
            keypair = self.get_borg_keypair_robust(identifier)
            result['accessible'] = True

        except KeypairReconstructionError as e:
            result['error'] = str(e)
            result['error_code'] = e.error_code
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            result['error_code'] = "UNEXPECTED_ERROR"

        return result

    def diagnose_keypair_issues(self, identifier: str) -> Dict[str, Any]:
        """
        Comprehensive diagnosis of keypair access issues.

        Returns:
            Detailed diagnostic information
        """
        diagnosis = {
            'identifier': identifier,
            'issues': [],
            'recommendations': []
        }

        # Check service name resolution
        service_name = self._resolve_service_name(identifier)
        if not service_name:
            diagnosis['issues'].append("Cannot resolve keyring service name")
            diagnosis['recommendations'].append("Check if borg is registered in database")
            return diagnosis

        diagnosis['service_name'] = service_name

        # Check individual key access
        import keyring
        key_types = ['private_key', 'public_key', 'address']

        for key_type in key_types:
            try:
                value = keyring.get_password(service_name, key_type)
                if value is None:
                    diagnosis['issues'].append(f"Missing {key_type} in keyring")
                    diagnosis['recommendations'].append(f"Check if {key_type} was stored correctly")
                elif key_type == 'private_key' and len(value) != 128:
                    diagnosis['issues'].append(f"Invalid {key_type} length: {len(value)} (expected 128)")
                elif key_type == 'public_key' and len(value) != 64:
                    diagnosis['issues'].append(f"Invalid {key_type} length: {len(value)} (expected 64)")
                elif key_type == 'address' and not value.startswith('5'):
                    diagnosis['issues'].append(f"Invalid address format: {value[:10]}...")
            except Exception as e:
                diagnosis['issues'].append(f"Error accessing {key_type}: {str(e)}")

        # Check database consistency
        if identifier.startswith('5'):
            borg_id = self.get_borg_id(identifier)
            if not borg_id:
                diagnosis['issues'].append("Address not found in database")
                diagnosis['recommendations'].append("Register borg in database")
        else:
            address = self.get_borg_address(identifier)
            if not address:
                diagnosis['issues'].append("Borg ID not found in database")
                diagnosis['recommendations'].append("Register borg in database")

        return diagnosis


# Convenience functions
def get_borg_keypair_safe(identifier: str, address_manager=None) -> Tuple[Optional[Keypair], Optional[str]]:
    """
    Safe keypair retrieval with error handling.

    Returns:
        Tuple of (keypair, error_message)
    """
    if not address_manager:
        address_manager = BorgAddressManagerRobust()

    try:
        keypair = address_manager.get_borg_keypair_robust(identifier)
        return keypair, None
    except KeypairReconstructionError as e:
        return None, str(e)


def diagnose_keypair_problem(identifier: str, address_manager=None) -> Dict[str, Any]:
    """
    Diagnose keypair access problems.

    Returns:
        Diagnostic information
    """
    if not address_manager:
        address_manager = BorgAddressManagerRobust()

    return address_manager.diagnose_keypair_issues(identifier)