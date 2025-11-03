"""
Synthesis Module Type Definitions

Type hints and data structures for the BorgLife synthesis pipeline.
"""

from typing import Dict, Any, Optional, List, Callable, Union, Protocol
from decimal import Decimal
from datetime import datetime

# Core DNA types
DNAHash = str  # SHA256 hash as hex string
ServiceIndex = str  # Borg service identifier
ManifestoHash = str  # Hash of Universal Principles manifesto

# Cost and economic types
DOTAmount = Decimal  # Polkadot/Kusama token amounts with high precision
CostBreakdown = Dict[str, DOTAmount]  # Breakdown of costs by category

# Execution types
ExecutionResult = Dict[str, Any]  # Result of task execution
ExecutionTime = float  # Time in seconds
ExecutionCost = DOTAmount  # Cost in DOT

# Organ types
OrganCallable = Callable[..., Any]  # Async callable for organ invocation
OrganMetadata = Dict[str, Any]  # Metadata about an organ (tool_name, endpoint, etc.)

# Cell types
CellParameters = Dict[str, Any]  # Cell configuration parameters
CellExecutionHistory = List[Dict[str, Any]]  # History of cell executions

# Phenotype types
PhenotypeBuildTimestamp = Optional[float]  # Unix timestamp of build
PhenotypeStatus = str  # 'building', 'built', 'failed', 'executing'

# Validation types
ValidationErrors = List[str]  # List of validation error messages
IntegrityCheck = bool  # True if integrity verified

# JAM storage types
JAMStorageFormat = Dict[str, Any]  # Format for on-chain storage
JAMRetrievalResult = Optional[Dict[str, Any]]  # Result of JAM retrieval

# Protocol definitions
class ExecutableCell(Protocol):
    """Protocol for executable cell instances."""

    name: str
    logic_type: str
    parameters: CellParameters

    async def execute(self, task: str) -> ExecutionResult:
        """Execute a task using this cell."""
        ...

class CostCalculator(Protocol):
    """Protocol for cost calculation implementations."""

    def calculate_phenotype_cost(self, dna: 'BorgDNA') -> Dict[str, Any]:
        """Calculate total cost of phenotype."""
        ...

    async def _calculate_task_cost(
        self,
        result: ExecutionResult,
        execution_time: ExecutionTime,
        wealth: Optional[DOTAmount]
    ) -> Dict[str, Any]:
        """Calculate cost of task execution."""
        ...

class DNAEncoder(Protocol):
    """Protocol for DNA encoding implementations."""

    def encode(self, phenotype: 'BorgPhenotype') -> 'BorgDNA':
        """Encode phenotype back to DNA."""
        ...

    def prepare_for_jam_storage(self, dna: 'BorgDNA') -> JAMStorageFormat:
        """Prepare DNA for JAM storage."""
        ...

# Type aliases for complex structures
PhenotypeCostInfo = Dict[str, Union[DOTAmount, CostBreakdown, Dict[str, DOTAmount], str, int, bool]]
TaskCostInfo = Dict[str, Union[DOTAmount, CostBreakdown, ExecutionTime, str, bool]]
EncodingStats = Dict[str, Union[int, float]]

# Forward references (to avoid circular imports)
# These will be resolved at runtime
BorgDNA = Any  # Forward reference to BorgDNA class
BorgPhenotype = Any  # Forward reference to BorgPhenotype class