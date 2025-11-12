import pytest
from typing import Dict
from archon_adapter import DockerMCPDiscovery, DockerMCPCompatibilityMatrix
from security import OrganRateLimiter
from billing import DockerMCPBilling

@pytest.mark.asyncio
async def test_docker_mcp_discovery():
    """Test Docker MCP organ discovery"""
    discovery = DockerMCPDiscovery()
    organs = await discovery.discover_mcp_containers()
    assert len(organs) >= 3  # gmail, stripe, bitcoin minimum

@pytest.mark.asyncio
async def test_docker_mcp_health_monitoring():
    """Test Docker MCP organ health monitoring"""
    from monitoring import DockerMCPHealthDashboard

    dashboard = DockerMCPHealthDashboard(
        monitor=None,  # Would need actual monitor
        rate_limiter=None,
        compatibility_matrix=None
    )

    # This would test health metrics collection
    # For now, just verify dashboard initializes
    assert dashboard is not None

@pytest.mark.asyncio
async def test_docker_mcp_circuit_breaker():
    """Test circuit breaker for failed Docker MCP organs"""
    from archon_adapter import MCPClient, AllFallbacksFailedError

    client = MCPClient(
        archon_adapter=None,
        fallback_manager=None,
        rate_limiter=None,
        billing_manager=None
    )

    # Simulate failures
    for i in range(3):
        try:
            await client.call_organ('nonexistent', 'test', {})
        except:
            pass

    # Circuit breaker should be open
    with pytest.raises(AllFallbacksFailedError):
        await client.call_organ('nonexistent', 'test', {})

@pytest.mark.asyncio
async def test_phenotype_with_docker_mcp_organs():
    """Test phenotype building with Docker MCP organs"""
    from synthesis import DNAParser, PhenotypeBuilder
    from archon_adapter import ArchonServiceAdapter

    adapter = ArchonServiceAdapter()
    await adapter.initialize()

    # DNA with Docker MCP organs and reputation data
    yaml_dna = """
    header:
      code_length: 2048
      gas_limit: 2000000
      service_index: "test-docker-mcp-borg"

    cells:
      - name: "payment_processor"
        logic_type: "decision_making"
        parameters:
          model: "gpt-4"
        cost_estimate: 0.002

    organs:
      - name: "stripe_payment"
        mcp_tool: "stripe:create_payment"
        url: "http://mcp-stripe:8080"
        abi_version: "2.3.0"
        price_cap: 0.005

      - name: "email_notification"
        mcp_tool: "gmail:send_email"
        url: "http://mcp-gmail:8080"
        abi_version: "1.2.0"
        price_cap: 0.0005

    manifesto_hash: "test_hash"

    reputation:
      average_rating: 4.5
      total_ratings: 10
      rating_distribution:
        5: 6
        4: 3
        3: 1
        2: 0
        1: 0
      last_rated: "2025-10-15T10:00:00Z"
    """

    parser = DNAParser()
    dna = parser.from_yaml(yaml_dna)

    # Verify reputation data is parsed
    assert dna.reputation.average_rating == 4.5
    assert dna.reputation.total_ratings == 10
    assert dna.reputation.rating_distribution[5] == 6

    builder = PhenotypeBuilder(adapter)
    phenotype = await builder.build(dna)

    # Verify Docker MCP organs are registered
    assert 'stripe_payment' in phenotype.organs
    assert 'email_notification' in phenotype.organs

    # Test organ invocation
    result = await phenotype.organs['stripe_payment'](
        amount=1000,
        currency='usd'
    )
    assert result is not None

@pytest.mark.asyncio
async def test_rating_integration_with_phenotype():
    """Test rating integration with phenotype execution"""
    from reputation import BorgRatingSystem
    from synthesis import DNAParser, PhenotypeBuilder
    from archon_adapter import ArchonServiceAdapter

    # Setup components
    rating_system = BorgRatingSystem()
    adapter = ArchonServiceAdapter()
    await adapter.initialize()

    parser = DNAParser()
    builder = PhenotypeBuilder(adapter)

    # Load DNA with initial reputation
    with open('borg_dna.yaml') as f:
        dna = parser.from_yaml(f.read())

    # Build phenotype
    phenotype = await builder.build(dna)

    # Simulate task execution and rating collection
    borg_id = dna.header.service_index
    sponsor_id = "test_sponsor"

    # Submit rating
    success = await rating_system.submit_rating(
        borg_id=borg_id,
        sponsor_id=sponsor_id,
        rating=5,
        feedback="Excellent performance on analysis task",
        task_context="Market data analysis"
    )
    assert success

    # Verify rating is stored
    ratings = await rating_system.get_borg_ratings(borg_id)
    assert len(ratings) >= 1
    assert any(r['rating'] == 5 for r in ratings)

    # Check reputation calculation
    reputation = await rating_system.calculate_reputation(borg_id)
    assert reputation['total_ratings'] >= 1
    assert 'average_rating' in reputation

    # Update DNA with new reputation data
    dna.reputation.average_rating = reputation['average_rating']
    dna.reputation.total_ratings = reputation['total_ratings']
    dna.reputation.rating_distribution = reputation['rating_distribution']
    dna.reputation.last_rated = reputation['last_rated']

    # Verify DNA integrity is maintained
    assert dna.validate_integrity()

@pytest.mark.asyncio
async def test_docker_mcp_authentication():
    """Test Docker MCP organ authentication"""
    from archon_adapter import DockerMCPAuthManager

    auth_manager = DockerMCPAuthManager()

    # Add credentials
    auth_manager.add_credential('gmail', 'app_password', 'test_app_password')
    auth_manager.add_credential('stripe', 'api_key', 'sk_test_123')

    # Retrieve credentials
    gmail_cred = auth_manager.get_credential('gmail')
    assert gmail_cred == 'test_app_password'

    stripe_cred = auth_manager.get_credential('stripe')
    assert stripe_cred == 'sk_test_123'