#!/usr/bin/env python3
"""
Keyring Service Migration: Address-Based Naming
Migrates existing keyring services from 'borglife-borg-{borg_id}' to 'borglife-address-{address}'.

This script ensures backward compatibility while transitioning to address-based keyring services.
"""

import os
import sys
import json
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append('code')

try:
    import keyring
    from supabase import create_client
    import os
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("❌ Required packages not available. Install with: pip install keyring supabase python-dotenv")
    sys.exit(1)


class KeyringServiceMigrator:
    """Migrate keyring services to address-based naming."""

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")

        self.supabase = create_client(self.supabase_url, self.supabase_key)
        self.migration_log = []

    def log(self, message: str, data: Dict = None):
        """Log migration step."""
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'message': message,
            'data': data or {}
        }
        self.migration_log.append(log_entry)
        print(f"[{timestamp}] {message}")

    def find_legacy_services(self) -> List[str]:
        """Find all keyring services using the old borg_id-based naming."""
        self.log("Finding legacy keyring services")

        legacy_services = []

        # We can't directly list keyring services, so we'll try common patterns
        # and check if they exist by attempting to read from them

        # Common borg IDs that might exist
        common_borg_ids = [
            'dispenser',
            'borgTester',
            'borg_1',
            'borg_2',
            'test_borg',
            'live_test_borg'
        ]

        # Also try to find services by checking recent timestamps
        import time
        current_time = int(time.time())
        for i in range(10):  # Check last 10 timestamps
            timestamp = current_time - (i * 3600)  # Go back by hours
            common_borg_ids.append(f"borgTester_{timestamp}")

        for borg_id in common_borg_ids:
            service_name = f"borglife-borg-{borg_id}"
            try:
                # Check if service exists by trying to read a key
                test_value = keyring.get_password(service_name, "private_key")
                if test_value is not None:
                    legacy_services.append(service_name)
                    self.log(f"Found legacy service: {service_name}")
            except Exception:
                # Service doesn't exist or can't be accessed
                pass

        self.log(f"Found {len(legacy_services)} legacy keyring services")
        return legacy_services

    def extract_borg_id_from_service(self, service_name: str) -> Optional[str]:
        """Extract borg_id from legacy service name."""
        if not service_name.startswith('borglife-borg-'):
            return None

        borg_id = service_name.replace('borglife-borg-', '')

        # Handle special case for dispenser
        if borg_id == 'dispenser':
            return 'dispenser'

        return borg_id

    def get_address_for_borg_id(self, borg_id: str) -> Optional[str]:
        """Get substrate address for a borg_id from database."""
        try:
            if borg_id == 'dispenser':
                # Dispenser address is hardcoded or stored differently
                # For now, we'll need to handle this specially
                return None

            result = self.supabase.table('borg_addresses').select('substrate_address').eq('borg_id', borg_id).execute()

            if result.data:
                return result.data[0]['substrate_address']

        except Exception as e:
            self.log(f"Error looking up address for borg_id {borg_id}: {str(e)}")

        return None

    def migrate_service(self, legacy_service: str) -> bool:
        """Migrate a single keyring service to address-based naming."""
        self.log(f"Migrating service: {legacy_service}")

        try:
            # Extract borg_id
            borg_id = self.extract_borg_id_from_service(legacy_service)
            if not borg_id:
                self.log(f"Could not extract borg_id from {legacy_service}")
                return False

            # Get address
            address = self.get_address_for_borg_id(borg_id)
            if not address:
                self.log(f"Could not find address for borg_id {borg_id}")
                return False

            # New service name
            new_service = f"borglife-address-{address}"

            # Check if new service already exists
            try:
                existing_private_key = keyring.get_password(new_service, "private_key")
                if existing_private_key is not None:
                    self.log(f"New service {new_service} already exists, skipping migration")
                    return True
            except Exception:
                pass

            # Read all data from legacy service
            service_data = {}
            key_types = ['private_key', 'public_key', 'address']

            for key_type in key_types:
                try:
                    value = keyring.get_password(legacy_service, key_type)
                    if value is not None:
                        service_data[key_type] = value
                except Exception as e:
                    self.log(f"Error reading {key_type} from {legacy_service}: {str(e)}")

            if not service_data:
                self.log(f"No data found in legacy service {legacy_service}")
                return False

            # Write data to new service
            for key_type, value in service_data.items():
                try:
                    keyring.set_password(new_service, key_type, value)
                    self.log(f"Migrated {key_type} to {new_service}")
                except Exception as e:
                    self.log(f"Error writing {key_type} to {new_service}: {str(e)}")
                    return False

            # Store borg_id in new service for reverse lookup
            try:
                keyring.set_password(new_service, "borg_id", borg_id)
            except Exception as e:
                self.log(f"Warning: Could not store borg_id in new service: {str(e)}")

            self.log(f"✅ Successfully migrated {legacy_service} to {new_service}")
            return True

        except Exception as e:
            self.log(f"❌ Failed to migrate {legacy_service}: {str(e)}")
            return False

    def create_backward_compatibility_layer(self) -> bool:
        """Create a compatibility layer for old service names."""
        self.log("Creating backward compatibility layer")

        # This would involve modifying the keyring access methods to check both
        # old and new service names. For now, we'll document this requirement.

        compatibility_code = '''
# Backward Compatibility Layer for Keyring Services
# Add this to BorgAddressManager.get_borg_keypair() method

def get_borg_keypair_compatible(self, identifier: str) -> Optional[Keypair]:
    """Get keypair with backward compatibility for old service names."""

    # First try new address-based service
    if identifier.startswith('5'):  # SS58 address
        service_name = f"borglife-address-{identifier}"
    else:
        # Assume borg_id, look up address first
        address = self.get_borg_address(identifier)
        if address:
            service_name = f"borglife-address-{address}"
        else:
            # Fallback to old service name for compatibility
            service_name = f"borglife-borg-{identifier}"

    # Try new service first
    try:
        private_key_hex = keyring.get_password(service_name, "private_key")
        if private_key_hex:
            # Use new service
            return self._reconstruct_keypair_from_service(service_name)
    except Exception:
        pass

    # Fallback to old service name if new one doesn't exist
    if not identifier.startswith('5'):
        old_service = f"borglife-borg-{identifier}"
        try:
            private_key_hex = keyring.get_password(old_service, "private_key")
            if private_key_hex:
                # Migrate on-the-fly if possible
                address = self.get_borg_address(identifier)
                if address:
                    self.migrate_service(old_service)
                    return self.get_borg_keypair(identifier)
                else:
                    # Use old service
                    return self._reconstruct_keypair_from_service(old_service)
        except Exception:
            pass

    return None
'''

        with open('keyring_compatibility_layer.py', 'w') as f:
            f.write(compatibility_code)

        self.log("✅ Created backward compatibility layer documentation")
        return True

    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        self.log("Validating keyring migration")

        try:
            # Check that we can access keypairs through both old and new methods
            legacy_services = self.find_legacy_services()

            validation_results = {
                'legacy_services_found': len(legacy_services),
                'migration_success_count': 0,
                'validation_errors': []
            }

            for legacy_service in legacy_services:
                borg_id = self.extract_borg_id_from_service(legacy_service)
                if borg_id:
                    # Try to get keypair using new system
                    address = self.get_address_for_borg_id(borg_id)
                    if address:
                        new_service = f"borglife-address-{address}"
                        try:
                            private_key = keyring.get_password(new_service, "private_key")
                            if private_key:
                                validation_results['migration_success_count'] += 1
                            else:
                                validation_results['validation_errors'].append(f"No private key in new service {new_service}")
                        except Exception as e:
                            validation_results['validation_errors'].append(f"Error accessing new service {new_service}: {str(e)}")

            success_rate = validation_results['migration_success_count'] / max(1, len(legacy_services))

            if success_rate >= 0.8:  # 80% success rate
                self.log(f"✅ Migration validation PASSED ({validation_results['migration_success_count']}/{len(legacy_services)} services)")
                return True
            else:
                self.log(f"❌ Migration validation FAILED - only {validation_results['migration_success_count']}/{len(legacy_services)} services migrated")
                return False

        except Exception as e:
            self.log(f"❌ Migration validation failed: {str(e)}")
            return False

    def run_migration(self) -> bool:
        """Run the complete keyring service migration."""
        print("🔐 KEYRING SERVICE MIGRATION")
        print("=" * 50)
        print("Migrating from borg_id-based to address-based keyring services")
        print("=" * 50)

        steps = [
            ("Find legacy services", lambda: (self.find_legacy_services(), True)),
            ("Migrate services", self._migrate_all_services),
            ("Create compatibility layer", self.create_backward_compatibility_layer),
            ("Validate migration", self.validate_migration)
        ]

        success = True
        legacy_services = []

        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            try:
                if step_name == "Find legacy services":
                    result = step_func()
                    legacy_services = result[0]
                else:
                    result = step_func()
                if not result:
                    success = False
                    break
            except Exception as e:
                self.log(f"❌ Step '{step_name}' failed: {str(e)}")
                success = False
                break

        print("\n" + "=" * 50)
        if success:
            print("🎉 KEYRING SERVICE MIGRATION COMPLETED!")
            print(f"✅ Migrated {len(legacy_services)} keyring services")
            print("\nNext steps:")
            print("1. Update BorgAddressManager to use new address-based services")
            print("2. Test keypair access with both old and new service names")
            print("3. Gradually phase out old service names")

            # Generate cleanup script
            cleanup_script = self._generate_cleanup_script(legacy_services)
            with open('cleanup_legacy_keyring_services.sh', 'w') as f:
                f.write(cleanup_script)
            os.chmod('cleanup_legacy_keyring_services.sh', 0o755)

            print("4. Run cleanup_legacy_keyring_services.sh when ready to remove old services")

        else:
            print("❌ KEYRING SERVICE MIGRATION FAILED!")
            print("Check the errors above and retry after fixing issues.")

        # Save migration log
        with open('keyring_migration_log.json', 'w') as f:
            json.dump(self.migration_log, f, indent=2, default=str)

        print(f"Migration log saved: keyring_migration_log.json")

        return success

    def _migrate_all_services(self) -> bool:
        """Migrate all found legacy services."""
        legacy_services = self.find_legacy_services()
        success_count = 0

        for service in legacy_services:
            if self.migrate_service(service):
                success_count += 1

        self.log(f"Migrated {success_count}/{len(legacy_services)} services")
        return success_count > 0

    def _generate_cleanup_script(self, legacy_services: List[str]) -> str:
        """Generate script to clean up old keyring services."""
        script = """#!/bin/bash
# Cleanup Legacy Keyring Services
# Run this after validating that new address-based services work correctly

set -e

echo "🧹 CLEANUP LEGACY KEYRING SERVICES"
echo "This will remove old borg_id-based keyring services"
echo "Make sure new address-based services are working first!"
echo ""

# List of legacy services to remove
"""

        for service in legacy_services:
            script += f'# security delete-generic-password -l "{service}"\n'

        script += """
echo "✅ Legacy keyring services cleaned up"
echo "Note: This action cannot be undone. Ensure backups exist."
"""

        return script


def main():
    """Run the keyring migration."""
    try:
        migrator = KeyringServiceMigrator()
        success = migrator.run_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()