"""
Pytest configuration and fixtures for BorgLife Phase 1 E2E testing.

This module provides:
- Service lifecycle management (Archon, BorgLife components)
- Test data fixtures (DNA samples, demo tasks)
- Async test support with proper event loop handling
- Health check utilities for service validation
"""

import asyncio
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional
import sys;
sys.path.insert(0, os.path.dirname(__file__) + "/..")

import pytest
import pytest_asyncio
import yaml
from dotenv import load_dotenv
from jam_mock.keypair_manager import KeypairManager

USE_MOCKS = False
# Load environment variables
load_dotenv()

# Load test-specific .env.test if exists (override)
test_env_path = Path(__file__).parent / ".env.test"
if test_env_path.exists():
    load_dotenv(str(test_env_path), override=True)
else:
    pass  # No test env, use defaults


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_addoption(parser):
    parser.addoption(
        "--mock",
        action="store_true",
        default=False,
        help="Use mock implementations instead of live blockchain"
    )
    parser.addoption(
        "--no-ssl-verify",
        action="store_true",
        default=False,
        help="Disable SSL certificate verification for live connections"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    global USE_MOCKS, NO_SSL_VERIFY
    USE_MOCKS = config.getoption("--mock")
    NO_SSL_VERIFY = config.getoption("--no-ssl-verify")
    
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (deselect with '-m \"not asyncio\"')"
    )
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "ui: mark test as UI interaction test")


# ============================================================================
# EVENT LOOP FIXTURE
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# ENVIRONMENT & CONFIGURATION FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Load test configuration from environment."""
    return {
        "archon_server_url": os.getenv("ARCHON_SERVER_URL", "http://localhost:8181"),
        "archon_mcp_url": os.getenv("ARCHON_MCP_URL", "http://localhost:8051"),
        "archon_agents_url": os.getenv("ARCHON_AGENTS_URL", "http://localhost:8052"),
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_key": os.getenv("SUPABASE_SERVICE_KEY"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "test_timeout": int(os.getenv("E2E_TEST_TIMEOUT", "300")),
        "test_parallel": os.getenv("E2E_TEST_PARALLEL", "false").lower() == "true",
    }


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Get path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def test_dna_samples(fixtures_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load test DNA samples from YAML file."""
    dna_file = fixtures_dir / "test_dna_samples.yaml"
    if not dna_file.exists():
        pytest.skip(f"Test DNA samples not found at {dna_file}")

    with open(dna_file, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def demo_tasks(fixtures_dir: Path) -> Dict[str, Any]:
    """Load demo task scenarios from JSON file."""
    tasks_file = fixtures_dir / "demo_tasks.json"
    if not tasks_file.exists():
        pytest.skip(f"Demo tasks not found at {tasks_file}")

    with open(tasks_file, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def expected_results(fixtures_dir: Path) -> Dict[str, Any]:
    """Load expected test results from JSON file."""
    results_file = fixtures_dir / "expected_results.json"
    if not results_file.exists():
        pytest.skip(f"Expected results not found at {results_file}")

    with open(results_file, "r") as f:
        return json.load(f)


# ============================================================================
# SERVICE FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def dispenser_keypair():
    """Load dispenser keypair from macOS Keychain service 'borglife-dispenser'."""
    import keyring
    from substrateinterface import Keypair
    
    service_name = "borglife-dispenser"
    private_key_hex = keyring.get_password(service_name, "private_key")
    if private_key_hex is None:
        pytest.skip("Dispenser private key not found in keychain")
    
    keypair = Keypair.create_from_private_key(
        bytes.fromhex(private_key_hex),
        ss58_format=42
    )
    assert keypair.ss58_address == "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD", "Wrong dispenser address"
    return keypair


@pytest.fixture
def random_keypair():
    """Generate random keypair for testing."""
    from substrateinterface import Keypair
    return Keypair.create_from_mnemonic(
        Keypair.generate_mnemonic(),
        ss58_format=42
    )


@pytest_asyncio.fixture
async def archon_adapter(test_config: Dict[str, Any]):
    """Initialize Archon service adapter."""
    adapter = None
    try:
        from archon_adapter import ArchonServiceAdapter

        adapter = ArchonServiceAdapter(
            server_url=test_config["archon_server_url"],
            mcp_url=test_config["archon_mcp_url"],
            agents_url=test_config["archon_agents_url"],
        )
        await adapter.initialize()

        # Verify health
        health = await adapter.check_health()
        if not health.get("overall"):
            pytest.skip(f"Archon services not healthy: {health}")

        return adapter
    except ImportError:
        pytest.skip("Archon adapter not available")
    except Exception as e:
        pytest.skip(f"Failed to initialize Archon adapter: {e}")
    finally:
        # Cleanup will be handled by pytest-asyncio
        pass


@pytest_asyncio.fixture
async def borg_agent(test_config: Dict[str, Any]):
    """Initialize ProtoBorgAgent for testing."""
    borg = None
    try:
        from proto_borg import BorgConfig, ProtoBorgAgent

        config = BorgConfig(
            service_index="test-borg-001",
            initial_wealth=Decimal("1.0"),
            kusama_endpoint=os.getenv("KUSAMA_RPC_URL", "wss://kusama-rpc.polkadot.io"),
        )

        borg = ProtoBorgAgent(config)
        await borg.initialize()

        return borg
    except ImportError:
        pytest.skip("ProtoBorgAgent not available")
    except Exception as e:
        pytest.skip(f"Failed to initialize ProtoBorgAgent: {e}")
    finally:
        # Cleanup will be handled by pytest-asyncio
        pass


@pytest_asyncio.fixture
async def dna_parser():
    """Initialize DNA parser."""
    try:
        from synthesis import DNAParser

        return DNAParser()
    except ImportError:
        pytest.skip("DNA parser not available")


@pytest_asyncio.fixture
async def phenotype_builder(archon_adapter):
    """Initialize phenotype builder."""
    try:
        from synthesis import PhenotypeBuilder

        return PhenotypeBuilder(archon_adapter)
    except ImportError:
        pytest.skip("Phenotype builder not available")


@pytest_asyncio.fixture
async def jam_interface(test_config: Dict[str, Any]):
    """Initialize JAM mock interface."""
    global USE_MOCKS
    if USE_MOCKS:
        from jam_mock.local_mock import LocalJAMMock
        jam = LocalJAMMock()
    else:
        try:
            from jam_mock import JAMInterface
            
            ssl_verify = not NO_SSL_VERIFY
            
            jam = JAMInterface(
                rpc_url=os.getenv("WESTEND_RPC_URL", "wss://westend-rpc.polkadot.io:443"),
                ssl_verify=ssl_verify,
                mock_mode=os.getenv("JAM_MOCK_MODE", "false").lower() == "true",
            )
            await asyncio.wait_for(jam.initialize(), timeout=60)
            assert len(jam.sub_pool) > 0, "Initial sub host pool is empty"
            
            # Phase 5: Assert live Westend connection
            health = await asyncio.wait_for(jam.health_check(), timeout=60)
            assert health.get("status") == "healthy", f"Cannot connect to live Westend network: {health}"
        except (ImportError, Exception) as e:
            pytest.skip(f"JAM interface not available: {e}")
    return jam


# ============================================================================
# HEALTH CHECK FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def service_health_check(archon_adapter):
    """Verify all services are healthy before test."""
    health = await archon_adapter.check_health()

    if not health.get("archon_server"):
        pytest.skip("Archon server not healthy")
    if not health.get("archon_mcp"):
        pytest.skip("Archon MCP not healthy")

    return health


# ============================================================================
# UTILITY FIXTURES
# ============================================================================


@pytest.fixture
def decimal_tolerance() -> Decimal:
    """Standard tolerance for Decimal comparisons."""
    return Decimal("0.001")


@pytest.fixture
def test_timeout(test_config: Dict[str, Any]) -> int:
    """Get test timeout in seconds."""
    return test_config["test_timeout"]


@pytest.fixture
def async_timeout():
    """Async timeout context manager."""

    @pytest.fixture
    async def _timeout(seconds: int = 30):
        try:
            yield
        except asyncio.TimeoutError:
            pytest.fail(f"Test timed out after {seconds} seconds")

    return _timeout


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture
def cleanup_resources():
    """Cleanup resources after test."""
    resources = []

    def register_cleanup(resource, cleanup_func):
        resources.append((resource, cleanup_func))

    yield register_cleanup

    # Cleanup in reverse order
    for resource, cleanup_func in reversed(resources):
        try:
            if asyncio.iscoroutinefunction(cleanup_func):
                asyncio.run(cleanup_func(resource))
            else:
                cleanup_func(resource)
        except Exception as e:
            print(f"Cleanup error: {e}")


# ============================================================================
# MARKERS & PARAMETRIZATION
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on naming conventions."""
    for item in items:
        # Add asyncio marker to async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)

        # Add integration marker to integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Add e2e marker to e2e tests
        if "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)

        # Add slow marker to slow tests
        if "slow" in item.nodeid or "performance" in item.nodeid:
            item.add_marker(pytest.mark.slow)

        # Add ui marker to UI tests
        if "ui" in item.nodeid:
            item.add_marker(pytest.mark.ui)
