"""
DNA Integrity Tests for BorgLife Phase 1 E2E Testing

Tests DNA parsing, validation, round-trip integrity (H(D') = H(D)),
and structural consistency across different borg configurations.
"""

import hashlib
import json
import os
import pytest
import yaml
from decimal import Decimal, getcontext
from typing import Dict, Any, List
from unittest.mock import MagicMock

# Test imports - these will be available in Docker environment
try:
    from synthesis.dna_parser import DNAParser
    from synthesis.phenotype_builder import PhenotypeBuilder
    IMPORTS_AVAILABLE = True
except ImportError:
    # Mock for development environment
    DNAParser = MagicMock
    PhenotypeBuilder = MagicMock
    IMPORTS_AVAILABLE = False


class TestDNAIntegrity:
    """Test suite for DNA parsing, validation, and integrity."""

    @pytest.fixture
    def dna_parser(self):
        """Fixture for DNA parser instance."""
        if not IMPORTS_AVAILABLE:
            # Mock parser for development
            parser = MagicMock()
            parser.parse_dna.return_value = {
                "header": {"code_length": 1024, "gas_limit": 1000000},
                "cells": [{"name": "test_cell", "logic_type": "rag_agent"}],
                "organs": [],
                "manifesto_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            }
            parser.validate_dna.return_value = True
            parser.calculate_hash.return_value = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            return parser
        else:
            # Real parser for Docker environment
            return DNAParser()

    @pytest.fixture
    def phenotype_builder(self):
        """Fixture for phenotype builder instance."""
        if not IMPORTS_AVAILABLE:
            # Mock builder for development
            builder = MagicMock()
            builder.build_phenotype.return_value = {
                "cells": [{"name": "test_cell", "capabilities": ["rag", "reasoning"]}],
                "organs": [],
                "total_cost": 0.001
            }
            return builder
        else:
            # Real builder for Docker environment
            return PhenotypeBuilder()

    @pytest.fixture
    def test_dna_samples(self) -> Dict[str, Dict[str, Any]]:
        """Load test DNA samples from fixtures."""
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_dna_samples.yaml")
        with open(fixture_path, 'r') as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def expected_results(self) -> Dict[str, Dict[str, Any]]:
        """Load expected results from fixtures."""
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "expected_results.json")
        with open(fixture_path, 'r') as f:
            return json.load(f)

    def test_dna_parsing_basic(self, dna_parser, test_dna_samples):
        """Test basic DNA parsing functionality."""
        for dna_name, dna_config in test_dna_samples.items():
            parsed_dna = dna_parser.parse_dna(dna_config)

            # Verify required fields are present
            assert "header" in parsed_dna
            assert "cells" in parsed_dna
            assert "organs" in parsed_dna
            assert "manifesto_hash" in parsed_dna

            # Verify header structure
            assert "code_length" in parsed_dna["header"]
            assert "gas_limit" in parsed_dna["header"]
            assert "service_index" in parsed_dna["header"]

    def test_dna_validation(self, dna_parser, test_dna_samples):
        """Test DNA validation against schema."""
        for dna_name, dna_config in test_dna_samples.items():
            is_valid = dna_parser.validate_dna(dna_config)
            assert is_valid, f"DNA validation failed for {dna_name}"

    def test_dna_round_trip_integrity(self, dna_parser, test_dna_samples, expected_results):
        """Test DNA round-trip integrity: H(D) = H(D')."""
        for dna_name, dna_config in test_dna_samples.items():
            # Parse DNA
            parsed_dna = dna_parser.parse_dna(dna_config)

            # Serialize back to canonical form
            canonical_dna = dna_parser.serialize_to_canonical(parsed_dna)

            # Calculate hash of original
            original_hash = dna_parser.calculate_hash(dna_config)

            # Calculate hash of round-trip result
            roundtrip_hash = dna_parser.calculate_hash(canonical_dna)

            # Verify integrity: H(D) = H(D')
            assert original_hash == roundtrip_hash, \
                f"Round-trip integrity failed for {dna_name}: {original_hash} != {roundtrip_hash}"

            # Verify against expected results
            expected = expected_results[dna_name]
            assert expected["roundtrip_integrity"] is True

    def test_dna_hash_consistency(self, dna_parser, test_dna_samples):
        """Test that DNA hashing is consistent and deterministic."""
        for dna_name, dna_config in test_dna_samples.items():
            # Calculate hash multiple times
            hash1 = dna_parser.calculate_hash(dna_config)
            hash2 = dna_parser.calculate_hash(dna_config)
            hash3 = dna_parser.calculate_hash(dna_config)

            # All hashes should be identical
            assert hash1 == hash2 == hash3, f"Inconsistent hashing for {dna_name}"

            # Hash should be valid SHA256
            assert len(hash1) == 64, f"Invalid hash length for {dna_name}"
            assert all(c in "0123456789abcdef" for c in hash1), f"Invalid hash characters for {dna_name}"

    def test_dna_structural_validation(self, dna_parser, test_dna_samples, expected_results):
        """Test DNA structural validation against expected results."""
        for dna_name, dna_config in test_dna_samples.items():
            parsed_dna = dna_parser.parse_dna(dna_config)
            expected = expected_results[dna_name]

            # Verify cell count
            assert len(parsed_dna["cells"]) == expected["expected_cells"], \
                f"Cell count mismatch for {dna_name}"

            # Verify organ count
            assert len(parsed_dna["organs"]) == expected["expected_organs"], \
                f"Organ count mismatch for {dna_name}"

            # Verify service index
            assert parsed_dna["header"]["service_index"] == expected["service_index"], \
                f"Service index mismatch for {dna_name}"

    def test_dna_cost_calculation(self, phenotype_builder, test_dna_samples, expected_results):
        """Test DNA cost calculation accuracy."""
        getcontext().prec = 6  # Set decimal precision

        for dna_name, dna_config in test_dna_samples.items():
            phenotype = phenotype_builder.build_phenotype(dna_config)
            expected = expected_results[dna_name]

            # Verify cost is within expected range
            total_cost = Decimal(str(phenotype["total_cost"]))
            expected_min = Decimal(str(expected["expected_cost_range"][0]))
            expected_max = Decimal(str(expected["expected_cost_range"][1]))

            assert expected_min <= total_cost <= expected_max, \
                f"Cost out of range for {dna_name}: {total_cost} not in [{expected_min}, {expected_max}]"

    def test_dna_phenotype_building(self, phenotype_builder, test_dna_samples):
        """Test phenotype building from DNA configurations."""
        for dna_name, dna_config in test_dna_samples.items():
            phenotype = phenotype_builder.build_phenotype(dna_config)

            # Verify phenotype structure
            assert "cells" in phenotype
            assert "organs" in phenotype
            assert "total_cost" in phenotype

            # Verify cells have capabilities
            for cell in phenotype["cells"]:
                assert "name" in cell
                assert "capabilities" in cell
                assert isinstance(cell["capabilities"], list)

    def test_dna_edge_cases(self, dna_parser, test_dna_samples):
        """Test DNA parsing with edge cases."""
        # Test minimal DNA (no organs)
        minimal_dna = test_dna_samples["test_dna_edge_case_no_organs"]
        parsed = dna_parser.parse_dna(minimal_dna)
        assert len(parsed["organs"]) == 0
        assert len(parsed["cells"]) == 1

        # Test complex DNA (many organs)
        complex_dna = test_dna_samples["test_dna_edge_case_many_organs"]
        parsed = dna_parser.parse_dna(complex_dna)
        assert len(parsed["organs"]) == 5
        assert len(parsed["cells"]) == 1

    def test_dna_canonical_serialization(self, dna_parser, test_dna_samples):
        """Test canonical serialization for consistent hashing."""
        for dna_name, dna_config in test_dna_samples.items():
            # Parse and serialize
            parsed = dna_parser.parse_dna(dna_config)
            canonical = dna_parser.serialize_to_canonical(parsed)

            # Parse canonical version
            reparsed = dna_parser.parse_dna(canonical)

            # Should be structurally equivalent
            assert parsed["header"] == reparsed["header"]
            assert len(parsed["cells"]) == len(reparsed["cells"])
            assert len(parsed["organs"]) == len(reparsed["organs"])

    def test_dna_validation_error_handling(self, dna_parser):
        """Test DNA validation error handling."""
        # Test invalid DNA structures
        invalid_dnas = [
            {},  # Empty
            {"cells": []},  # No header
            {"header": {}, "cells": []},  # Empty header
            {"header": {"code_length": "invalid"}, "cells": []},  # Invalid types
        ]

        for invalid_dna in invalid_dnas:
            is_valid = dna_parser.validate_dna(invalid_dna)
            assert not is_valid, f"Should reject invalid DNA: {invalid_dna}"

    def test_dna_hash_collision_resistance(self, dna_parser, test_dna_samples):
        """Test that different DNAs produce different hashes."""
        hashes = set()

        for dna_name, dna_config in test_dna_samples.items():
            dna_hash = dna_parser.calculate_hash(dna_config)
            # All hashes should be unique
            assert dna_hash not in hashes, f"Hash collision detected for {dna_name}"
            hashes.add(dna_hash)

        # Should have as many unique hashes as DNA samples
        assert len(hashes) == len(test_dna_samples)

    def test_dna_round_trip_integrity_explicit(self, dna_parser, test_dna_samples):
        """Explicit test for DNA round-trip integrity: H(D) = H(D')."""
        for dna_name, dna_config in test_dna_samples.items():
            # Original DNA hash
            original_hash = dna_parser.calculate_hash(dna_config)

            # Parse DNA
            parsed_dna = dna_parser.parse_dna(dna_config)

            # Serialize back to YAML (simulating storage/transmission)
            serialized_yaml = dna_parser.to_yaml(parsed_dna)

            # Parse again (simulating loading from storage)
            reparsed_dna = dna_parser.from_yaml(serialized_yaml)

            # Serialize again to canonical form
            final_yaml = dna_parser.to_yaml(reparsed_dna)

            # Calculate final hash
            final_hash = dna_parser.calculate_hash_from_yaml(final_yaml)

            # CRITICAL: H(D) = H(D') - round-trip integrity maintained
            assert original_hash == final_hash, \
                f"Round-trip integrity FAILED for {dna_name}: {original_hash} != {final_hash}"

            # Verify structural equivalence
            assert parsed_dna["header"] == reparsed_dna["header"]
            assert len(parsed_dna["cells"]) == len(reparsed_dna["cells"])
            assert len(parsed_dna["organs"]) == len(reparsed_dna["organs"])

    def test_dna_hash_consistency_across_formats(self, dna_parser, test_dna_samples):
        """Test DNA hash consistency across different serialization formats."""
        for dna_name, dna_config in test_dna_samples.items():
            # Calculate hash from dict
            dict_hash = dna_parser.calculate_hash(dna_config)

            # Convert to YAML and back
            yaml_str = dna_parser.to_yaml(dna_config)
            from_yaml = dna_parser.from_yaml(yaml_str)

            # Calculate hash from reparsed dict
            reparse_hash = dna_parser.calculate_hash(from_yaml)

            # Calculate hash directly from YAML string
            yaml_hash = dna_parser.calculate_hash_from_yaml(yaml_str)

            # All hashes should be identical (H(D) = H(D'))
            assert dict_hash == reparse_hash == yaml_hash, \
                f"Hash inconsistency for {dna_name}: {dict_hash} != {reparse_hash} != {yaml_hash}"

            # Verify this is the core success criteria for BorgLife Phase 1
            # DNA integrity must be maintained through all transformations