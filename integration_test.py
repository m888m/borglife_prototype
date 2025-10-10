#!/usr/bin/env python3
"""
End-to-End Integration and Validation for Borglife Phase 1 Prototype

Demo loop: Funding → Execution → Encoding → Storage → Decoding
Comprehensive testing for autonomy and hybrid architecture.
"""

import pytest
from decimal import Decimal
from dna_system import DNAMapper, BorgPhenotype
from on_chain import KusamaStorage, BorgWealthManager
from proto_borg import ProtoBorgAgent, BorgConfig

class TestBorglifeIntegration:
    """Integration tests for Borglife prototype."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mapper = DNAMapper()
        self.storage = KusamaStorage()
        self.config = BorgConfig(
            name="TestBorg",
            wallet_address="test_address",
            mock_costs=True
        )
        self.borg = ProtoBorgAgent(self.config)
        self.wealth_manager = BorgWealthManager(self.storage, "test_address")

    def test_dna_round_trip(self):
        """Test DNA encoding/decoding round-trip integrity."""
        phenotype = BorgPhenotype(
            name="TestBorg",
            config={"service_index": 1},
            cells=[{"name": "test_cell", "logic": "test"}],
            organs=[{"url": "http://test", "price": 0.01}],
            manifesto_hash=self.mapper.manifesto_hash
        )

        assert self.mapper.round_trip_check(phenotype), "Round-trip integrity failed"

    def test_wealth_management(self):
        """Test wealth tracking and transactions."""
        # Receive sponsorship
        success = self.borg.receive_sponsorship(Decimal('1.0'), "DOT")
        assert success, "Sponsorship failed"

        # Check wealth
        wealth = self.borg.check_balance()
        assert Decimal(wealth["dot_balance"]) == Decimal('1.0'), "Wealth not updated"

        # Execute task (mock cost)
        result = self.borg.execute_task("Test task")
        assert result, "Task execution failed"

        # Check net wealth
        wealth_after = self.borg.check_balance()
        assert Decimal(wealth_after["net_wealth"]) == Decimal('0.999'), "Net wealth incorrect"

    def test_on_chain_storage(self):
        """Test DNA storage and retrieval."""
        dna_yaml = "test: dna"
        dna_hash = self.storage.store_dna_hash(dna_yaml, "test_address")
        assert dna_hash, "DNA hash storage failed"

        retrieved = self.storage.retrieve_dna_hash("test_address")
        assert retrieved, "DNA hash retrieval failed"

    def test_jam_mock_phases(self):
        """Test mock JAM phases."""
        operations = ["op1", "op2"]
        results = self.storage.jam_mock.refine_phase(operations)
        assert len(results) == 2, "Refine phase failed"

        state = self.storage.jam_mock.accumulate_phase(results)
        assert state["transactions"] == 2, "Accumulate phase failed"

    def test_end_to_end_demo(self):
        """Full end-to-end demo loop."""
        # 1. Create phenotype
        phenotype = BorgPhenotype(
            name="DemoBorg",
            config={"service_index": 1},
            cells=[{"name": "processor", "logic": "summarize"}],
            organs=[{"url": "http://localhost:8051", "price": 0.01}],
            manifesto_hash=self.mapper.manifesto_hash
        )

        # 2. Encode DNA
        dna_yaml = self.mapper.encode_to_yaml(phenotype)

        # 3. Store on-chain
        dna_hash = self.storage.store_dna_hash(dna_yaml, "demo_address")

        # 4. Receive sponsorship
        self.borg.receive_sponsorship(Decimal('1.0'), "DOT")

        # 5. Execute task
        result = self.borg.execute_task("Summarize: Borglife is a decentralized platform...")

        # 6. Decode DNA
        decoded = self.mapper.decode_from_yaml(dna_yaml)

        # Assertions
        assert dna_hash, "DNA storage failed"
        assert result, "Task execution failed"
        assert decoded.name == phenotype.name, "DNA decoding failed"
        assert self.borg.wealth.net_wealth() == Decimal('0.999'), "Wealth calculation failed"

        print("✅ End-to-end demo completed successfully!")

def run_demo():
    """Run the demo loop manually."""
    print("🚀 Starting Borglife Phase 1 Demo")

    # Initialize components
    mapper = DNAMapper()
    storage = KusamaStorage()
    config = BorgConfig(
        name="DemoBorg",
        wallet_address="demo_wallet_address",
        mock_costs=True
    )
    borg = ProtoBorgAgent(config)

    # Demo steps
    print("1. Creating borg phenotype...")
    phenotype = BorgPhenotype(
        name="DemoBorg",
        config={"service_index": 1},
        cells=[{"name": "data_processor", "logic": "summarize_text"}],
        organs=[{"url": "http://localhost:8051", "price": 0.01}],
        manifesto_hash=mapper.manifesto_hash
    )

    print("2. Encoding DNA...")
    dna_yaml = mapper.encode_to_yaml(phenotype)
    print(f"DNA length: {len(dna_yaml)} chars")

    print("3. Storing DNA on-chain...")
    dna_hash = storage.store_dna_hash(dna_yaml, config.wallet_address)
    print(f"DNA hash: {dna_hash}")

    print("4. Receiving sponsorship...")
    borg.receive_sponsorship(Decimal('1.0'), "DOT")

    print("5. Executing task...")
    result = borg.execute_task("Summarize the key benefits of decentralized AI.")
    print(f"Task result: {result}")

    print("6. Checking wealth...")
    wealth = borg.check_balance()
    print(f"Final wealth: {wealth}")

    print("✅ Demo completed! Borg autonomy demonstrated.")

if __name__ == "__main__":
    # Run demo
    run_demo()

    # Run tests
    print("\n🧪 Running integration tests...")
    test_instance = TestBorglifeIntegration()
    test_instance.setup_method()

    try:
        test_instance.test_dna_round_trip()
        print("✅ DNA round-trip test passed")

        test_instance.test_wealth_management()
        print("✅ Wealth management test passed")

        test_instance.test_on_chain_storage()
        print("✅ On-chain storage test passed")

        test_instance.test_jam_mock_phases()
        print("✅ JAM mock phases test passed")

        test_instance.test_end_to_end_demo()
        print("✅ End-to-end demo test passed")

        print("\n🎉 All tests passed! Borglife Phase 1 prototype is ready.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise