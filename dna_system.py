#!/usr/bin/env python3
"""
DNA Encoding/Decoding System for Borglife Phase 1 Prototype

Implements forward (YAML → Python classes) and reverse (classes → YAML) mappings
for borg DNA with round-trip integrity. Starts with YAML, foundations for PVM.
"""

import yaml
import hashlib
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path

class BorgDNA(BaseModel):
    """Borg DNA structure as per whitepaper section 5.1."""
    header: Dict[str, Any] = Field(...)  # code length, gas limits, service index
    cells: List[Dict[str, Any]] = Field(default_factory=list)  # evolved subroutines
    organs: List[Dict[str, Any]] = Field(default_factory=list)  # MCP server pointers
    manifesto_hash: str = Field(...)  # Blake2 hash of Universal Principles

class BorgPhenotype(BaseModel):
    """Executable borg phenotype mapped from DNA."""
    name: str
    config: Dict[str, Any]
    cells: List[Dict[str, Any]]  # Python-callable logic
    organs: List[Dict[str, Any]]  # MCP endpoints
    manifesto_hash: str

class DNAMapper:
    """Handles DNA encoding/decoding with integrity checks."""

    def __init__(self, manifesto_text: str = "Universal Ethical Principles..."):
        """Initialize with manifesto for hashing."""
        self.manifesto_text = manifesto_text
        self.manifesto_hash = self._compute_manifesto_hash()

    def _compute_manifesto_hash(self) -> str:
        """Compute Blake2 hash of manifesto."""
        return hashlib.blake2b(self.manifesto_text.encode()).hexdigest()

    def encode_to_yaml(self, phenotype: BorgPhenotype) -> str:
        """Encode phenotype to YAML DNA."""
        dna_data = {
            "header": {
                "code_length": len(phenotype.cells),
                "gas_limits": {"max_gas": 1000000},  # Mock limits
                "service_index": 1  # JAM service index
            },
            "cells": phenotype.cells,
            "organs": phenotype.organs,
            "manifesto_hash": phenotype.manifesto_hash
        }

        dna = BorgDNA(**dna_data)
        return yaml.dump(dna.model_dump(), default_flow_style=False)

    def decode_from_yaml(self, yaml_str: str) -> BorgPhenotype:
        """Decode YAML DNA to phenotype."""
        dna_data = yaml.safe_load(yaml_str)
        dna = BorgDNA(**dna_data)

        # Validate manifesto hash
        if dna.manifesto_hash != self.manifesto_hash:
            raise ValueError("Manifesto hash mismatch - integrity check failed")

        phenotype = BorgPhenotype(
            name=f"Borg-{dna.header.get('service_index', 1)}",
            config=dna.header,
            cells=dna.cells,
            organs=dna.organs,
            manifesto_hash=dna.manifesto_hash
        )

        return phenotype

    def round_trip_check(self, phenotype: BorgPhenotype) -> bool:
        """Verify round-trip integrity: phenotype → YAML → phenotype."""
        yaml_str = self.encode_to_yaml(phenotype)
        decoded = self.decode_from_yaml(yaml_str)

        # Compare key fields
        return (
            phenotype.name == decoded.name and
            phenotype.config == decoded.config and
            phenotype.cells == decoded.cells and
            phenotype.organs == decoded.organs and
            phenotype.manifesto_hash == decoded.manifesto_hash
        )

    def save_dna(self, phenotype: BorgPhenotype, filepath: str):
        """Save DNA to YAML file."""
        yaml_str = self.encode_to_yaml(phenotype)
        Path(filepath).write_text(yaml_str)

    def load_dna(self, filepath: str) -> BorgPhenotype:
        """Load DNA from YAML file."""
        yaml_str = Path(filepath).read_text()
        return self.decode_from_yaml(yaml_str)

# Example usage and testing
if __name__ == "__main__":
    mapper = DNAMapper()

    # Example phenotype
    example_phenotype = BorgPhenotype(
        name="ProtoBorg-001",
        config={"service_index": 1, "gas_limits": {"max_gas": 1000000}},
        cells=[
            {"name": "data_processor", "logic": "summarize_text", "params": {"max_length": 100}}
        ],
        organs=[
            {"url": "http://localhost:8051", "interface": "MCP", "price": 0.01}
        ],
        manifesto_hash=mapper.manifesto_hash
    )

    # Test round-trip
    print("Testing round-trip integrity...")
    is_valid = mapper.round_trip_check(example_phenotype)
    print(f"Round-trip check: {'PASSED' if is_valid else 'FAILED'}")

    # Save and load
    mapper.save_dna(example_phenotype, "borg_dna.yaml")
    loaded = mapper.load_dna("borg_dna.yaml")
    print(f"Loaded phenotype: {loaded.name}")
    print(f"Cells: {len(loaded.cells)}, Organs: {len(loaded.organs)}")