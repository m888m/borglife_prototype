"""
DNA Parser for BorgLife Phase 1

Handles DNA encoding/decoding between YAML and PVM formats.
D = (H, C, O, M) where:
- H: Header (gas limits, service index)
- C: Cells (GP-evolved subroutines)
- O: Organs (MCP pointers)
- M: Hash of Universal Principles manifesto
"""

import yaml
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DNAHeader(BaseModel):
    """DNA header (H) containing execution parameters."""
    code_length: int = Field(..., description="Total length of DNA code")
    gas_limit: int = Field(..., description="Maximum gas for execution")
    service_index: str = Field(..., description="Unique service identifier")


class Cell(BaseModel):
    """Cell definition (C) - GP-evolved subroutine."""
    name: str = Field(..., description="Cell identifier")
    logic_type: str = Field(..., description="Type of logic (data_processing, decision_making, etc.)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Cell-specific parameters")
    cost_estimate: float = Field(default=0.0, description="Estimated execution cost in DOT")


class Organ(BaseModel):
    """Organ pointer (O) - MCP tool reference."""
    name: str = Field(..., description="Organ identifier")
    mcp_tool: str = Field(..., description="MCP tool name (e.g., archon:perform_rag_query)")
    url: str = Field(..., description="MCP server URL")
    abi_version: str = Field(default="1.0", description="ABI version for compatibility")
    price_cap: float = Field(default=0.0, description="Maximum price in DOT")


class BorgDNA(BaseModel):
    """Complete DNA structure D = (H, C, O, M)."""
    header: DNAHeader
    cells: List[Cell] = Field(default_factory=list)
    organs: List[Organ] = Field(default_factory=list)
    manifesto_hash: str = Field(..., description="Blake2 hash of Universal Principles (M)")

    def compute_hash(self) -> str:
        """Compute DNA hash H(D) for integrity verification."""
        # Serialize to canonical form for consistent hashing
        dna_dict = self.dict(exclude_unset=True)
        dna_yaml = yaml.dump(dna_dict, sort_keys=True, default_flow_style=False)
        return hashlib.blake2b(dna_yaml.encode('utf-8')).hexdigest()

    def verify_integrity(self, expected_hash: Optional[str] = None) -> bool:
        """Verify DNA integrity: H(D') = H(D)."""
        computed_hash = self.compute_hash()
        if expected_hash:
            return computed_hash == expected_hash
        # If no expected hash provided, verify against stored manifesto_hash
        return computed_hash == self.manifesto_hash


class DNAParser:
    """
    Parser for DNA encoding/decoding between formats.

    Phase 1: YAML ↔ BorgDNA (PVM conversion is placeholder)
    Phase 2: Full PVM bytecode support
    """

    @staticmethod
    def from_yaml(yaml_str: str) -> BorgDNA:
        """
        Parse YAML DNA to BorgDNA object.

        Args:
            yaml_str: YAML string containing DNA structure

        Returns:
            BorgDNA object

        Raises:
            ValueError: If YAML is invalid or missing required fields
        """
        try:
            data = yaml.safe_load(yaml_str)
            if not isinstance(data, dict):
                raise ValueError("Invalid YAML: expected dictionary")

            # Validate required fields
            if 'header' not in data:
                raise ValueError("DNA missing required 'header' field")
            if 'manifesto_hash' not in data:
                raise ValueError("DNA missing required 'manifesto_hash' field")

            return BorgDNA(**data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")

    @staticmethod
    def to_yaml(dna: BorgDNA) -> str:
        """
        Serialize BorgDNA to YAML string.

        Args:
            dna: BorgDNA object

        Returns:
            YAML string representation
        """
        dna_dict = dna.dict(exclude_unset=True)
        return yaml.dump(dna_dict, default_flow_style=False, sort_keys=False)

    @staticmethod
    def from_pvm(bytecode: bytes) -> BorgDNA:
        """
        Parse PVM bytecode to BorgDNA (Phase 2).

        Placeholder implementation for Phase 1.
        In Phase 2, this will disassemble PVM bytecode into DNA structure.

        Args:
            bytecode: PVM bytecode

        Returns:
            BorgDNA object

        Raises:
            NotImplementedError: PVM parsing not implemented in Phase 1
        """
        # Phase 1 placeholder - would implement PVM disassembly
        raise NotImplementedError("PVM parsing implemented in Phase 2")

    @staticmethod
    def to_pvm(dna: BorgDNA) -> bytes:
        """
        Compile BorgDNA to PVM bytecode (Phase 2).

        Placeholder implementation for Phase 1.
        In Phase 2, this will compile DNA structure to PVM bytecode.

        Args:
            dna: BorgDNA object

        Returns:
            PVM bytecode

        Raises:
            NotImplementedError: PVM compilation not implemented in Phase 1
        """
        # Phase 1 placeholder - would implement PVM assembly
        raise NotImplementedError("PVM compilation implemented in Phase 2")

    @staticmethod
    def validate_dna(dna: BorgDNA) -> List[str]:
        """
        Validate DNA structure and return list of issues.

        Args:
            dna: BorgDNA object to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []

        # Validate header
        if dna.header.code_length <= 0:
            issues.append("Header code_length must be positive")
        if dna.header.gas_limit <= 0:
            issues.append("Header gas_limit must be positive")
        if not dna.header.service_index:
            issues.append("Header service_index cannot be empty")

        # Validate cells
        cell_names = set()
        for cell in dna.cells:
            if cell.name in cell_names:
                issues.append(f"Duplicate cell name: {cell.name}")
            cell_names.add(cell.name)

            if not cell.logic_type:
                issues.append(f"Cell {cell.name} missing logic_type")

            if cell.cost_estimate < 0:
                issues.append(f"Cell {cell.name} has negative cost_estimate")

        # Validate organs
        organ_names = set()
        for organ in dna.organs:
            if organ.name in organ_names:
                issues.append(f"Duplicate organ name: {organ.name}")
            organ_names.add(organ.name)

            if not organ.mcp_tool:
                issues.append(f"Organ {organ.name} missing mcp_tool")

            if organ.price_cap < 0:
                issues.append(f"Organ {organ.name} has negative price_cap")

        # Validate manifesto hash
        if not dna.manifesto_hash:
            issues.append("Manifesto hash cannot be empty")

        # Check for name conflicts between cells and organs
        name_conflicts = cell_names & organ_names
        if name_conflicts:
            issues.append(f"Name conflicts between cells and organs: {name_conflicts}")

        return issues

    @staticmethod
    def create_example_dna(service_index: str = "borg-001") -> BorgDNA:
        """
        Create an example DNA structure for testing.

        Args:
            service_index: Service identifier for the borg

        Returns:
            Example BorgDNA object
        """
        return BorgDNA(
            header=DNAHeader(
                code_length=1024,
                gas_limit=1000000,
                service_index=service_index
            ),
            cells=[
                Cell(
                    name="data_processor",
                    logic_type="data_processing",
                    parameters={"model": "gpt-4", "max_tokens": 500},
                    cost_estimate=0.001
                ),
                Cell(
                    name="decision_maker",
                    logic_type="decision_making",
                    parameters={"strategy": "utility_maximization"},
                    cost_estimate=0.0005
                )
            ],
            organs=[
                Organ(
                    name="knowledge_retrieval",
                    mcp_tool="archon:perform_rag_query",
                    url="http://archon-mcp:8051",
                    abi_version="1.0",
                    price_cap=0.0001
                ),
                Organ(
                    name="task_manager",
                    mcp_tool="archon:create_task",
                    url="http://archon-mcp:8051",
                    abi_version="1.0",
                    price_cap=0.0002
                )
            ],
            manifesto_hash="blake2_hash_of_universal_principles"
        )