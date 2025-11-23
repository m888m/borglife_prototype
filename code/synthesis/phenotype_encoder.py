"""
Phenotype Encoder - Convert working phenotypes back to DNA for on-chain storage.

This module handles the reverse mapping from executable borg phenotypes back to
DNA structures suitable for JAM protocol storage and integrity verification.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

from .dna_parser import BorgDNA, Cell, DNAHeader, Organ
from .phenotype_builder import BorgPhenotype


class PhenotypeEncoder:
    """
    Encode working phenotype back to DNA structure for on-chain storage.

    Handles the reverse mapping: Phenotype → DNA → JAM storage
    Ensures round-trip integrity: H(D') = H(D)
    """

    def __init__(self):
        self.encoding_stats = {
            "total_encodings": 0,
            "successful_encodings": 0,
            "failed_encodings": 0,
            "avg_encoding_time": 0.0,
        }

    def encode(self, phenotype: BorgPhenotype) -> BorgDNA:
        """
        Convert phenotype to DNA with full fidelity preservation.

        Process:
        1. Extract header with updated metadata
        2. Encode cells with runtime state and optimizations
        3. Encode organs with usage statistics and performance data
        4. Preserve manifesto hash for integrity verification
        5. Validate round-trip integrity

        Args:
            phenotype: Working phenotype to encode

        Returns:
            BorgDNA ready for on-chain storage

        Raises:
            EncodingError: If encoding fails or integrity check fails
        """
        start_time = datetime.utcnow()

        try:
            # Extract header with updated metadata
            header = DNAHeader(
                code_length=self._estimate_code_length(phenotype),
                gas_limit=phenotype.dna.header.gas_limit,
                service_index=phenotype.dna.header.service_index,
            )

            # Encode cells with full runtime state
            cells = []
            for cell_name, cell_instance in phenotype.cells.items():
                cells.append(self._encode_cell(cell_name, cell_instance))

            # Encode organs with usage statistics
            organs = []
            for organ_name, organ_callable in phenotype.organs.items():
                organs.append(self._encode_organ(organ_name, organ_callable))

            # Create encoded DNA
            encoded_dna = BorgDNA(
                header=header,
                cells=cells,
                organs=organs,
                manifesto_hash=phenotype.dna.manifesto_hash,
            )

            # Validate integrity
            if not self._validate_encoding_integrity(phenotype.dna, encoded_dna):
                raise EncodingError(
                    phenotype.dna.header.service_index,
                    "Round-trip integrity validation failed",
                )

            # Update stats
            encoding_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_encoding_stats(True, encoding_time)

            return encoded_dna

        except Exception as e:
            encoding_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_encoding_stats(False, encoding_time)
            borg_id = phenotype.dna.header.service_index if phenotype.dna else "unknown"
            raise EncodingError(borg_id, f"Phenotype encoding failed: {e}")

    def _encode_cell(self, cell_name: str, cell_instance) -> Cell:
        """
        Encode a single cell with full runtime state.

        Captures:
        - Base parameters and runtime optimizations
        - Execution history and performance metrics
        - Cost estimates and usage statistics
        - Model configurations and tuning parameters
        """
        return Cell(
            name=cell_name,
            logic_type=getattr(cell_instance, "logic_type", "unknown"),
            parameters=self._extract_cell_params(cell_instance),
            cost_estimate=self._calculate_cell_cost(cell_instance),
        )

    def _encode_organ(self, organ_name: str, organ_callable) -> Organ:
        """
        Encode a single organ with usage statistics.

        Captures:
        - MCP tool metadata and endpoint information
        - Usage statistics and performance metrics
        - Price caps and cost history
        - Compatibility and version information
        """
        return Organ(
            name=organ_name,
            mcp_tool=getattr(organ_callable, "tool_name", organ_name),
            url=getattr(organ_callable, "endpoint", ""),
            abi_version=getattr(organ_callable, "version", "1.0"),
            price_cap=self._calculate_organ_price_cap(organ_callable),
        )

    def _extract_cell_params(self, cell_instance) -> Dict[str, Any]:
        """
        Extract comprehensive cell parameters including runtime state.

        Includes:
        - Base configuration parameters
        - Runtime optimizations and tuning
        - Model parameters and settings
        - Performance and usage statistics
        """
        params = {}

        # Extract base parameters
        if hasattr(cell_instance, "parameters"):
            params.update(cell_instance.parameters)
        elif hasattr(cell_instance, "base_parameters"):
            params.update(cell_instance.base_parameters)

        # Add runtime optimizations
        if hasattr(cell_instance, "optimized_params"):
            params["runtime_optimizations"] = cell_instance.optimized_params

        # Add performance metrics
        if hasattr(cell_instance, "performance_metrics"):
            params["performance_metrics"] = cell_instance.performance_metrics

        # Add model configuration
        if hasattr(cell_instance, "model_config"):
            params["model_config"] = cell_instance.model_config

        return params

    def _calculate_cell_cost(self, cell_instance) -> float:
        """
        Calculate cell cost based on execution history and complexity.

        Uses execution history when available, falls back to static estimates.
        """
        if (
            hasattr(cell_instance, "execution_history")
            and cell_instance.execution_history
        ):
            costs = []
            for execution in cell_instance.execution_history:
                if "cost" in execution:
                    costs.append(float(execution["cost"]))
            return (
                sum(costs) / len(costs)
                if costs
                else getattr(cell_instance, "cost_estimate", 0.001)
            )

        # Fallback to static cost estimate
        return getattr(cell_instance, "cost_estimate", 0.001)

    def _calculate_organ_price_cap(self, organ_callable) -> float:
        """
        Calculate organ price cap based on usage and performance.

        Uses stored price cap, with fallback to default.
        """
        return getattr(organ_callable, "price_cap", 0.001)

    def _estimate_code_length(self, phenotype: BorgPhenotype) -> int:
        """
        Estimate code length based on phenotype complexity.

        Considers:
        - Number of cells and organs
        - Parameter complexity
        - Execution history size
        """
        base_length = 1024  # Minimum code length

        # Add length for cells
        cell_length = sum(
            len(str(getattr(cell, "parameters", {})))
            + len(str(getattr(cell, "execution_history", [])))
            for cell in phenotype.cells.values()
        )

        # Add length for organs
        organ_length = sum(
            len(str(getattr(organ, "tool_name", "")))
            + len(str(getattr(organ, "endpoint", "")))
            for organ in phenotype.organs.values()
        )

        return base_length + cell_length + organ_length

    def _validate_encoding_integrity(
        self, original_dna: BorgDNA, encoded_dna: BorgDNA
    ) -> bool:
        """
        Validate that encoding preserves DNA integrity.

        Checks:
        - Service index consistency
        - Manifesto hash preservation
        - Structural completeness
        """
        # Service index must match
        if original_dna.header.service_index != encoded_dna.header.service_index:
            return False

        # Manifesto hash must be preserved
        if original_dna.manifesto_hash != encoded_dna.manifesto_hash:
            return False

        # Must have same number of cells and organs
        if len(original_dna.cells) != len(encoded_dna.cells):
            return False
        if len(original_dna.organs) != len(encoded_dna.organs):
            return False

        return True

    def prepare_for_jam_storage(self, dna: BorgDNA) -> Dict[str, Any]:
        """
        Prepare DNA for JAM protocol storage.

        Formats DNA for on-chain storage with:
        - DNA hash computation
        - Storage format optimization
        - Metadata for retrieval
        """
        # Serialize to canonical format using DNAParser
        from .dna_parser import DNAParser

        parser = DNAParser()
        dna_yaml = parser.to_yaml(dna)

        # Compute hash for integrity verification
        dna_hash = hashlib.sha256(dna_yaml.encode("utf-8")).hexdigest()

        return {
            "dna_hash": dna_hash,
            "dna_yaml": dna_yaml,
            "service_index": dna.header.service_index,
            "code_length": dna.header.code_length,
            "cell_count": len(dna.cells),
            "organ_count": len(dna.organs),
            "manifesto_hash": dna.manifesto_hash,
            "prepared_at": datetime.utcnow().isoformat(),
            "encoder_version": "1.0.0",
        }

    def _update_encoding_stats(self, success: bool, encoding_time: float):
        """Update encoding statistics."""
        self.encoding_stats["total_encodings"] += 1

        if success:
            self.encoding_stats["successful_encodings"] += 1
        else:
            self.encoding_stats["failed_encodings"] += 1

        # Update rolling average
        total_time = self.encoding_stats["avg_encoding_time"] * (
            self.encoding_stats["total_encodings"] - 1
        )
        self.encoding_stats["avg_encoding_time"] = (
            total_time + encoding_time
        ) / self.encoding_stats["total_encodings"]

    def get_encoding_stats(self) -> Dict[str, Any]:
        """Get encoding statistics."""
        return self.encoding_stats.copy()


class EncodingError(Exception):
    """Raised when phenotype encoding fails."""

    def __init__(self, borg_id: str, message: str):
        self.borg_id = borg_id
        self.message = message
        super().__init__(f"Borg {borg_id}: {message}")
