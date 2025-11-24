
#!/usr/bin/env python3
"""
Phenotype Encoder Tests - Validate encoding/decoding round-trip integrity.
"""

import pytest
from unittest.mock import MagicMock, patch

from synthesis.phenotype_encoder import PhenotypeEncoder, EncodingError
from synthesis.dna_parser import BorgDNA, DNAHeader, Cell, Organ
from synthesis.phenotype_builder import BorgPhenotype

@pytest.fixture
def mock_phenotype():
    """Mock phenotype for testing."""
    dna = BorgDNA(
        header=DNAHeader(code_length=1024, gas_limit=1000000, service_index="test-borg"),
        cells=[Cell(name="test_cell", logic_type="test", parameters={}, cost_estimate=0.001)],
        organs=[Organ(name="test_organ", mcp_tool="test_tool", url="http://test", abi_version="1.0", price_cap=0.001)],
        manifesto_hash="test_hash"
    )
    phenotype = MagicMock()
    phenotype.dna