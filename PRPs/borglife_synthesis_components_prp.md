name: "BorgLife Synthesis Components Implementation PRP"
description: |

---

## Goal

**Feature Goal**: Implement complete BorgLife synthesis components (DNA Parser, Phenotype Builder, Cell/Organ Protocol) to enable real DNA-to-phenotype transformation and task execution capabilities.

**Deliverable**: Fully functional synthesis engine that can parse BorgLife DNA, build executable phenotypes, and orchestrate cell/organ interactions for task execution.

**Success Definition**: All synthesis components work together to transform DNA configurations into executable borgs that can perform tasks through coordinated cell/organ interactions, with proper error handling and validation.

## User Persona (if applicable)

**Target User**: BorgLife Phase 1 developers and demo participants

**Use Case**: Creating functional borgs from DNA configurations for task execution and demonstration

**User Journey**:
1. Define borg DNA with cells and organs
2. Parse DNA into structured format
3. Build phenotype with executable cells/organs
4. Execute tasks through phenotype orchestration
5. Validate results and DNA integrity

**Pain Points Addressed**: Lack of real DNA parsing, phenotype building, and task execution capabilities

## Why

- **Business value**: Enables core BorgLife functionality for demos and Phase 1 validation
- **Integration with existing features**: Builds on existing proto_borg.py and test infrastructure
- **Problems this solves**: Missing synthesis components prevent real borg creation and task execution

## What

Complete implementation of BorgLife synthesis components:

### DNA Parser
- YAML/JSON DNA parsing and validation
- Canonical serialization for hashing
- Round-trip integrity validation H(D') = H(D)
- Schema validation and error handling

### Phenotype Builder
- Cell instantiation from DNA configurations
- Organ injection and MCP tool binding
- Cost calculation and resource allocation
- Async phenotype construction

### Cell/Organ Protocol
- Standardized cell-organ communication
- Async task execution coordination
- Error propagation and recovery
- Resource management and cleanup

### Integration Points
- Archon MCP tool integration
- JAM interface for wealth tracking
- Docker MCP organ support
- Circuit breaker and fallback handling

## All Needed Context

### Context Completeness Check

_Before writing this PRP, validate: "If someone knew nothing about this codebase, would they have everything needed to implement this successfully?"_

### Documentation & References

```yaml
- file: code/proto_borg.py
  why: Core borg lifecycle and task execution patterns
  pattern: BorgConfig, ProtoBorgAgent initialization, execute_task flow
  gotcha: Async initialization required, wealth tracking integration

- file: code/tests/test_dna_integrity.py
  why: DNA parsing and validation requirements
  pattern: Round-trip integrity H(D')=H(D), canonical serialization
  gotcha: YAML canonical format for consistent hashing

- file: code/tests/test_economic_model.py
  why: Cost calculation and decimal precision requirements
  pattern: Decimal arithmetic, wealth tracking, transaction logging
  gotcha: Use Decimal for all DOT amounts, avoid float precision issues

- file: code/archon_adapter/adapter.py
  why: MCP tool integration patterns and circuit breaker usage
  pattern: Async service calls, health checking, error recovery
  gotcha: Circuit breaker state management, fallback handling

- file: code/jam_mock/interface.py
  why: Wealth tracking and on-chain simulation patterns
  pattern: Balance management, transaction logging, async operations
  gotcha: Decimal precision for DOT calculations

- url: https://github.com/coleam00/archon/blob/stable/docker-compose.yml
  why: Service orchestration and health check patterns
  critical: MCP service endpoints and configuration

- docfile: borglife-archon-strategy.md
  why: Phase 1 architecture and integration requirements
  section: Part 3 - Technical Architecture, Part 6 - Success Metrics
```

### Current Codebase tree

```bash
code/synthesis/
├── __init__.py                 # Synthesis module exports
├── dna_parser.py              # DNA parsing (currently mocked)
├── dna_validator.py           # DNA validation logic
├── phenotype_builder.py       # Phenotype construction (currently mocked)
├── phenotype_encoder.py       # DNA encoding utilities
└── cell_organ_protocol.py     # Cell-organ communication protocol
```

### Desired Codebase tree with files to be added and responsibility of file

```bash
code/synthesis/
├── __init__.py                 # Export all synthesis components
├── dna_parser.py              # COMPLETE: DNA parsing, validation, canonical serialization
├── dna_validator.py           # COMPLETE: Schema validation, integrity checks
├── phenotype_builder.py       # COMPLETE: Cell instantiation, organ injection, cost calculation
├── phenotype_encoder.py       # COMPLETE: DNA encoding, on-chain storage preparation
├── cell_organ_protocol.py     # COMPLETE: Cell-organ communication, task orchestration
├── exceptions.py              # NEW: Synthesis-specific exceptions
└── types.py                   # NEW: Type definitions for synthesis components
```

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: Async initialization required for all synthesis components
# All builders, parsers, and protocols need async initialize() calls

# CRITICAL: DNA hash computation requires canonical YAML serialization
# Use yaml.dump(..., sort_keys=True, default_flow_style=False) for consistency

# CRITICAL: Decimal precision for all cost calculations
# Never use float for DOT amounts - always use Decimal with proper precision

# CRITICAL: Circuit breaker integration for external service calls
# All MCP tool calls must go through circuit breaker protection

# CRITICAL: Cell-organ bridge protocol for seamless integration
# Cells and organs communicate through standardized async interfaces

# CRITICAL: Resource cleanup on phenotype destruction
# Proper async cleanup to prevent resource leaks in long-running borgs
```

## Implementation Blueprint

### Data models and structure

```python
# Core data structures for synthesis components

@dataclass
class BorgDNA:
    """Complete Borg DNA structure."""
    header: DNAHeader
    cells: List[BorgCell]
    organs: List[BorgOrgan]
    manifesto_hash: str

@dataclass
class DNAHeader:
    """DNA header with metadata."""
    code_length: int
    gas_limit: int
    service_index: str

@dataclass
class BorgCell:
    """Individual cell configuration."""
    name: str
    logic_type: str  # "rag_agent", "decision_maker", "data_processor"
    parameters: Dict[str, Any]
    cost_estimate: Decimal

@dataclass
class BorgOrgan:
    """Organ configuration with MCP binding."""
    name: str
    mcp_tool: str  # MCP tool identifier
    url: str       # MCP service URL
    abi_version: str
    price_cap: Decimal

@dataclass
class BorgPhenotype:
    """Executable phenotype with cells and organs."""
    cells: Dict[str, BorgCell]
    organs: Dict[str, BorgOrgan]
    total_cost: Decimal
    service_index: str

class DNAParsingError(Exception):
    """DNA parsing specific errors."""
    pass

class PhenotypeBuildError(Exception):
    """Phenotype building specific errors."""
    pass
```

### Implementation Tasks (Complete - 12 Tasks with Proper Dependencies)

**Infrastructure Already Available:**
- ✅ Pydantic for data validation
- ✅ Asyncio for concurrent operations
- ✅ YAML/JSON parsing libraries
- ✅ Decimal for precision arithmetic
- ✅ Logging infrastructure

```yaml
Task 1: DNA Parser Core Implementation
  - IMPLEMENT: dna_parser.py with YAML parsing, validation, canonical serialization
  - INCLUDE: DNAParsingError exception class, round-trip integrity validation
  - VALIDATE: All test_dna_samples.yaml configurations parse correctly
  - DEPENDS: None (foundational component)

Task 2: DNA Validator Implementation
  - IMPLEMENT: dna_validator.py with schema validation and integrity checks
  - INCLUDE: Header validation, cell/organ structure validation, hash verification
  - INTEGRATE: With dna_parser.py for comprehensive validation
  - DEPENDS: Task 1 (needs parser to validate)

Task 3: Cell-Organ Protocol Foundation
  - IMPLEMENT: cell_organ_protocol.py with communication interfaces
  - DEFINE: AsyncCell, AsyncOrgan protocols, task execution coordination
  - INCLUDE: Error propagation, resource management, cleanup patterns
  - DEPENDS: None (independent protocol layer)

Task 4: Phenotype Builder Core
  - IMPLEMENT: phenotype_builder.py cell instantiation logic
  - INCLUDE: Cell creation from DNA, async initialization patterns
  - INTEGRATE: With cell_organ_protocol.py for proper interfaces
  - DEPENDS: Task 3 (needs protocol for cell communication)

Task 5: Organ Injection System
  - IMPLEMENT: MCP tool binding in phenotype_builder.py
  - INCLUDE: Archon adapter integration, circuit breaker protection
  - SUPPORT: Docker MCP organs and external service integration
  - DEPENDS: Task 4 (needs basic cell instantiation)

Task 6: Cost Calculation Engine
  - IMPLEMENT: Cost calculation in phenotype_builder.py
  - INCLUDE: Cell costs, organ price caps, total phenotype costing
  - VALIDATE: Decimal precision, economic model compliance
  - DEPENDS: Task 5 (needs organ injection for price cap calculations)

Task 7: Phenotype Encoder Implementation
  - IMPLEMENT: phenotype_encoder.py for DNA encoding preparation
  - INCLUDE: On-chain storage formatting, hash computation
  - INTEGRATE: With JAM interface for storage operations
  - DEPENDS: Task 1 (needs DNA parser for encoding)

Task 8: Synthesis Module Integration
  - UPDATE: synthesis/__init__.py to export all components
  - CREATE: synthesis/exceptions.py and synthesis/types.py
  - VALIDATE: All imports work correctly in test environment
  - DEPENDS: Tasks 1-7 (needs all components implemented)

Task 9: Proto-Borg Integration
  - UPDATE: proto_borg.py to use real synthesis components
  - REMOVE: Mock fallbacks, enable real DNA parsing and phenotype building
  - VALIDATE: Borg initialization works with real components
  - DEPENDS: Task 8 (needs complete synthesis module)

Task 10: Test Suite Updates
  - UPDATE: All test files to remove mock fallbacks
  - ENABLE: Real component testing in test_dna_integrity.py, test_economic_model.py
  - VALIDATE: Tests pass with real implementations
  - DEPENDS: Task 9 (needs integrated proto_borg)

Task 11: Error Handling & Recovery
  - IMPLEMENT: Comprehensive error handling across all synthesis components
  - INCLUDE: Circuit breaker integration, graceful degradation, recovery patterns
  - TEST: Error scenarios and recovery mechanisms
  - DEPENDS: Tasks 1-10 (needs all components for integration testing)

Task 12: Performance Optimization & Validation
  - OPTIMIZE: Async patterns, resource usage, execution speed
  - VALIDATE: 5-minute E2E execution limit, memory efficiency
  - DOCUMENT: Performance characteristics and optimization opportunities
  - DEPENDS: Tasks 1-11 (needs complete implementation for optimization)
```

### Implementation Patterns & Key Details

```python
# DNA Parser implementation pattern
class DNAParser:
    async def parse_dna(self, dna_config: Dict[str, Any]) -> BorgDNA:
        """Parse DNA configuration into BorgDNA object."""
        # Validate structure
        self._validate_dna_structure(dna_config)

        # Parse header
        header = DNAHeader(
            code_length=dna_config['header']['code_length'],
            gas_limit=dna_config['header']['gas_limit'],
            service_index=dna_config['header']['service_index']
        )

        # Parse cells
        cells = []
        for cell_config in dna_config.get('cells', []):
            cell = BorgCell(
                name=cell_config['name'],
                logic_type=cell_config['logic_type'],
                parameters=cell_config.get('parameters', {}),
                cost_estimate=Decimal(str(cell_config['cost_estimate']))
            )
            cells.append(cell)

        # Parse organs
        organs = []
        for organ_config in dna_config.get('organs', []):
            organ = BorgOrgan(
                name=organ_config['name'],
                mcp_tool=organ_config['mcp_tool'],
                url=organ_config['url'],
                abi_version=organ_config['abi_version'],
                price_cap=Decimal(str(organ_config['price_cap']))
            )
            organs.append(organ)

        return BorgDNA(
            header=header,
            cells=cells,
            organs=organs,
            manifesto_hash=dna_config['manifesto_hash']
        )

# Phenotype Builder implementation pattern
class PhenotypeBuilder:
    def __init__(self, archon_adapter):
        self.archon_adapter = archon_adapter

    async def build_phenotype(self, dna: BorgDNA) -> BorgPhenotype:
        """Build executable phenotype from DNA."""
        # Initialize cells
        cells = {}
        for cell_config in dna.cells:
            cell = await self._create_cell(cell_config)
            cells[cell_config.name] = cell

        # Initialize organs
        organs = {}
        for organ_config in dna.organs:
            organ = await self._create_organ(organ_config)
            organs[organ_config.name] = organ

        # Calculate total cost
        total_cost = self._calculate_total_cost(dna)

        return BorgPhenotype(
            cells=cells,
            organs=organs,
            total_cost=total_cost,
            service_index=dna.header.service_index
        )

# Cell-Organ Protocol implementation pattern
class AsyncCell(Protocol):
    """Protocol for cell implementations."""
    async def initialize(self) -> None:
        """Initialize cell resources."""
        ...

    async def execute_task(self, task: str, organs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using available organs."""
        ...

    async def cleanup(self) -> None:
        """Clean up cell resources."""
        ...

class AsyncOrgan(Protocol):
    """Protocol for organ implementations."""
    async def initialize(self) -> None:
        """Initialize organ connection."""
        ...

    async def call_tool(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool call."""
        ...

    async def get_status(self) -> Dict[str, Any]:
        """Get organ status and health."""
        ...

    async def cleanup(self) -> None:
        """Clean up organ connection."""
        ...
```

### Integration Points (Leveraging Existing Infrastructure)

```yaml
SERVICES (Already Running):
  - archon-server:8181 - Core data operations and MCP tools
  - archon-mcp:8051 - AI assistant tools and RAG queries
  - archon-agents:8052 - Cell execution and task processing
  - supabase - Data persistence and state management

PROTOCOLS (To Be Implemented):
  - Cell-Organ Bridge Protocol - Standardized async communication
  - MCP Tool Integration - Circuit breaker protected service calls
  - Cost Calculation Protocol - Decimal precision economic modeling
  - Error Recovery Protocol - Graceful degradation and recovery
```

## Validation Loop (Complete - 12 Tasks)

### Level 1: Component Implementation (Tasks 1-4 Complete)

```bash
cd borglife_proto_private/code
# Test individual component imports
python -c "from synthesis.dna_parser import DNAParser; print('✅ DNA Parser OK')"
python -c "from synthesis.phenotype_builder import PhenotypeBuilder; print('✅ Phenotype Builder OK')"
python -c "from synthesis.cell_organ_protocol import AsyncCell, AsyncOrgan; print('✅ Protocol OK')"
```

### Level 2: Integration Testing (Tasks 5-8 Complete)

```bash
cd borglife_proto_private/code
# Test synthesis module integration
python -c "import synthesis; print('✅ Synthesis module OK')"
python -c "from synthesis import DNAParser, PhenotypeBuilder; print('✅ Exports OK')"
```

### Level 3: Proto-Borg Integration (Tasks 9-10 Complete)

```bash
cd borglife_proto_private/code
# Test proto_borg with real synthesis components
python -c "
from proto_borg import ProtoBorgAgent, BorgConfig
config = BorgConfig(service_index='test-borg')
borg = ProtoBorgAgent(config)
print('✅ Proto-Borg integration OK')
"
```

### Level 4: End-to-End Validation (Tasks 11-12 Complete)

```bash
cd borglife_proto_private/code
# Run synthesis component tests
python -m pytest tests/test_dna_integrity.py -v --tb=short
python -m pytest tests/test_economic_model.py -v --tb=short
python -m pytest tests/e2e_test_suite.py -v --tb=short
```

## Final Validation Checklist

### Technical Validation

- [ ] All 12 implementation tasks completed successfully
- [ ] All synthesis components import and initialize without errors
- [ ] DNA parsing works for all test_dna_samples.yaml configurations
- [ ] Phenotype building creates executable borgs with cells and organs
- [ ] Cell-organ protocol enables proper task execution coordination
- [ ] Cost calculations use decimal precision and match economic model
- [ ] Error handling provides meaningful messages and recovery options

### Feature Validation

- [ ] Proto-borg can initialize with real synthesis components
- [ ] DNA-to-phenotype transformation works end-to-end
- [ ] Task execution through phenotype orchestration succeeds
- [ ] MCP tool integration works through circuit breaker protection
- [ ] Wealth tracking and cost deduction functions correctly
- [ ] Round-trip DNA integrity H(D') = H(D) maintained

### Code Quality Validation

- [ ] Follows existing codebase patterns and async conventions
- [ ] File placement matches desired codebase tree structure
- [ ] Anti-patterns avoided (no sync functions in async context)
- [ ] Dependencies properly managed and imported
- [ ] Configuration changes properly integrated

### Documentation & Testing

- [ ] Code is self-documenting with clear docstrings
- [ ] Comprehensive error logging for debugging
- [ ] Test coverage includes all synthesis components
- [ ] Performance benchmarks meet 5-minute execution requirement

---

## Anti-Patterns to Avoid

- ❌ Don't implement sync functions in async context
- ❌ Don't use float for any DOT/cost calculations
- ❌ Don't bypass circuit breaker protection for MCP calls
- ❌ Don't skip proper resource cleanup in async contexts
- ❌ Don't hardcode service URLs - use configuration
- ❌ Don't ignore error propagation in cell-organ communication
- ❌ Don't create tight coupling between cells and organs
- ❌ Don't forget decimal precision in cost calculations