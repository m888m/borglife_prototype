#!/usr/bin/env python3
"""
Database Migration: Address Primary Key Refactor
Migrates borg_addresses and borg_balances tables to use substrate_address as primary key.

This script creates new tables with address-based primary keys and migrates existing data.
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append('code')

try:
    from supabase import create_client
    import os
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("❌ Required packages not available. Install with: pip install supabase python-dotenv")
    sys.exit(1)


class AddressPrimaryKeyMigrator:
    """Migrate database to use address as primary key."""

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")

        self.supabase = create_client(self.supabase_url, self.supabase_key)
        self.migration_log = []

    def log(self, message: str, data: Dict[str, Any] = None):
        """Log migration step."""
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'message': message,
            'data': data or {}
        }
        self.migration_log.append(log_entry)
        print(f"[{timestamp}] {message}")

    def create_new_tables(self) -> bool:
        """Create new tables with address-based primary keys."""
        self.log("Creating new tables with address primary keys")

        # New borg_addresses table with address as primary key
        borg_addresses_sql = """
        CREATE TABLE IF NOT EXISTS borg_addresses_new (
            substrate_address VARCHAR(100) PRIMARY KEY,
            borg_id VARCHAR(100) NOT NULL UNIQUE,
            dna_hash VARCHAR(100) NOT NULL,
            keypair_encrypted TEXT NOT NULL,
            creator_public_key VARCHAR(100),
            creator_signature VARCHAR(200),
            anchoring_tx_hash VARCHAR(100),
            anchoring_status VARCHAR(20) DEFAULT 'pending',
            keyring_service_name VARCHAR(100),
            setup_version VARCHAR(10) DEFAULT '4.1',
            storage_method VARCHAR(50) DEFAULT 'macos_keychain_address_primary',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_sync TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        # New borg_balances table with address as primary key
        borg_balances_sql = """
        CREATE TABLE IF NOT EXISTS borg_balances_new (
            substrate_address VARCHAR(100) REFERENCES borg_addresses_new(substrate_address),
            currency VARCHAR(10) NOT NULL CHECK (currency IN ('WND', 'USDB')),
            balance_wei BIGINT NOT NULL DEFAULT 0,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (substrate_address, currency)
        );
        """

        # New transfer_transactions table (if needed)
        transfer_transactions_sql = """
        CREATE TABLE IF NOT EXISTS transfer_transactions_new (
            tx_id VARCHAR(100) PRIMARY KEY,
            from_address VARCHAR(100) REFERENCES borg_addresses_new(substrate_address),
            to_address VARCHAR(100) REFERENCES borg_addresses_new(substrate_address),
            from_borg_id VARCHAR(100),
            to_borg_id VARCHAR(100),
            currency VARCHAR(10) NOT NULL CHECK (currency IN ('WND', 'USDB')),
            amount_wei BIGINT NOT NULL,
            transaction_hash VARCHAR(100),
            block_number BIGINT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            confirmed_at TIMESTAMP WITH TIME ZONE
        );
        """

        tables = [
            ("borg_addresses_new", borg_addresses_sql),
            ("borg_balances_new", borg_balances_sql),
            ("transfer_transactions_new", transfer_transactions_sql)
        ]

        for table_name, sql in tables:
            try:
                self.supabase.rpc('exec_sql', {'sql': sql})
                self.log(f"✅ Created table {table_name}")
            except Exception as e:
                self.log(f"❌ Failed to create {table_name}: {str(e)}", {'error': str(e)})
                return False

        return True

    def migrate_borg_addresses_data(self) -> bool:
        """Migrate existing borg_addresses data to new schema."""
        self.log("Migrating borg_addresses data")

        try:
            # Get all existing borg addresses
            result = self.supabase.table('borg_addresses').select('*').execute()

            if not result.data:
                self.log("No existing borg_addresses data to migrate")
                return True

            migrated_count = 0
            for record in result.data:
                try:
                    # Transform record for new schema
                    new_record = {
                        'substrate_address': record['substrate_address'],
                        'borg_id': record['borg_id'],
                        'dna_hash': record['dna_hash'],
                        'keypair_encrypted': record.get('keypair_encrypted', ''),
                        'creator_public_key': record.get('creator_public_key'),
                        'creator_signature': record.get('creator_signature'),
                        'anchoring_tx_hash': record.get('anchoring_tx_hash'),
                        'anchoring_status': record.get('anchoring_status', 'pending'),
                        'keyring_service_name': record.get('keyring_service_name'),
                        'setup_version': '4.1',
                        'storage_method': 'macos_keychain_address_primary',
                        'created_at': record.get('created_at', datetime.utcnow().isoformat()),
                        'last_sync': datetime.utcnow().isoformat()
                    }

                    # Insert into new table
                    self.supabase.table('borg_addresses_new').upsert(
                        new_record,
                        on_conflict='substrate_address'
                    ).execute()

                    migrated_count += 1

                except Exception as e:
                    self.log(f"❌ Failed to migrate borg {record.get('borg_id')}: {str(e)}",
                           {'borg_id': record.get('borg_id'), 'error': str(e)})
                    return False

            self.log(f"✅ Migrated {migrated_count} borg addresses")
            return True

        except Exception as e:
            self.log(f"❌ Failed to migrate borg_addresses data: {str(e)}", {'error': str(e)})
            return False

    def migrate_borg_balances_data(self) -> bool:
        """Migrate existing borg_balances data to new schema."""
        self.log("Migrating borg_balances data")

        try:
            # Get all existing balances
            result = self.supabase.table('borg_balances').select('*').execute()

            if not result.data:
                self.log("No existing borg_balances data to migrate")
                return True

            migrated_count = 0
            for record in result.data:
                try:
                    # Get address for this borg_id
                    borg_result = self.supabase.table('borg_addresses').select('substrate_address').eq('borg_id', record['borg_id']).execute()

                    if not borg_result.data:
                        self.log(f"⚠️  No address found for borg_id {record['borg_id']}, skipping balance migration")
                        continue

                    address = borg_result.data[0]['substrate_address']

                    # Transform record for new schema
                    new_record = {
                        'substrate_address': address,
                        'currency': record['currency'],
                        'balance_wei': record['balance_wei'],
                        'last_updated': record.get('last_updated', datetime.utcnow().isoformat())
                    }

                    # Insert into new table
                    self.supabase.table('borg_balances_new').upsert(
                        new_record,
                        on_conflict='substrate_address,currency'
                    ).execute()

                    migrated_count += 1

                except Exception as e:
                    self.log(f"❌ Failed to migrate balance for {record.get('borg_id')}: {str(e)}",
                           {'borg_id': record.get('borg_id'), 'error': str(e)})
                    return False

            self.log(f"✅ Migrated {migrated_count} balance records")
            return True

        except Exception as e:
            self.log(f"❌ Failed to migrate borg_balances data: {str(e)}", {'error': str(e)})
            return False

    def migrate_transfer_transactions_data(self) -> bool:
        """Migrate existing transfer_transactions data to new schema."""
        self.log("Migrating transfer_transactions data")

        try:
            # Check if transfer_transactions table exists and has data
            try:
                result = self.supabase.table('transfer_transactions').select('*').limit(1).execute()
            except Exception:
                self.log("transfer_transactions table does not exist or is empty, skipping")
                return True

            if not result.data:
                self.log("No transfer_transactions data to migrate")
                return True

            # Get all transfer transactions
            all_result = self.supabase.table('transfer_transactions').select('*').execute()

            migrated_count = 0
            for record in all_result.data:
                try:
                    # Get addresses for borg_ids
                    from_address = None
                    to_address = None

                    if record.get('from_borg_id'):
                        from_result = self.supabase.table('borg_addresses').select('substrate_address').eq('borg_id', record['from_borg_id']).execute()
                        if from_result.data:
                            from_address = from_result.data[0]['substrate_address']

                    if record.get('to_borg_id'):
                        to_result = self.supabase.table('borg_addresses').select('substrate_address').eq('borg_id', record['to_borg_id']).execute()
                        if to_result.data:
                            to_address = to_result.data[0]['substrate_address']

                    # Transform record for new schema
                    new_record = {
                        'tx_id': record['tx_id'],
                        'from_address': from_address,
                        'to_address': to_address,
                        'from_borg_id': record.get('from_borg_id'),
                        'to_borg_id': record.get('to_borg_id'),
                        'currency': record['currency'],
                        'amount_wei': record['amount_wei'],
                        'transaction_hash': record.get('transaction_hash'),
                        'block_number': record.get('block_number'),
                        'status': record.get('status', 'pending'),
                        'created_at': record.get('created_at', datetime.utcnow().isoformat()),
                        'confirmed_at': record.get('confirmed_at')
                    }

                    # Insert into new table
                    self.supabase.table('transfer_transactions_new').upsert(
                        new_record,
                        on_conflict='tx_id'
                    ).execute()

                    migrated_count += 1

                except Exception as e:
                    self.log(f"❌ Failed to migrate transaction {record.get('tx_id')}: {str(e)}",
                           {'tx_id': record.get('tx_id'), 'error': str(e)})
                    return False

            self.log(f"✅ Migrated {migrated_count} transfer transactions")
            return True

        except Exception as e:
            self.log(f"❌ Failed to migrate transfer_transactions data: {str(e)}", {'error': str(e)})
            return False

    def create_indexes(self) -> bool:
        """Create performance indexes for new tables."""
        self.log("Creating performance indexes")

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_borg_addresses_new_borg_id ON borg_addresses_new(borg_id);",
            "CREATE INDEX IF NOT EXISTS idx_borg_balances_new_address_currency ON borg_balances_new(substrate_address, currency);",
            "CREATE INDEX IF NOT EXISTS idx_transfer_transactions_new_addresses ON transfer_transactions_new(from_address, to_address);",
            "CREATE INDEX IF NOT EXISTS idx_transfer_transactions_new_status ON transfer_transactions_new(status);",
            "CREATE INDEX IF NOT EXISTS idx_transfer_transactions_new_created ON transfer_transactions_new(created_at DESC);"
        ]

        for sql in indexes:
            try:
                self.supabase.rpc('exec_sql', {'sql': sql})
                self.log("✅ Created index")
            except Exception as e:
                self.log(f"❌ Failed to create index: {str(e)}", {'sql': sql, 'error': str(e)})
                return False

        return True

    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        self.log("Validating migration integrity")

        try:
            # Check record counts
            old_addresses = self.supabase.table('borg_addresses').select('*', count='exact').execute()
            new_addresses = self.supabase.table('borg_addresses_new').select('*', count='exact').execute()

            old_balances = self.supabase.table('borg_balances').select('*', count='exact').execute()
            new_balances = self.supabase.table('borg_balances_new').select('*', count='exact').execute()

            validation = {
                'old_addresses_count': len(old_addresses.data) if old_addresses.data else 0,
                'new_addresses_count': len(new_addresses.data) if new_addresses.data else 0,
                'old_balances_count': len(old_balances.data) if old_balances.data else 0,
                'new_balances_count': len(new_balances.data) if new_balances.data else 0,
                'addresses_match': len(old_addresses.data) == len(new_addresses.data) if old_addresses.data and new_addresses.data else False,
                'balances_match': len(old_balances.data) == len(new_balances.data) if old_balances.data and new_balances.data else False
            }

            self.log("Migration validation results", validation)

            if validation['addresses_match'] and validation['balances_match']:
                self.log("✅ Migration validation PASSED")
                return True
            else:
                self.log("❌ Migration validation FAILED - record counts don't match")
                return False

        except Exception as e:
            self.log(f"❌ Migration validation failed: {str(e)}", {'error': str(e)})
            return False

    def generate_rollback_script(self) -> str:
        """Generate rollback script for emergency recovery."""
        rollback_script = f"""#!/bin/bash
# Rollback Script for Address Primary Key Migration
# Generated: {datetime.utcnow().isoformat()}

set -e

echo "🚨 EMERGENCY ROLLBACK - Address Primary Key Migration"
echo "Generated: {datetime.utcnow().isoformat()}"
echo ""

# Drop new tables (this will remove migrated data)
echo "🗑️  Dropping new tables..."
psql "$DATABASE_URL" -c "DROP TABLE IF EXISTS transfer_transactions_new CASCADE;"
psql "$DATABASE_URL" -c "DROP TABLE IF EXISTS borg_balances_new CASCADE;"
psql "$DATABASE_URL" -c "DROP TABLE IF EXISTS borg_addresses_new CASCADE;"
echo "✅ New tables dropped"
echo ""

echo "🎉 Rollback completed. Original tables are intact."
echo "Note: Any new data created after migration will be lost."
"""

        return rollback_script

    def run_migration(self) -> bool:
        """Run the complete migration process."""
        print("🚀 ADDRESS PRIMARY KEY MIGRATION")
        print("=" * 50)
        print("Migrating database to use substrate_address as primary key")
        print("=" * 50)

        steps = [
            ("Create new tables", self.create_new_tables),
            ("Migrate borg_addresses data", self.migrate_borg_addresses_data),
            ("Migrate borg_balances data", self.migrate_borg_balances_data),
            ("Migrate transfer_transactions data", self.migrate_transfer_transactions_data),
            ("Create indexes", self.create_indexes),
            ("Validate migration", self.validate_migration)
        ]

        success = True
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                success = False
                break

        print("\n" + "=" * 50)
        if success:
            print("🎉 ADDRESS PRIMARY KEY MIGRATION COMPLETED!")
            print("\nNext steps:")
            print("1. Update application code to use new BorgAddressManagerAddressPrimary")
            print("2. Test all functionality with new schema")
            print("3. Switch over to new tables (rename or update code)")
            print("4. Remove old tables after validation")

            # Generate rollback script
            rollback_script = self.generate_rollback_script()
            with open('migration_rollback.sh', 'w') as f:
                f.write(rollback_script)
            os.chmod('migration_rollback.sh', 0o755)

            print(f"5. Rollback script saved: migration_rollback.sh")

        else:
            print("❌ ADDRESS PRIMARY KEY MIGRATION FAILED!")
            print("Check the errors above and retry after fixing issues.")

        # Save migration log
        with open('migration_log.json', 'w') as f:
            json.dump(self.migration_log, f, indent=2, default=str)

        print(f"Migration log saved: migration_log.json")

        return success


def main():
    """Run the migration."""
    try:
        migrator = AddressPrimaryKeyMigrator()
        success = migrator.run_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()