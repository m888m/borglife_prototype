"""
BorgLife Synthesis Module

Handles DNA parsing, phenotype building, encoding, and borg lifecycle management.
Provides the core synthesis pipeline from DNA to executable phenotypes and back.
"""

# Communication protocols
from .cell_organ_protocol import CellOrganBridge
# Core DNA handling
from .dna_parser import BorgDNA, Cell, DNAHeader, DNAParser, Organ
from .dna_validator import DNAValidator
from .exceptions import *
# Phenotype synthesis
from .phenotype_builder import BorgPhenotype, PhenotypeBuilder
from .phenotype_encoder import EncodingError, PhenotypeEncoder
# Types and exceptions
from .types import *

# Version info
__version__ = "1.0.0"

__all__ = [
    # DNA handling
    "DNAParser",
    "BorgDNA",
    "DNAHeader",
    "Cell",
    "Organ",
    "DNAValidator",
    # Phenotype synthesis
    "PhenotypeBuilder",
    "BorgPhenotype",
    "PhenotypeEncoder",
    "EncodingError",
    # Communication
    "CellOrganBridge",
    # Types
    "DNAHash",
    "ServiceIndex",
    "ManifestoHash",
    "DOTAmount",
    "CostBreakdown",
    "ExecutionResult",
    "ExecutionTime",
    "ExecutionCost",
    "OrganCallable",
    "OrganMetadata",
    "CellParameters",
    "CellExecutionHistory",
    "PhenotypeBuildTimestamp",
    "PhenotypeStatus",
    "ValidationErrors",
    "IntegrityCheck",
    "JAMStorageFormat",
    "JAMRetrievalResult",
    "ExecutableCell",
    "CostCalculator",
    "DNAEncoder",
    "PhenotypeCostInfo",
    "TaskCostInfo",
    "EncodingStats",
    # Exceptions
    "SynthesisError",
    "DNAParseError",
    "DNAValidationError",
    "PhenotypeBuildError",
    "OrganInjectionError",
    "CellExecutionError",
    "CostCalculationError",
    "EncodingError",
    "IntegrityError",
    # Version
    "__version__",
]
