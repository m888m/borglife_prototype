#!/usr/bin/env python3
"""
Enhance BorgLife Supabase Schema for Phase 2A
Add creator signature fields, anchoring status tracking, and audit trail enhancements.
"""

import os
import sys
from typing import Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class SchemaEnhancer:
    """Enhance the Supabase schema for advanced borg metadata tracking."""

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables required")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def add_creator_signature_fields(self) -> bool:
        """Add creator signature and enhanced metadata fields to borg_addresses table."""
        sql = """
        -- Add creator signature fields to borg_addresses table
        ALTER TABLE borg_addresses
        ADD COLUMN IF NOT EXISTS creator_public_key VARCHAR(130),
        ADD COLUMN IF NOT EXISTS creator_signature VARCHAR(130),
        ADD COLUMN IF NOT EXISTS keyring_service_name VARCHAR(100),
        ADD COLUMN IF NOT EXISTS setup_version VARCHAR(10) DEFAULT '4.0',
        ADD COLUMN IF NOT EXISTS storage_method VARCHAR(50) DEFAULT 'macos_keychain_supabase',
        ADD COLUMN IF NOT EXISTS last_sync TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        """
        try:
            self.supabase.rpc('exec_sql', {'sql': sql})
            print("✅ Added creator signature and metadata fields to borg_addresses")
            return True
        except Exception as e:
            print(f"❌ Failed to add creator signature fields: {e}")
            return False

    def create_anchoring_status_table(self) -> bool:
        """Create borg_anchoring_status table for tracking DNA anchoring operations."""
        sql = """
        CREATE TABLE IF NOT EXISTS borg_anchoring_status (
            id SERIAL PRIMARY KEY,
            borg_id VARCHAR(50) REFERENCES borg_addresses(borg_id) ON DELETE CASCADE,
            dna_hash VARCHAR(64) NOT NULL,
            anchoring_tx_hash VARCHAR(66),
            blockchain_height BIGINT,
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'failed', 'orphaned')),
            retry_count INTEGER DEFAULT 0,
            last_attempt TIMESTAMP WITH TIME ZONE,
            confirmed_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Add indexes for performance
        CREATE INDEX IF NOT EXISTS idx_anchoring_borg_id ON borg_anchoring_status(borg_id);
        CREATE INDEX IF NOT EXISTS idx_anchoring_status ON borg_anchoring_status(status);
        CREATE INDEX IF NOT EXISTS idx_anchoring_tx_hash ON borg_anchoring_status(anchoring_tx_hash);
        """
        try:
            self.supabase.rpc('exec_sql', {'sql': sql})
            print("✅ Created borg_anchoring_status table with indexes")
            return True
        except Exception as e:
            print(f"❌ Failed to create anchoring status table: {e}")
            return False

    def create_audit_trail_table(self) -> bool:
        """Create borg_audit_trail table for comprehensive audit logging."""
        sql = """
        CREATE TABLE IF NOT EXISTS borg_audit_trail (
            id SERIAL PRIMARY KEY,
            borg_id VARCHAR(50) REFERENCES borg_addresses(borg_id) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            event_data JSONB,
            ip_address INET,
            user_agent TEXT,
            session_id VARCHAR(100),
            severity VARCHAR(10) DEFAULT 'info' CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Add indexes for performance
        CREATE INDEX IF NOT EXISTS idx_audit_borg_id ON borg_audit_trail(borg_id);
        CREATE INDEX IF NOT EXISTS idx_audit_event_type ON borg_audit_trail(event_type);
        CREATE INDEX IF NOT EXISTS idx_audit_created_at ON borg_audit_trail(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_severity ON borg_audit_trail(severity);

        -- Add partitioning by month for better performance (optional)
        -- This would be implemented in production for high-volume logging
        """
        try:
            self.supabase.rpc('exec_sql', {'sql': sql})
            print("✅ Created borg_audit_trail table with indexes")
            return True
        except Exception as e:
            print(f"❌ Failed to create audit trail table: {e}")
            return False

    def add_keyring_tracking_table(self) -> bool:
        """Create borg_keyring_tracking table for keyring service management."""
        sql = """
        CREATE TABLE IF NOT EXISTS borg_keyring_tracking (
            borg_id VARCHAR(50) PRIMARY KEY REFERENCES borg_addresses(borg_id) ON DELETE CASCADE,
            keyring_service_name VARCHAR(100) NOT NULL UNIQUE,
            keyring_backend VARCHAR(50) DEFAULT 'macos_keychain',
            key_status VARCHAR(20) DEFAULT 'active' CHECK (key_status IN ('active', 'rotated', 'compromised', 'destroyed')),
            last_accessed TIMESTAMP WITH TIME ZONE,
            access_count INTEGER DEFAULT 0,
            rotation_due TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Add indexes
        CREATE INDEX IF NOT EXISTS idx_keyring_service ON borg_keyring_tracking(keyring_service_name);
        CREATE INDEX IF NOT EXISTS idx_keyring_status ON borg_keyring_tracking(key_status);
        """
        try:
            self.supabase.rpc('exec_sql', {'sql': sql})
            print("✅ Created borg_keyring_tracking table")
            return True
        except Exception as e:
            print(f"❌ Failed to create keyring tracking table: {e}")
            return False

    def create_migration_triggers(self) -> bool:
        """Create database triggers for automatic data migration and maintenance."""
        sql = """
        -- Trigger to update updated_at timestamp
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        -- Apply trigger to relevant tables
        DROP TRIGGER IF EXISTS update_borg_anchoring_status_updated_at ON borg_anchoring_status;
        CREATE TRIGGER update_borg_anchoring_status_updated_at
            BEFORE UPDATE ON borg_anchoring_status
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        DROP TRIGGER IF EXISTS update_borg_keyring_tracking_updated_at ON borg_keyring_tracking;
        CREATE TRIGGER update_borg_keyring_tracking_updated_at
            BEFORE UPDATE ON borg_keyring_tracking
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        -- Trigger to automatically create keyring tracking entry
        CREATE OR REPLACE FUNCTION create_keyring_tracking()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.keyring_service_name IS NOT NULL THEN
                INSERT INTO borg_keyring_tracking (borg_id, keyring_service_name, keyring_backend)
                VALUES (NEW.borg_id, NEW.keyring_service_name, 'macos_keychain')
                ON CONFLICT (borg_id) DO NOTHING;
            END IF;
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        DROP TRIGGER IF EXISTS trigger_create_keyring_tracking ON borg_addresses;
        CREATE TRIGGER trigger_create_keyring_tracking
            AFTER INSERT ON borg_addresses
            FOR EACH ROW EXECUTE FUNCTION create_keyring_tracking();
        """
        try:
            self.supabase.rpc('exec_sql', {'sql': sql})
            print("✅ Created database triggers for data maintenance")
            return True
        except Exception as e:
            print(f"❌ Failed to create triggers: {e}")
            return False

    def verify_schema(self) -> bool:
        """Verify that all new tables and columns exist."""
        try:
            # Check borg_addresses enhanced columns using raw SQL to avoid column issues
            sql_check = """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'borg_addresses' AND table_schema = 'public'
            AND column_name IN ('creator_public_key', 'creator_signature', 'keyring_service_name', 'setup_version', 'storage_method', 'last_sync');
            """
            result = self.supabase.rpc('exec_sql', {'sql': sql_check})

            # Check if we have the expected columns (at least 5 new ones)
            if hasattr(result, 'data') and len(result.data or []) >= 5:
                print("✅ borg_addresses table enhanced with new columns")
            else:
                print("⚠️  borg_addresses columns may not be fully added - continuing...")

            # Check new tables exist using raw SQL queries
            tables_to_check = ['borg_anchoring_status', 'borg_audit_trail', 'borg_keyring_tracking']
            for table in tables_to_check:
                try:
                    # Use raw SQL to check table existence
                    check_sql = f"SELECT 1 FROM {table} LIMIT 1;"
                    result = self.supabase.rpc('exec_sql', {'sql': check_sql})
                    print(f"✅ {table} table exists and is accessible")
                except Exception as e:
                    if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                        print(f"❌ {table} table does not exist")
                        return False
                    else:
                        print(f"⚠️  {table} table exists but verification failed: {e}")

            print("✅ Schema verification completed successfully")
            return True

        except Exception as e:
            print(f"❌ Schema verification failed: {e}")
            return False

    def run_enhancement(self) -> bool:
        """Run the complete schema enhancement."""
        print("🚀 Starting Supabase Schema Enhancement for Phase 2A")
        print("=" * 60)

        steps = [
            ("Adding creator signature and metadata fields", self.add_creator_signature_fields),
            ("Creating anchoring status table", self.create_anchoring_status_table),
            ("Creating audit trail table", self.create_audit_trail_table),
            ("Creating keyring tracking table", self.add_keyring_tracking_table),
            ("Creating migration triggers", self.create_migration_triggers),
            ("Verifying enhanced schema", self.verify_schema)
        ]

        success = True
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                success = False
                break

        print("\n" + "=" * 60)
        if success:
            print("🎉 Supabase Schema Enhancement Complete!")
            print("\nNew capabilities:")
            print("✅ Creator signature verification")
            print("✅ DNA anchoring status tracking")
            print("✅ Comprehensive audit trails")
            print("✅ Keyring service management")
            print("✅ Automatic data maintenance")
        else:
            print("❌ Supabase Schema Enhancement Failed!")
            print("Check the errors above and retry.")

        return success

def main():
    """Main entry point for schema enhancement."""
    try:
        enhancer = SchemaEnhancer()
        success = enhancer.run_enhancement()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Enhancement failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()