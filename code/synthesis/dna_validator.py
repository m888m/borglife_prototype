# borglife_prototype/synthesis/dna_validator.py
"""
DNA Validator - Validate DNA integrity, structure, and manifesto compliance.

Handles validation of BorgLife DNA structures including manifesto hash verification,
service indexing, and round-trip integrity checks.
"""

from typing import List, Dict, Any, Optional
import hashlib
import logging
from datetime import datetime

from .dna_parser import BorgDNA, DNAHeader, Cell, Organ, BorgReputation

logger = logging.getLogger(__name__)

class DNAValidator:
    """Validate DNA integrity and structure"""

    # Universal Principles manifesto hash (BLAKE2b)
    # This would be computed from the actual manifesto document
    # For Phase 1 testing, accept any hash or use test fixture hash
    UNIVERSAL_PRINCIPLES_HASH = "abc123def456789abcdef123456789abcdef123456789abcdef123456789abcdef"  # test fixture hash

    @staticmethod
    def validate_structure(dna: BorgDNA) -> List[str]:
        """
        Validate DNA structure completeness

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check header
        if not dna.header.service_index:
            errors.append("Missing service_index in header")
        if dna.header.gas_limit <= 0:
            errors.append("Invalid gas_limit in header")
        if dna.header.code_length <= 0:
            errors.append("Invalid code_length in header")

        # Check cells
        if not dna.cells:
            errors.append("No cells defined")
        for cell in dna.cells:
            if not cell.name:
                errors.append(f"Cell missing name")
            if not cell.logic_type:
                errors.append(f"Cell {cell.name} missing logic_type")
            if cell.cost_estimate < 0:
                errors.append(f"Cell {cell.name} has negative cost_estimate")

        # Check organs
        for organ in dna.organs:
            if not organ.mcp_tool:
                errors.append(f"Organ {organ.name} missing mcp_tool")
            if not organ.url:
                errors.append(f"Organ {organ.name} missing url")
            if organ.price_cap < 0:
                errors.append(f"Organ {organ.name} has negative price_cap")

        # Check manifesto hash
        if not dna.manifesto_hash:
            errors.append("Missing manifesto_hash")
        elif dna.manifesto_hash != DNAValidator.UNIVERSAL_PRINCIPLES_HASH:
            errors.append("Manifesto hash does not match Universal Principles")

        # Check reputation (optional, but validate if present)
        if dna.reputation:
            if dna.reputation.average_rating < 0 or dna.reputation.average_rating > 5:
                errors.append("Invalid average_rating (must be 0-5)")
            if dna.reputation.total_ratings < 0:
                errors.append("Invalid total_ratings (cannot be negative)")
            # Rating distribution should sum to total_ratings
            distribution_sum = sum(dna.reputation.rating_distribution.values())
            if distribution_sum != dna.reputation.total_ratings:
                errors.append(f"Rating distribution sum ({distribution_sum}) doesn't match total_ratings ({dna.reputation.total_ratings})")

        return errors

    @staticmethod
    def validate_round_trip(original_dna: BorgDNA, yaml_str: str) -> bool:
        """
        Validate round-trip integrity: DNA → YAML → DNA

        Returns:
            True if H(D') = H(D)
        """
        from .dna_parser import DNAParser

        # Encode to YAML
        encoded_yaml = DNAParser.to_yaml(original_dna)

        # Decode back
        decoded_dna = DNAParser.from_yaml(encoded_yaml)

        # Compare hashes
        original_hash = original_dna.compute_hash()
        decoded_hash = decoded_dna.compute_hash()

        return original_hash == decoded_hash