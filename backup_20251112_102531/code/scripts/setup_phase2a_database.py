#!/usr/bin/env python3
"""
Setup Phase 2A Database Schema for BorgLife Fund Holding & Transfer System

Creates the required Supabase tables for dual-currency support:
- borg_addresses: Borg address and keypair management
- borg_balances: Dual-currency balance tracking (WND/USDB)
- transfer_transactions: Transfer transaction history

Run this script to set up the database schema for Phase 2A.
"""

import os
import sys
from typing import Dict, Any
import json
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env.borglife file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.borglife'))

# Add the code directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# from jam_mock.secure_key_storage import SecureKeyStorage  # Not needed for database setup

class Phase2ADatabaseSetup:
    """Setup Phase 2A database schema for fund holding and transfers."""

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        # Try service role key first, then fall back to secret key
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_SECRET_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SECRET_KEY) environment variables required")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def create_borg_addresses_table(self) -> bool:
        """Create borg_addresses table for address and keypair management."""
        sql = """
        CREATE TABLE IF NOT EXISTS borg_addresses (
            borg_id VARCHAR(100) PRIMARY KEY,
            substrate_address VARCHAR(100) NOT NULL UNIQUE,
            dna_hash VARCHAR(100) NOT NULL,
            keypair_encrypted TEXT NOT NULL,
            creator_public_key VARCHAR(100),
            creator_signature VARCHAR(200),
            anchoring_tx_hash VARCHAR(100),
            anchoring_status VARCHAR(20) DEFAULT 'pending',
            keyring_service_name VARCHAR(100),
            setup_version VARCHAR(10) DEFAULT '4.0',
            storage_method VARCHAR(50) DEFAULT 'macos_keychain_supabase',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_sync TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        try:
            self.supabase.rpc('exec_sql', {'sql': sql})
            print("✅ Created borg_addresses table")
            return True
        except Exception as e:
            print(f"❌ Failed to create borg_addresses table: {e}")
            return False

    def create_borg_balances_table(self) -> bool:
        """Create borg_balances table for dual-currency balance tracking."""
        sql = """
        CREATE TABLE IF NOT EXISTS borg_balances (
            borg_id VARCHAR(100) REFERENCES borg_addresses(borg_id),
            currency VARCHAR(10) NOT NULL CHECK (currency IN ('WND', 'USDB')),
            balance_wei BIGINT NOT NULL DEFAULT 0,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (borg_id, currency)
        );
        """
        try:
            self.supabase.rpc('exec_sql', {'sql': sql})
            print("✅ Created borg_balances table")
            return True
        except Exception as e:
            print(f"❌ Failed to create borg_balances table: {e}")
            return False

    def create_transfer_transactions_table(self) -> bool:
        """Create transfer_transactions table for transfer history."""
        sql = """
        CREATE TABLE IF NOT EXISTS transfer_transactions (
            tx_id VARCHAR(100) PRIMARY KEY,
            from_borg_id VARCHAR(100) REFERENCES borg_addresses(borg_id),
            to_borg_id VARCHAR(100) REFERENCES borg_addresses(borg_id),
            currency VARCHAR(10) NOT NULL CHECK (currency IN ('WND', 'USDB')),
            amount_wei BIGINT NOT NULL,
            transaction_hash VARCHAR(100),
            block_number BIGINT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            confirmed_at TIMESTAMP WITH TIME ZONE
        );
        """
        try:
            self.supabase.rpc('exec_sql', {'sql': sql})
            print("✅ Created transfer_transactions table")
            return True
        except Exception as e:
            print(f"❌ Failed to create transfer_transactions table: {e}")
            return False

    def create_indexes(self) -> bool:
        """Create performance indexes for the new tables."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_balances_borg_currency ON borg_balances(borg_id, currency);",
            "CREATE INDEX IF NOT EXISTS idx_transfers_status ON transfer_transactions(status);",
            "CREATE INDEX IF NOT EXISTS idx_transfers_created ON transfer_transactions(created_at DESC);"
        ]

        success = True
        for sql in indexes:
            try:
                self.supabase.rpc('exec_sql', {'sql': sql})
                print("✅ Created index")
            except Exception as e:
                print(f"❌ Failed to create index: {e}")
                success = False

        return success

    def verify_schema(self) -> bool:
        """Verify that all required tables exist by attempting to query them."""
        try:
            # Check tables exist by trying to query them
            tables_to_check = ['borg_addresses', 'borg_balances', 'transfer_transactions']

            for table in tables_to_check:
                try:
                    # Try to select from the table (will fail if table doesn't exist)
                    result = self.supabase.table(table).select('*').limit(1).execute()
                    print(f"✅ Table {table} exists and is accessible")
                except Exception as e:
                    if "Could not find the table" in str(e):
                        print(f"❌ Table {table} does not exist")
                        return False
                    else:
                        # Other errors (permissions, etc.) - table exists but we can't verify
                        print(f"⚠️  Table {table} exists but verification failed: {e}")

            print("✅ Schema verification completed")
            return True

        except Exception as e:
            print(f"❌ Schema verification failed: {e}")
            return False

    def run_setup(self) -> bool:
        """Run the complete Phase 2A database setup."""
        print("🚀 Starting Phase 2A Database Setup")
        print("=" * 50)

        steps = [
            ("Creating borg_addresses table", self.create_borg_addresses_table),
            ("Creating borg_balances table", self.create_borg_balances_table),
            ("Creating transfer_transactions table", self.create_transfer_transactions_table),
            ("Creating performance indexes", self.create_indexes),
            ("Verifying schema", self.verify_schema)
        ]

        success = True
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                success = False
                break

        print("\n" + "=" * 50)
        if success:
            print("🎉 Phase 2A Database Setup Complete!")
            print("\nNext steps:")
            print("1. Run migration scripts if needed")
            print("2. Proceed to USDB asset creation")
        else:
            print("❌ Phase 2A Database Setup Failed!")
            print("Check the errors above and retry.")

        return success

def main():
    """Main entry point for the setup script."""
    try:
        setup = Phase2ADatabaseSetup()
        success = setup.run_setup()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Setup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()