#!/usr/bin/env python3
"""
Comprehensive Backup Script for Blockchain Address Primary Key Refactor
Creates full backup of keyring entries, database exports, and service mappings.
Includes rollback script generation for emergency recovery.
"""

import os
import sys
import json
import subprocess
from datetime import datetime
import keyring
import shutil

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class ComprehensiveBackup:
    """Create comprehensive backup of keyring and database before refactoring."""

    def __init__(self, backup_dir):
        self.backup_dir = backup_dir
        self.timestamp = datetime.utcnow().isoformat()
        self.backup_data = {
            'timestamp': self.timestamp,
            'keyring_entries': {},
            'database_exports': {},
            'file_backups': {},
            'service_mappings': {},
            'rollback_script': None
        }

    def backup_keyring_entries(self):
        """Backup all keyring entries related to borglife."""
        print("🔑 Backing up keyring entries...")

        # Common service name patterns to backup
        service_patterns = [
            'borglife-dispenser',
            'borglife-borg-',
            'borglife-address-'
        ]

        keyring_entries = {}

        for pattern in service_patterns:
            if pattern.endswith('-'):
                # Find all services matching pattern
                try:
                    # Use security command to list keychain items (macOS specific)
                    result = subprocess.run([
                        'security', 'dump-keychain', '-d'
                    ], capture_output=True, text=True, timeout=30)

                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if pattern in line and '"borglife' in line:
                                # Extract service name
                                service_name = line.split('"')[1] if '"' in line else None
                                if service_name and service_name.startswith('borglife'):
                                    keyring_entries[service_name] = self._backup_service(service_name)
                    else:
                        print(f"⚠️  Could not dump keychain: {result.stderr}")
                except Exception as e:
                    print(f"⚠️  Error accessing keychain: {e}")
            else:
                # Direct service name
                keyring_entries[pattern] = self._backup_service(pattern)

        self.backup_data['keyring_entries'] = keyring_entries
        print(f"✅ Backed up {len(keyring_entries)} keyring services")

    def _backup_service(self, service_name):
        """Backup a specific keyring service."""
        service_data = {}

        # Common key types used in borglife
        key_types = ['private_key', 'public_key', 'address', 'seed']

        for key_type in key_types:
            try:
                value = keyring.get_password(service_name, key_type)
                if value:
                    # Mask sensitive data in logs but keep full data in backup
                    masked_value = value[:16] + '...' if len(value) > 16 else value
                    service_data[key_type] = {
                        'value': value,  # Full value for backup
                        'masked': masked_value,
                        'length': len(value)
                    }
            except Exception as e:
                service_data[key_type] = {'error': str(e)}

        return service_data

    def backup_database_data(self):
        """Backup database tables and data."""
        print("💾 Backing up database data...")

        # Try to connect to Supabase and export data
        try:
            # Import here to avoid dependency issues
            from supabase import create_client
            import os
            from dotenv import load_dotenv

            load_dotenv()

            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

            if supabase_url and supabase_key:
                supabase = create_client(supabase_url, supabase_key)

                # Tables to backup
                tables = ['borg_addresses', 'borg_balances', 'transfer_transactions']

                for table in tables:
                    try:
                        result = supabase.table(table).select('*').execute()
                        self.backup_data['database_exports'][table] = {
                            'data': result.data,
                            'count': len(result.data) if result.data else 0
                        }
                        print(f"✅ Backed up {len(result.data) if result.data else 0} records from {table}")
                    except Exception as e:
                        print(f"⚠️  Failed to backup {table}: {e}")
                        self.backup_data['database_exports'][table] = {'error': str(e)}
            else:
                print("⚠️  Supabase credentials not found")
                self.backup_data['database_exports'] = {'error': 'No Supabase credentials'}

        except Exception as e:
            print(f"⚠️  Database backup failed: {e}")
            self.backup_data['database_exports'] = {'error': str(e)}

    def backup_files(self):
        """Backup important files and directories."""
        print("📁 Backing up important files...")

        files_to_backup = [
            'code/jam_mock/.dispenser_keystore.enc',
            'code/.borglife_config',
            'code/.westend_config',
            '.env',
            '.env.borglife',
            '.env.test'
        ]

        for file_path in files_to_backup:
            if os.path.exists(file_path):
                try:
                    # Copy file to backup directory
                    backup_path = os.path.join(self.backup_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, backup_path)
                    self.backup_data['file_backups'][file_path] = {
                        'backed_up': True,
                        'backup_path': backup_path,
                        'size': os.path.getsize(file_path)
                    }
                    print(f"✅ Backed up {file_path}")
                except Exception as e:
                    self.backup_data['file_backups'][file_path] = {'error': str(e)}
                    print(f"⚠️  Failed to backup {file_path}: {e}")
            else:
                self.backup_data['file_backups'][file_path] = {'not_found': True}

    def document_service_mappings(self):
        """Document current service name mappings and relationships."""
        print("📋 Documenting service mappings...")

        mappings = {
            'dispenser': {
                'service_name': 'borglife-dispenser',
                'purpose': 'WND dispenser keypair storage',
                'key_types': ['private_key', 'public_key', 'address']
            },
            'borg_pattern': {
                'service_name': 'borglife-borg-{borg_id}',
                'purpose': 'Individual borg keypair storage',
                'key_types': ['private_key', 'public_key', 'address'],
                'example': 'borglife-borg-borgTest1_1762870300'
            },
            'address_pattern': {
                'service_name': 'borglife-address-{address}',
                'purpose': 'Future address-based keypair storage',
                'key_types': ['private_key', 'public_key', 'address'],
                'status': 'not_yet_implemented'
            }
        }

        self.backup_data['service_mappings'] = mappings
        print("✅ Documented service name patterns and relationships")

    def create_rollback_script(self):
        """Create rollback script for emergency recovery."""
        print("🔄 Creating rollback script...")

        rollback_script = f"""#!/bin/bash
# Rollback Script for Blockchain Address Primary Key Refactor
# Generated: {self.timestamp}
# Backup Directory: {self.backup_dir}

set -e

echo "🚨 EMERGENCY ROLLBACK - Blockchain Address Primary Key Refactor"
echo "Generated: {self.timestamp}"
echo "Backup Directory: {self.backup_dir}"
echo ""

# Stop all services (add your service stop commands here)
echo "🛑 Stopping services..."
# systemctl stop borglife-service  # Example
echo "✅ Services stopped"
echo ""

# Restore keyring entries
echo "🔑 Restoring keyring entries..."
python3 -c "
import keyring
import json

# Load backup data
with open('{self.backup_dir}/backup_manifest.json', 'r') as f:
    backup = json.load(f)

# Restore keyring entries
for service_name, service_data in backup['keyring_entries'].items():
    print(f'Restoring service: {{service_name}}')
    for key_type, key_data in service_data.items():
        if 'value' in key_data:
            keyring.set_password(service_name, key_type, key_data['value'])
            print(f'  Restored {{key_type}}')

print('✅ Keyring entries restored')
"
echo ""

# Restore files
echo "📁 Restoring files..."
"""

        # Add file restoration commands
        for file_path, file_info in self.backup_data['file_backups'].items():
            if file_info.get('backed_up'):
                backup_path = file_info['backup_path']
                rollback_script += f"cp '{backup_path}' '{file_path}'\n"

        rollback_script += """
echo "✅ Files restored"
echo ""

# Database rollback would need manual intervention
echo "💾 Database rollback requires manual intervention:"
echo "  1. Restore from backup dump if available"
echo "  2. Or manually recreate dropped tables/indexes"
echo "  3. Verify data integrity"
echo ""

# Restart services
echo "▶️  Restarting services..."
# systemctl start borglife-service  # Example
echo "✅ Services restarted"
echo ""

echo "🎉 Rollback completed successfully!"
echo "Please verify system functionality before resuming normal operations."
"""

        rollback_path = os.path.join(self.backup_dir, 'rollback_emergency.sh')
        with open(rollback_path, 'w') as f:
            f.write(rollback_script)

        os.chmod(rollback_path, 0o755)

        self.backup_data['rollback_script'] = rollback_path
        print(f"✅ Created rollback script: {rollback_path}")

    def save_backup_manifest(self):
        """Save backup manifest with all backup information."""
        manifest_path = os.path.join(self.backup_dir, 'backup_manifest.json')

        # Create a safe version for logging (mask sensitive data)
        safe_backup = self._create_safe_backup_copy()

        with open(manifest_path, 'w') as f:
            json.dump(safe_backup, f, indent=2, default=str)

        print(f"✅ Saved backup manifest: {manifest_path}")

    def _create_safe_backup_copy(self):
        """Create a safe copy of backup data with sensitive information masked."""
        safe_copy = self.backup_data.copy()

        # Mask sensitive keyring data
        if 'keyring_entries' in safe_copy:
            for service_name, service_data in safe_copy['keyring_entries'].items():
                for key_type, key_info in service_data.items():
                    if isinstance(key_info, dict) and 'value' in key_info:
                        original_value = key_info['value']
                        if len(original_value) > 16:
                            key_info['value'] = original_value[:8] + '***MASKED***' + original_value[-8:]
                        else:
                            key_info['value'] = '***MASKED***'

        return safe_copy

    def run_full_backup(self):
        """Run the complete backup process."""
        print(f"🚀 Starting comprehensive backup to: {self.backup_dir}")
        print(f"Timestamp: {self.timestamp}")
        print("=" * 60)

        try:
            self.backup_keyring_entries()
            self.backup_database_data()
            self.backup_files()
            self.document_service_mappings()
            self.create_rollback_script()
            self.save_backup_manifest()

            print("=" * 60)
            print("🎉 Comprehensive backup completed successfully!")
            print(f"Backup Directory: {self.backup_dir}")
            print(f"Manifest: {os.path.join(self.backup_dir, 'backup_manifest.json')}")
            print(f"Rollback Script: {self.backup_data['rollback_script']}")

            return True

        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False


def main():
    """Main backup execution."""
    backup_dir = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    backup = ComprehensiveBackup(backup_dir)
    success = backup.run_full_backup()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()