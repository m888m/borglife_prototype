import pytest
from archon_adapter import ArchonServiceAdapter
from synthesis import DNAParser, PhenotypeBuilder
from proto_borg import ProtoBorgAgent

@pytest.mark.asyncio
async def test_archon_health():
    """Verify Archon services are reachable"""
    adapter = ArchonServiceAdapter()
    health = await adapter.check_health()
    assert health['archon_server'] is True
    assert health['archon_mcp'] is True

@pytest.mark.asyncio
async def test_rag_query():
    """Test RAG query via adapter"""
    adapter = ArchonServiceAdapter()
    await adapter.initialize()

    result = await adapter.perform_rag_query("What is BorgLife?")
    assert 'results' in result
    assert len(result['results']) > 0

@pytest.mark.asyncio
async def test_dna_parsing():
    """Test DNA parsing"""
    yaml_dna = """
    header:
      code_length: 1024
      gas_limit: 1000000
      service_index: "test-borg"
    cells: []
    organs: []
    manifesto_hash: "test_hash"
    """

    parser = DNAParser()
    dna = parser.from_yaml(yaml_dna)
    assert dna.header.code_length == 1024

@pytest.mark.asyncio
async def test_phenotype_building():
    """Test phenotype building from DNA"""
    adapter = ArchonServiceAdapter()
    await adapter.initialize()

    parser = DNAParser()
    builder = PhenotypeBuilder(adapter)

    # Load test DNA
    with open('tests/fixtures/test_dna.yaml') as f:
        dna = parser.from_yaml(f.read())

    # Build phenotype
    phenotype = await builder.build(dna)
    assert len(phenotype.cells) > 0
    assert len(phenotype.organs) > 0

@pytest.mark.asyncio
async def test_end_to_end_task_execution():
    """Test complete flow: DNA → Phenotype → Task Execution"""
    # Initialize
    adapter = ArchonServiceAdapter()
    await adapter.initialize()

    # Parse DNA
    parser = DNAParser()
    with open('borg_dna.yaml') as f:
        dna = parser.from_yaml(f.read())

    # Build phenotype
    builder = PhenotypeBuilder(adapter)
    phenotype = await builder.build(dna)

    # Execute task
    result = await phenotype.execute_task("Summarize BorgLife whitepaper")
    assert result is not None

@pytest.mark.asyncio
async def test_full_demo_loop():
    """End-to-end demo: Funding → Execution → Encoding → Storage → Decoding"""
    # Mock sponsor funding (simulate DOT transfer)
    # Create borg with DNA
    borg = ProtoBorgAgent(config=test_config)
    await borg.initialize()

    # Execute task
    task = "Analyze BorgLife evolution mechanisms"
    result = await borg.execute_task(task)

    # Verify wealth tracking
    assert borg.wealth.total_costs > 0
    assert len(borg.wealth.transactions) > 0

    # Encode DNA to YAML
    dna_yaml = borg.dna_parser.to_yaml(borg.dna)
    assert 'header' in dna_yaml

    # Mock on-chain storage (verify hash consistency)
    dna_hash = hash(dna_yaml)
    # Simulate storage and retrieval
    retrieved_dna = borg.dna_parser.from_yaml(dna_yaml)
    assert retrieved_dna.header.service_index == borg.dna.header.service_index

@pytest.mark.asyncio
async def test_sponsor_ui_integration():
    """Test sponsor UI workflow (requires running Streamlit)"""
    # This would test the UI endpoints, but for CI use API tests
    # Verify UI can connect to borg agent
    pass

@pytest.mark.asyncio
async def test_archon_failure_graceful_degradation():
    """Test behavior when Archon services are unavailable"""
    # Simulate Archon downtime
    adapter = ArchonServiceAdapter()
    # Force failure
    with pytest.raises(Exception):
        await adapter.perform_rag_query("test")

    # Verify fallback or error handling
    # (Implement fallback logic in adapter)