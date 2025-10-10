"""
Archon Integration Tests

Tests the complete integration between BorgLife and Archon services.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from archon_adapter import ArchonServiceAdapter, ArchonConfig
from synthesis import DNAParser, PhenotypeBuilder, BorgDNA
from jam_mock import LocalJAMMock


class TestArchonIntegration:
    """Test Archon service integration."""

    @pytest.fixture
    async def archon_adapter(self):
        """Create mock Archon adapter for testing."""
        config = ArchonConfig()
        adapter = ArchonServiceAdapter(config)

        # Mock the session and HTTP calls
        adapter.session = AsyncMock()
        adapter._make_request = AsyncMock()

        yield adapter

        await adapter.close()

    @pytest.mark.asyncio
    async def test_archon_health_check(self, archon_adapter):
        """Test Archon service health checks."""
        # Mock successful health responses
        archon_adapter._make_request.side_effect = [
            {"status": "healthy"},  # server
            {"status": "healthy"},  # mcp
            {"status": "healthy"}   # agents
        ]

        health = await archon_adapter.check_health()

        assert health['archon_server'] is True
        assert health['archon_mcp'] is True
        assert health['archon_agents'] is True
        assert health['status'] == 'healthy'

    @pytest.mark.asyncio
    async def test_rag_query_integration(self, archon_adapter):
        """Test RAG query through Archon adapter."""
        mock_response = {
            "results": [
                {"content": "BorgLife is an autonomous AI system", "score": 0.95}
            ]
        }
        archon_adapter._make_request.return_value = mock_response

        result = await archon_adapter.perform_rag_query("What is BorgLife?")

        assert 'results' in result
        assert len(result['results']) > 0
        archon_adapter._make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_tool_call(self, archon_adapter):
        """Test MCP tool invocation."""
        mock_response = {"result": "Task created successfully"}
        archon_adapter._make_request.return_value = mock_response

        result = await archon_adapter.call_mcp_tool("archon:create_task", {"title": "Test task"})

        assert result == "Task created successfully"

    @pytest.mark.asyncio
    async def test_agent_execution(self, archon_adapter):
        """Test PydanticAI agent execution."""
        mock_response = {"result": "Analysis complete", "cost": 0.001}
        archon_adapter._make_request.return_value = mock_response

        result = await archon_adapter.run_agent("RagAgent", "Analyze this text")

        assert result["result"] == "Analysis complete"
        assert result["cost"] == 0.001


class TestDNAIntegration:
    """Test DNA parsing and validation integration."""

    def test_dna_yaml_roundtrip(self):
        """Test DNA YAML parsing and serialization roundtrip."""
        # Create example DNA
        original_dna = DNAParser.create_example_dna()

        # Serialize to YAML
        yaml_str = DNAParser.to_yaml(original_dna)

        # Parse back from YAML
        parsed_dna = DNAParser.from_yaml(yaml_str)

        # Verify integrity
        assert original_dna.compute_hash() == parsed_dna.compute_hash()
        assert original_dna.header.service_index == parsed_dna.header.service_index
        assert len(original_dna.cells) == len(parsed_dna.cells)
        assert len(original_dna.organs) == len(parsed_dna.organs)

    def test_dna_validation(self):
        """Test DNA validation functionality."""
        # Valid DNA
        valid_dna = DNAParser.create_example_dna()
        issues = DNAParser.validate_dna(valid_dna)
        assert len(issues) == 0

        # Invalid DNA - missing manifesto hash
        invalid_dna = valid_dna.copy()
        invalid_dna.manifesto_hash = ""
        issues = DNAParser.validate_dna(invalid_dna)
        assert len(issues) > 0
        assert any("manifesto hash" in issue.lower() for issue in issues)

    def test_dna_integrity_verification(self):
        """Test DNA integrity verification."""
        dna = DNAParser.create_example_dna()
        expected_hash = dna.compute_hash()

        # Should verify against itself
        assert dna.verify_integrity()

        # Should verify against computed hash
        assert dna.verify_integrity(expected_hash)

        # Should fail against wrong hash
        assert not dna.verify_integrity("wrong_hash")


class TestPhenotypeIntegration:
    """Test phenotype building integration."""

    @pytest.fixture
    async def mock_archon_adapter(self):
        """Create mock Archon adapter for phenotype testing."""
        config = ArchonConfig()
        adapter = ArchonServiceAdapter(config)
        adapter.session = AsyncMock()

        # Mock agent execution
        adapter.run_agent = AsyncMock(return_value={
            "result": "Mock analysis result",
            "cost": 0.001
        })

        yield adapter
        await adapter.close()

    @pytest.mark.asyncio
    async def test_phenotype_building(self, mock_archon_adapter):
        """Test complete phenotype building from DNA."""
        # Create DNA
        dna = DNAParser.create_example_dna()

        # Create phenotype builder
        builder = PhenotypeBuilder(mock_archon_adapter)

        # Build phenotype
        phenotype = await builder.build(dna)

        # Verify phenotype structure
        assert len(phenotype.cells) == len(dna.cells)
        assert len(phenotype.organs) == len(dna.organs)
        assert phenotype.dna == dna
        assert phenotype.archon_adapter == mock_archon_adapter

        # Verify metadata
        assert phenotype.metadata['cell_count'] == len(dna.cells)
        assert phenotype.metadata['organ_count'] == len(dna.organs)
        assert phenotype.metadata['build_time'] is not None

    @pytest.mark.asyncio
    async def test_task_execution(self, mock_archon_adapter):
        """Test task execution through phenotype."""
        dna = DNAParser.create_example_dna()
        builder = PhenotypeBuilder(mock_archon_adapter)
        phenotype = await builder.build(dna)

        # Execute task
        result = await phenotype.execute_task("Analyze BorgLife mechanisms")

        # Verify result structure
        assert 'result' in result
        assert 'cell_used' in result
        assert 'cost' in result
        assert 'dna_hash' in result
        assert result['cell_used'] in phenotype.cells

    @pytest.mark.asyncio
    async def test_phenotype_validation(self, mock_archon_adapter):
        """Test phenotype validation during building."""
        dna = DNAParser.create_example_dna()
        builder = PhenotypeBuilder(mock_archon_adapter)

        # Should build successfully
        phenotype = await builder.build(dna)
        assert phenotype is not None

        # Test execution validation
        result = await phenotype.execute_task("Test validation")
        assert 'error' not in result or result.get('error') is None


class TestJAMIntegration:
    """Test JAM mock integration."""

    @pytest.fixture
    def jam_mock(self):
        """Create JAM mock for testing."""
        return LocalJAMMock()

    @pytest.mark.asyncio
    async def test_jam_dna_storage(self, jam_mock):
        """Test DNA hash storage in JAM."""
        borg_id = "test_borg"
        dna_hash = "abc123hash"

        result = await jam_mock.store_dna_hash(borg_id, dna_hash)

        assert result['success'] is True
        assert 'block' in result
        assert 'transaction_hash' in result
        assert result['cost'] > 0

        # Verify retrieval
        stored_hash = await jam_mock.retrieve_dna_hash(borg_id)
        assert stored_hash == dna_hash

    @pytest.mark.asyncio
    async def test_jam_wealth_tracking(self, jam_mock):
        """Test wealth tracking in JAM."""
        borg_id = "test_borg"

        # Initial balance should be 0
        balance = await jam_mock.get_wealth_balance(borg_id)
        assert balance == Decimal('0')

        # Add revenue
        success = await jam_mock.update_wealth(
            borg_id, Decimal('1.0'), 'revenue', 'Test funding'
        )
        assert success is True

        # Check balance
        balance = await jam_mock.get_wealth_balance(borg_id)
        assert balance == Decimal('1.0')

        # Add cost
        success = await jam_mock.update_wealth(
            borg_id, Decimal('0.1'), 'cost', 'Test execution'
        )
        assert success is True

        # Check final balance
        balance = await jam_mock.get_wealth_balance(borg_id)
        assert balance == Decimal('0.9')

    @pytest.mark.asyncio
    async def test_jam_integrity_verification(self, jam_mock):
        """Test DNA integrity verification through JAM."""
        borg_id = "test_borg"
        dna_hash = "integrity_test_hash"

        # Store hash
        await jam_mock.store_dna_hash(borg_id, dna_hash)

        # Verify integrity
        is_valid = await jam_mock.verify_dna_integrity(borg_id, dna_hash)
        assert is_valid is True

        # Verify against wrong hash
        is_valid = await jam_mock.verify_dna_integrity(borg_id, "wrong_hash")
        assert is_valid is False


class TestEndToEndDemo:
    """Test complete end-to-end demo scenarios."""

    @pytest.fixture
    async def demo_setup(self):
        """Setup complete demo environment."""
        # JAM mock
        jam = LocalJAMMock()

        # Mock Archon adapter
        config = ArchonConfig()
        archon = ArchonServiceAdapter(config)
        archon.session = AsyncMock()
        archon.run_agent = AsyncMock(return_value={
            "result": "Demo analysis complete",
            "cost": 0.001
        })

        # Phenotype builder
        builder = PhenotypeBuilder(archon)

        yield {
            'jam': jam,
            'archon': archon,
            'builder': builder
        }

        await archon.close()

    @pytest.mark.asyncio
    async def test_funding_execution_encoding_storage_decoding(self, demo_setup):
        """Test complete demo loop: funding → execution → encoding → storage → decoding."""
        jam = demo_setup['jam']
        archon = demo_setup['archon']
        builder = demo_setup['builder']

        borg_id = "demo_borg"

        # 1. FUNDING: Fund borg with DOT
        await jam.update_wealth(borg_id, Decimal('0.1'), 'revenue', 'Demo funding')
        balance = await jam.get_wealth_balance(borg_id)
        assert balance == Decimal('0.1')

        # 2. EXECUTION: Create and execute borg
        dna = DNAParser.create_example_dna(borg_id)
        phenotype = await builder.build(dna)
        result = await phenotype.execute_task("Analyze BorgLife whitepaper")

        assert 'result' in result
        assert result['cost'] > 0

        # 3. ENCODING: Serialize DNA to YAML
        dna_yaml = DNAParser.to_yaml(dna)
        assert isinstance(dna_yaml, str)
        assert 'header:' in dna_yaml

        # 4. STORAGE: Store DNA hash on-chain
        dna_hash = dna.compute_hash()
        store_result = await jam.store_dna_hash(borg_id, dna_hash)
        assert store_result['success'] is True

        # 5. DECODING: Retrieve and verify
        stored_hash = await jam.retrieve_dna_hash(borg_id)
        assert stored_hash == dna_hash

        # Round-trip verification
        decoded_dna = DNAParser.from_yaml(dna_yaml)
        assert decoded_dna.compute_hash() == dna_hash

        # Verify wealth tracking
        final_balance = await jam.get_wealth_balance(borg_id)
        assert final_balance < balance  # Cost was deducted

    @pytest.mark.asyncio
    async def test_multiple_borg_execution(self, demo_setup):
        """Test multiple borgs executing tasks simultaneously."""
        jam = demo_setup['jam']
        archon = demo_setup['archon']
        builder = demo_setup['builder']

        borg_ids = [f"borg_{i}" for i in range(3)]

        # Fund all borgs
        for borg_id in borg_ids:
            await jam.update_wealth(borg_id, Decimal('0.1'), 'revenue', f'Funding {borg_id}')

        # Create and execute tasks for each borg
        tasks = []
        for borg_id in borg_ids:
            dna = DNAParser.create_example_dna(borg_id)
            phenotype = await builder.build(dna)

            # Execute different tasks
            task = f"Analyze topic {borg_id}"
            tasks.append(phenotype.execute_task(task))

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Verify all executions succeeded
        assert len(results) == len(borg_ids)
        for result in results:
            assert 'result' in result
            assert 'error' not in result

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, demo_setup):
        """Test error handling and recovery in demo scenarios."""
        jam = demo_setup['jam']
        archon = demo_setup['archon']
        builder = demo_setup['builder']

        borg_id = "error_test_borg"

        # Fund borg
        await jam.update_wealth(borg_id, Decimal('0.1'), 'revenue', 'Error test funding')

        # Create phenotype
        dna = DNAParser.create_example_dna(borg_id)
        phenotype = await builder.build(dna)

        # Test with failing Archon service
        archon.run_agent = AsyncMock(side_effect=Exception("Service unavailable"))

        # Execution should handle error gracefully
        result = await phenotype.execute_task("Test error handling")

        # Should return error but not crash
        assert 'error' in result or result.get('error') is not None

        # Wealth should not be deducted for failed execution
        balance_after = await jam.get_wealth_balance(borg_id)
        initial_balance = Decimal('0.1')
        assert balance_after == initial_balance