# borglife_prototype/synthesis/dna_parser.py
"""
DNA Parser - Parse Borg DNA from YAML/PVM formats.

Handles conversion between YAML representation and structured BorgDNA objects,
with validation and integrity checking.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, validator


# Custom exception for DNA parsing errors
class DNAParsingError(Exception):
    """Exception raised for DNA parsing errors."""

    def __init__(
        self, format_type: str, message: str, line_number: Optional[int] = None
    ):
        self.format_type = format_type
        self.message = message
        self.line_number = line_number
        super().__init__(
            f"{format_type.upper()} parsing error: {message}"
            + (f" at line {line_number}" if line_number else "")
        )


logger = logging.getLogger(__name__)


class DNAHeader(BaseModel):
    """DNA header structure (H) - contains metadata and constraints."""

    code_length: int = Field(..., gt=0, description="Total code length in bytes")
    gas_limit: int = Field(..., gt=0, description="Maximum gas units for execution")
    service_index: str = Field(
        ..., min_length=1, description="Unique service identifier"
    )

    @validator("service_index")
    def validate_service_index(cls, v):
        """Validate service index format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Service index must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v


class Cell(BaseModel):
    """Cell definition (C) - individual logic units."""

    name: str = Field(..., min_length=1, description="Unique cell name")
    logic_type: str = Field(
        ..., description="Type of logic (rag_agent, decision_maker, etc.)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Cell-specific parameters"
    )
    cost_estimate: float = Field(
        default=0.0, ge=0, description="Estimated execution cost"
    )

    @validator("name")
    def validate_name(cls, v):
        """Validate cell name format."""
        if not v.replace("_", "").isalnum():
            raise ValueError(
                "Cell name must contain only alphanumeric characters and underscores"
            )
        return v


class Organ(BaseModel):
    """Organ definition (O) - external capability pointers."""

    name: str = Field(..., min_length=1, description="Unique organ name")
    mcp_tool: str = Field(..., description="MCP tool identifier")
    url: str = Field(..., description="Service endpoint URL")
    abi_version: str = Field("1.0", description="ABI version for compatibility")
    price_cap: float = Field(default=0.0, ge=0, description="Maximum price per call")

    @validator("name")
    def validate_name(cls, v):
        """Validate organ name format."""
        if not v.replace("_", "").isalnum():
            raise ValueError(
                "Organ name must contain only alphanumeric characters and underscores"
            )
        return v

    @validator("url")
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class BorgReputation(BaseModel):
    """Reputation data integrated into DNA for evolution substrate."""

    average_rating: float = Field(
        default=0.0, ge=0.0, le=5.0, description="Average rating (1-5 stars)"
    )
    total_ratings: int = Field(
        default=0, ge=0, description="Total number of ratings received"
    )
    rating_distribution: Dict[int, int] = Field(
        default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        description="Distribution of ratings by star level",
    )
    last_rated: Optional[str] = Field(
        default=None, description="ISO timestamp of last rating"
    )


class BorgDNA(BaseModel):
    """Complete DNA structure (D = (H, C, O, M, R))."""

    header: DNAHeader
    cells: List[Cell] = Field(default_factory=list)
    organs: List[Organ] = Field(default_factory=list)
    manifesto_hash: str = Field(
        ..., description="Hash of Universal Principles manifesto"
    )
    reputation: BorgReputation = Field(
        default_factory=BorgReputation, description="User satisfaction ratings"
    )

    def compute_hash(self) -> str:
        """
        Compute DNA hash H(D) for integrity verification.

        Returns:
            BLAKE2b hash of the DNA structure
        """
        # Serialize to canonical form for consistent hashing
        dna_dict = self.dict(exclude_unset=True)

        # Sort keys for deterministic serialization
        canonical_yaml = yaml.dump(
            dna_dict, default_flow_style=False, sort_keys=True, allow_unicode=True
        )

        # Compute hash
        hash_obj = hashlib.blake2b(digest_size=32)
        hash_obj.update(canonical_yaml.encode("utf-8"))

        return hash_obj.hexdigest()

    def validate_integrity(self) -> bool:
        """
        Validate DNA integrity by checking structure and manifesto compliance.

        Returns:
            True if DNA is valid and compliant
        """
        from .dna_validator import DNAValidator

        # Structural validation
        structure_errors = DNAValidator.validate_structure(self)
        if structure_errors:
            logger.warning(f"DNA structure validation failed: {structure_errors}")
            return False

        # Manifesto hash validation (skip for Phase 1 demo)
        if (
            not DNAValidator.SKIP_MANIFESTO_VALIDATION
            and self.manifesto_hash != DNAValidator.UNIVERSAL_PRINCIPLES_HASH
        ):
            logger.warning(
                f"Manifesto hash mismatch: {self.manifesto_hash} != {DNAValidator.UNIVERSAL_PRINCIPLES_HASH}"
            )
            return False

        return True

    def get_cell_names(self) -> List[str]:
        """Get list of cell names."""
        return [cell.name for cell in self.cells]

    def get_organ_names(self) -> List[str]:
        """Get list of organ names."""
        return [organ.name for organ in self.organs]

    def get_cell_by_name(self, name: str) -> Optional[Cell]:
        """Get cell by name."""
        for cell in self.cells:
            if cell.name == name:
                return cell
        return None

    def get_organ_by_name(self, name: str) -> Optional[Organ]:
        """Get organ by name."""
        for organ in self.organs:
            if organ.name == name:
                return organ
        return None


class DNAParser:
    """Parser for DNA in various formats."""

    @staticmethod
    def from_yaml(yaml_str: str) -> BorgDNA:
        """
        Parse DNA from YAML string.

        Args:
            yaml_str: YAML representation of DNA

        Returns:
            BorgDNA object

        Raises:
            DNAParsingError: If parsing fails
        """
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_str)
            if not isinstance(data, dict):
                raise DNAParsingError("yaml", "Root must be a dictionary", None)

            # Validate required fields
            required_fields = ["header", "manifesto_hash"]
            for field in required_fields:
                if field not in data:
                    raise DNAParsingError(
                        "yaml", f"Missing required field: {field}", None
                    )

            # Handle optional fields
            if "cells" not in data:
                data["cells"] = []
            if "organs" not in data:
                data["organs"] = []

            # Create BorgDNA object (validation happens in Pydantic)
            dna = BorgDNA(**data)

            # Additional validation
            if not dna.validate_integrity():
                raise DNAParsingError("yaml", "DNA integrity validation failed", None)

            logger.info(
                f"Successfully parsed DNA for service: {dna.header.service_index}"
            )
            return dna

        except yaml.YAMLError as e:
            line = getattr(e, "problem_mark", None)
            line_num = line.line if line else None
            raise DNAParsingError("yaml", str(e), line_num)
        except Exception as e:
            raise DNAParsingError("yaml", f"Unexpected error: {e}", None)

    @staticmethod
    def to_yaml(dna: BorgDNA) -> str:
        """
        Serialize DNA to YAML string.

        Args:
            dna: BorgDNA object

        Returns:
            YAML representation
        """
        dna_dict = dna.dict(exclude_unset=True)

        return yaml.dump(
            dna_dict,
            default_flow_style=False,
            sort_keys=True,
            allow_unicode=True,
            indent=2,
        )

    @staticmethod
    def from_pvm(bytecode: bytes) -> BorgDNA:
        """
        Parse DNA from PVM bytecode (Phase 2).

        Args:
            bytecode: PVM bytecode

        Returns:
            BorgDNA object

        Raises:
            NotImplementedError: PVM parsing not implemented in Phase 1
        """
        raise NotImplementedError("PVM bytecode parsing implemented in Phase 2")

    @staticmethod
    def to_pvm(dna: BorgDNA) -> bytes:
        """
        Compile DNA to PVM bytecode (Phase 2).

        Args:
            dna: BorgDNA object

        Returns:
            PVM bytecode

        Raises:
            NotImplementedError: PVM compilation not implemented in Phase 1
        """
        raise NotImplementedError("PVM bytecode compilation implemented in Phase 2")

    @staticmethod
    def validate_round_trip(dna: BorgDNA) -> bool:
        """
        Validate DNA round-trip integrity: DNA → YAML → DNA.

        Args:
            dna: Original DNA object

        Returns:
            True if H(D') = H(D)
        """
        try:
            # Serialize to YAML
            yaml_str = DNAParser.to_yaml(dna)

            # Parse back
            parsed_dna = DNAParser.from_yaml(yaml_str)

            # Compare hashes
            original_hash = dna.compute_hash()
            parsed_hash = parsed_dna.compute_hash()

            return original_hash == parsed_hash

        except Exception as e:
            logger.error(f"Round-trip validation failed: {e}")
            return False

    @staticmethod
    def merge_dna(base_dna: BorgDNA, updates: Dict[str, Any]) -> BorgDNA:
        """
        Merge updates into existing DNA (for evolution).

        Args:
            base_dna: Original DNA
            updates: Updates to apply

        Returns:
            Updated DNA object
        """
        # Create copy of base DNA
        merged_data = base_dna.dict(exclude_unset=True)

        # Apply updates
        def deep_update(base_dict, updates_dict):
            for key, value in updates_dict.items():
                if (
                    isinstance(value, dict)
                    and key in base_dict
                    and isinstance(base_dict[key], dict)
                ):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value

        deep_update(merged_data, updates)

        # Create new DNA object
        return BorgDNA(**merged_data)

    @staticmethod
    def create_minimal_dna(service_index: str, manifesto_hash: str) -> BorgDNA:
        """
        Create minimal viable DNA for bootstrapping.

        Args:
            service_index: Unique service identifier
            manifesto_hash: Hash of manifesto

        Returns:
            Minimal BorgDNA object
        """
        return BorgDNA(
            header=DNAHeader(
                code_length=1024, gas_limit=1000000, service_index=service_index
            ),
            cells=[],
            organs=[],
            manifesto_hash=manifesto_hash,
        )

    @staticmethod
    def parse_dna(dna_data: Dict[str, Any]) -> str:
        """
        Parse DNA data and return hash (simplified for live testing).

        Args:
            dna_data: DNA data dictionary

        Returns:
            DNA hash string
        """
        import hashlib

        # Simple hash of the DNA data for testing
        dna_str = str(sorted(dna_data.items()))
        return hashlib.sha256(dna_str.encode()).hexdigest()
