#!/usr/bin/env python3
"""
Live Westend End-to-End Test
Complete live blockchain testing with real WND transfers.
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from security.secure_dispenser import SecureDispenser
from jam_mock.borg_address_manager import BorgAddressManager
from jam_mock.kusama_adapter import WestendAdapter
from synthesis.dna_parser import DNAParser
# from synthesis.phenotype_builder import PhenotypeBuilder  # Skip for live test


class LiveWestendTester:
    """Live Westend end-to-end testing with real blockchain operations."""

    def __init__(self):
        self.dispenser = None
        self.address_manager = None
        self.westend_adapter = None
        self.test_results = {
            'borg_creation': None,
            'dispenser_funding': None,
            'inter_borg_transfer': None,
            'final_balances': None,
            'overall_success': False
        }

    async def initialize_components(self) -> bool:
        """Initialize all testing components."""
        print("🚀 INITIALIZING LIVE WESTEND TEST COMPONENTS")
        print("=" * 60)

        try:
            # Initialize dispenser
            print("\n🔐 Initializing dispenser...")
            self.dispenser = SecureDispenser()
            if not self.dispenser.unlock_for_session():
                print("❌ Failed to unlock dispenser")
                return False
            print("✅ Dispenser unlocked")

            # Initialize address manager
            print("\n📋 Initializing address manager...")
            self.address_manager = BorgAddressManager(supabase_client=None)  # No Supabase for live test
            print("✅ Address manager initialized")

            # Initialize Westend adapter
            print("\n🌐 Initializing Westend adapter...")
            self.westend_adapter = WestendAdapter("wss://westend.api.onfinality.io/public-ws")
            print("✅ Westend adapter initialized")

            return True

        except Exception as e:
            print(f"❌ Component initialization failed: {e}")
            return False

    async def create_test_borg(self, borg_id: str) -> Optional[str]:
        """Create a test borg with DNA and register address."""
        try:
            print(f"\n🧬 Creating test borg: {borg_id}")

            # Generate test DNA (simplified for live test)
            dna_parser = DNAParser()
            # phenotype_builder = PhenotypeBuilder()  # Skip for live test

            # Create simple test DNA
            test_dna = {
                'sequence': 'ATCG' * 16,  # 64 characters
                'metadata': {
                    'test_borg': True,
                    'created_at': datetime.utcnow().isoformat(),
                    'purpose': 'live_westend_test'
                }
            }

            # Parse and validate DNA (simplified for live test)
            dna_hash = dna_parser.parse_dna(test_dna)
            print(f"   DNA Hash: {dna_hash}")

            # Register borg address (simplified for live test - no Supabase)
            # Generate deterministic keypair directly
            from substrateinterface import Keypair
            keypair = Keypair.create_from_seed(dna_hash[:64])  # Use DNA hash as seed

            result = {
                'success': True,
                'borg_id': borg_id,
                'address': keypair.ss58_address,
                'dna_hash': dna_hash
            }

            if result.get('success'):
                address = result['address']
                print(f"✅ Borg {borg_id} created with address: {address}")
                return address
            else:
                print(f"❌ Borg creation failed: {result.get('error')}")
                return None

        except Exception as e:
            print(f"❌ Borg creation error: {e}")
            return None

    async def fund_borg_from_dispenser(self, borg_address: str, borg_id: str, amount_wnd: float) -> bool:
        """Fund a borg address with WND from the dispenser."""
        try:
            print(f"\n💸 Funding borg {borg_id} with {amount_wnd} WND from dispenser")

            # Convert WND to planck
            amount_planck = int(amount_wnd * (10 ** 12))

            # Execute transfer
            result = await self.dispenser.transfer_usdb_to_borg(
                borg_address=borg_address,
                borg_id=borg_id,
                amount_usdb=amount_wnd  # Note: using USDB method but with WND amount
            )

            if result.get('success'):
                print("✅ Dispenser funding successful!")
                print(f"   Transaction: {result.get('transaction_hash')}")
                print(f"   Block: {result.get('block_number')}")
                return True
            else:
                print(f"❌ Dispenser funding failed: {result.get('error')}")
                return False

        except Exception as e:
            print(f"❌ Dispenser funding error: {e}")
            return False

    async def transfer_between_borgs(self, from_address: str, to_address: str, from_id: str, to_id: str, amount_wnd: float) -> bool:
        """Transfer WND between two borg addresses."""
        try:
            print(f"\n🔄 Transferring {amount_wnd} WND from {from_id} to {to_id}")

            # Get keypair for the sender borg
            from_keypair = self.address_manager.get_borg_keypair(from_id)
            if not from_keypair:
                print(f"❌ Could not retrieve keypair for {from_id}")
                return False

            # Execute transfer using Westend adapter
            amount_planck = int(amount_wnd * (10 ** 12))

            transfer_result = await self.westend_adapter.transfer_usdb(
                from_address=from_address,
                to_address=to_address,
                amount=amount_planck,
                asset_id=0  # WND asset ID is 0
            )

            if transfer_result.get('success'):
                print("✅ Inter-borg transfer successful!")
                print(f"   Transaction: {transfer_result.get('transaction_hash')}")
                print(f"   Block: {transfer_result.get('block_number')}")
                return True
            else:
                print(f"❌ Inter-borg transfer failed: {transfer_result.get('error')}")
                return False

        except Exception as e:
            print(f"❌ Inter-borg transfer error: {e}")
            return False

    async def check_balance(self, address: str, label: str) -> Optional[float]:
        """Check WND balance for an address."""
        try:
            balance_planck = await self.westend_adapter.get_wnd_balance(address)
            balance_wnd = balance_planck / (10 ** 12)
            print(f"   {label} Balance: {balance_wnd:.6f} WND ({balance_planck:,} planck)")
            return balance_wnd
        except Exception as e:
            print(f"❌ Balance check failed for {label}: {e}")
            return None

    async def run_live_test(self) -> Dict[str, Any]:
        """Run the complete live Westend test."""
        print("🎯 LIVE WESTEND END-TO-END TEST")
        print("=" * 60)

        # Initialize components
        if not await self.initialize_components():
            self.test_results['error'] = 'Component initialization failed'
            return self.test_results

        try:
            # Step 1: Create first test borg
            print("\n📋 STEP 1: Create Borg A")
            borg_a_id = f"live_test_borg_{int(datetime.utcnow().timestamp())}"
            borg_a_address = await self.create_test_borg(borg_a_id)

            if not borg_a_address:
                self.test_results['error'] = 'Borg A creation failed'
                return self.test_results

            self.test_results['borg_creation'] = {
                'borg_a': {'id': borg_a_id, 'address': borg_a_address}
            }

            # Step 2: Fund Borg A with 2 WND from dispenser
            print("\n📋 STEP 2: Fund Borg A with 2 WND")
            funding_success = await self.fund_borg_from_dispenser(
                borg_address=borg_a_address,
                borg_id=borg_a_id,
                amount_wnd=2.0
            )

            if not funding_success:
                self.test_results['error'] = 'Borg A funding failed'
                return self.test_results

            self.test_results['dispenser_funding'] = {
                'borg_a_funded': True,
                'amount_wnd': 2.0
            }

            # Wait for transaction confirmation
            print("\n⏳ Waiting for transaction confirmation...")
            await asyncio.sleep(12)  # Wait for block finalization

            # Check Borg A balance
            print("\n📊 Checking Borg A balance after funding")
            borg_a_balance = await self.check_balance(borg_a_address, "Borg A")

            # Step 3: Create Borg B or use existing
            print("\n📋 STEP 3: Create Borg B")
            borg_b_id = f"live_test_borg_{int(datetime.utcnow().timestamp()) + 1}"
            borg_b_address = await self.create_test_borg(borg_b_id)

            if not borg_b_address:
                print("⚠️  Borg B creation failed, trying to find existing borg...")
                # Try to find an existing borg
                existing_borgs = self.address_manager.list_registered_borgs()
                if existing_borgs:
                    borg_b_record = existing_borgs[0]  # Use first available
                    borg_b_id = borg_b_record['borg_id']
                    borg_b_address = borg_b_record['substrate_address']
                    print(f"✅ Using existing borg: {borg_b_id}")
                else:
                    self.test_results['error'] = 'Could not create or find Borg B'
                    return self.test_results

            self.test_results['borg_creation']['borg_b'] = {'id': borg_b_id, 'address': borg_b_address}

            # Check Borg B initial balance
            print("\n📊 Checking Borg B initial balance")
            borg_b_initial_balance = await self.check_balance(borg_b_address, "Borg B Initial")

            # Step 4: Transfer 0.7 WND from Borg A to Borg B
            print("\n📋 STEP 4: Transfer 0.7 WND from Borg A to Borg B")
            transfer_success = await self.transfer_between_borgs(
                from_address=borg_a_address,
                to_address=borg_b_address,
                from_id=borg_a_id,
                to_id=borg_b_id,
                amount_wnd=0.7
            )

            if not transfer_success:
                self.test_results['error'] = 'Inter-borg transfer failed'
                return self.test_results

            self.test_results['inter_borg_transfer'] = {
                'from_borg': borg_a_id,
                'to_borg': borg_b_id,
                'amount_wnd': 0.7,
                'success': True
            }

            # Wait for transaction confirmation
            print("\n⏳ Waiting for transfer confirmation...")
            await asyncio.sleep(12)

            # Step 5: Check final balances
            print("\n📋 STEP 5: Check Final Balances")
            final_borg_a_balance = await self.check_balance(borg_a_address, "Borg A Final")
            final_borg_b_balance = await self.check_balance(borg_b_address, "Borg B Final")

            self.test_results['final_balances'] = {
                'borg_a': {
                    'id': borg_a_id,
                    'address': borg_a_address,
                    'initial_balance': borg_a_balance,
                    'final_balance': final_borg_a_balance
                },
                'borg_b': {
                    'id': borg_b_id,
                    'address': borg_b_address,
                    'initial_balance': borg_b_initial_balance,
                    'final_balance': final_borg_b_balance
                }
            }

            # Validate results
            if (borg_a_balance and final_borg_a_balance and final_borg_b_balance is not None and
                abs((borg_a_balance - 0.7) - final_borg_a_balance) < 0.001 and
                final_borg_b_balance >= (borg_b_initial_balance or 0) + 0.7 - 0.001):

                self.test_results['overall_success'] = True
                print("\n🎉 ALL TESTS PASSED!")
                print("✅ Borg creation: SUCCESS")
                print("✅ Dispenser funding: SUCCESS")
                print("✅ Inter-borg transfer: SUCCESS")
                print("✅ Balance validation: SUCCESS")

            else:
                print("\n⚠️  Balance validation inconclusive - manual verification needed")

            return self.test_results

        except Exception as e:
            print(f"\n❌ Test execution failed: {e}")
            self.test_results['error'] = str(e)
            return self.test_results

        finally:
            # Cleanup
            if self.dispenser:
                self.dispenser.lock_session()


async def main():
    """Main test execution."""
    tester = LiveWestendTester()
    results = await tester.run_live_test()

    # Save results
    with open('live_westend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Results saved to live_westend_test_results.json")

    # Exit with appropriate code
    success = results.get('overall_success', False)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())