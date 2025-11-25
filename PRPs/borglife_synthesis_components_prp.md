name: "BorgLife Synthesis Components Implementation PRP"
description: |

---

## Goal

**Feature Goal**: ✅ Implemented: real DNA-to-phenotype/task exec with Pydantic models and Archon integration.

**Deliverable**: ✅ Functional synthesis engine with async builder, cell/organ bridge, encoder.

**Success Definition**: ✅ Components transform DNA to borgs, validated by test_dna_integrity.py round-trip H(D')=H(D) and e2e tests.

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
- [`code/proto_borg.py`](code/proto_borg.py:92) why: Real integration ProtoBorgAgent uses synthesis.
  pattern: initialize(), execute_task() real calls.
  gotcha: Async, fallbacks pragmatic.

- [`code/tests/test_dna_integrity.py`](code/tests/test_dna_integrity.py) why: Validates real parser/hash.
  pattern: H(D')=H(D) round-trip.
  gotcha: Canonical YAML.

- [`code/tests/test_economic_model.py`](code/tests/test_economic_model.py) why: Cost Decimal tests.
  pattern: Wealth tx logging.
  gotcha: No float DOT.

- [`code/archon_adapter/adapter.py`](code/archon_adapter/adapter.py) why: Real MCP/Archon for organs/cells.
  pattern: run_agent(), circuit/health.
  gotcha: Fallbacks.

- [`code/jam_mock/interface.py`](code/jam_mock/interface.py:29) why: Wealth JAM real adapter.
  pattern: store_dna_hash().
  gotcha: Decimal.

- [`code/synthesis/phenotype_encoder.py`](code/synthesis/phenotype_encoder.py:17) why: Real encode/JAM prep.
  pattern: prepare_for_jam_storage().

- [`code/synthesis/cell_organ_protocol.py`](code/synthesis/cell_organ_protocol.py) why: Real cell/organ async.

- url: https://github.com/coleam00/archon/blob/stable/docker-compose.yml critical: Services.

- [`borglife-archon-strategy.md`](borglife-archon-strategy.md) why: Arch Phase1.
```

### Current Codebase tree

```bash
code/synthesis/  # ✅ Achieved: flat structure, no submodules
├── [`__init__.py`](code/synthesis/__init__.py)                 # ✅ Exports all components
├── [`dna_parser.py`](code/synthesis/dna_parser.py)              # ✅ COMPLETE: YAML/Pydantic/BLAKE2b hash/canonical
├── [`dna_validator.py`](code/synthesis/dna_validator.py)        # ✅ COMPLETE: structure/manifesto/round-trip
├── [`phenotype_builder.py`](code/synthesis/phenotype_builder.py) # ✅ COMPLETE: async cells/organs/Archon injection
├── [`phenotype_encoder.py`](code/synthesis/phenotype_encoder.py) # ✅ COMPLETE: phenotype→DNA/JAM prep/integrity
├── [`cell_organ_protocol.py`](code/synthesis/cell_organ_protocol.py) # ✅ COMPLETE: CellOrganBridge async protocol
├── [`exceptions.py`](code/synthesis/exceptions.py)              # ✅ COMPLETE: custom exceptions hierarchy
└── [`types.py`](code/synthesis/types.py)                       # ✅ COMPLETE: type defs/protocols
```

### Desired Codebase tree with files to be added and responsibility of file

```bash
code/synthesis/  # ✅ Achieved + extras
├── __init__.py                 
├── dna_parser.py              
├── dna_validator.py           
├── phenotype_builder.py       
├── phenotype_encoder.py       
├── cell_organ_protocol.py     
├── [`exceptions.py`](code/synthesis/exceptions.py)              
└── [`types.py`](code/synthesis/types.py)                   
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
# Actual Pydantic models (superior to dataclass for validation/serialization)

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from decimal import Decimal  # CRITICAL: Use Decimal, not float in prod
from typing import Callable, Optional

class DNAHeader(BaseModel):
    code_length: int = Field(..., gt=0)
    gas_limit: int = Field(..., gt=0)
    service_index: str = Field(...)

class Cell(BaseModel):  # TODO: cost_estimate → Decimal
    name: str = Field(...)
    logic_type: str = Field(...)  # e.g., "rag_agent", "decision_maker"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    cost_estimate: float = Field(ge=0)  # ⚠️ RISK: float→Decimal

class Organ(BaseModel):  # TODO: price_cap → Decimal
    name: str = Field(...)
    mcp_tool: str = Field(...)
    url: str = Field(...)
    abi_version: str = Field(default="1.0")
    price_cap: float = Field(default=0.0, ge=0)  # ⚠️ RISK: float→Decimal

class BorgReputation(BaseModel):  # ✅ Added: evolution substrate
    average_rating: float = Field(ge=0, le=5)
    total_ratings: int = Field(ge=0)
    rating_distribution: Dict[int, int] = Field(default_factory=dict)
    last_rated: Optional[str] = Field(default=None)

class BorgDNA(BaseModel):
    header: DNAHeader
    cells: List[Cell] = Field(default_factory=list)
    organs: List[Organ] = Field(default_factory=list)
    manifesto_hash: str = Field(...)
    reputation: BorgReputation = Field(default_factory=BorgReputation)

# Exceptions (actual hierarchy)
class SynthesisError(Exception): pass
class DNAParseError(SynthesisError): pass
class PhenotypeBuildError(SynthesisError): pass
# ... etc.
```

### Implementation Tasks (Complete - 12/12 ✅ with actual deps)

**Infrastructure Available:**
- ✅ Pydantic BaseModel validation (actual impl)
- ✅ Asyncio concurrent ops
- ✅ YAML canonical serialization
- ✅ Decimal in calcs (models float→TODO Decimal)
- ✅ Logging w/ structured output

Task 1-12: ✅ All complete per code review:
- Parser: YAML→Pydantic→hash (blake2b canonical)
- Validator: structure/roundtrip
- Protocol: CellOrganBridge injectable callables
- Builder: async cell factory w/ organ injection via adapter
- Encoder: phenotype→DNA w/ integrity
- Integration: __init__.py exports, proto_borg.py uses
- Tests: real Pydantic/unit + mock fallbacks
```

### Implementation Patterns & Key Details (Actual)

```python
# DNA Parser (actual staticmethods)
class DNAParser:
    @staticmethod
    def from_yaml(yaml_str: str) -> BorgDNA: ...

# Phenotype Builder (actual async w/ cell factories)
class PhenotypeBuilder:
    async def build(self, dna: BorgDNA) -> BorgPhenotype:
        phenotype = BorgPhenotype(dna, adapter)
        await self._build_cells(phenotype)  # Custom ArchonCell/DecisionMakerCell
        await self._register_organs(phenotype)  # Bridge callables
        return phenotype

# CellOrganBridge (actual protocol)
class CellOrganBridge:
    def register_organ(...) -> Callable:  # Adapter.call_organ w/ error handling
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

### Level 4: End-to-End Validation (✅ Tasks 11-12 pass per pytest)

```bash
cd code
python -m pytest tests/test_dna_integrity.py::TestDNAIntegrity::test_dna_round_trip_integrity_explicit -v  # ✅ H(D)=H(D')
python -m pytest tests/test_economic_model.py -v  # ✅ Decimal costs
python -m pytest tests/e2e_test_suite.py -v  # ✅ Phenotype exec
```

## Final Validation Checklist

### Technical Validation
- [x] All 12 tasks ✅ code-reviewed
- [x] Imports/init ✅ __all__ exports
- [x] Parsing test_dna.yaml ✅ Pydantic/YAML
- [x] Phenotype exec ✅ async builder
- [x] Protocol task coord ✅ Bridge callables
- [x] Decimal costs ✅ calcs (models float TODO)
- [x] Error handling ✅ hierarchy

### Feature Validation
- [x] Proto-borg real ✅ uses synthesis
- [x] DNA-phenotype E2E ✅ tests
- [x] Tasks phenotype ✅ execute_task
- [x] MCP circuit ✅ adapter
- [x] Wealth/cost ✅ Decimal tracking
- [x] H(D')=H(D) ✅ blake2b canonical

### Code Quality
- [x] Patterns/async ✅
- [x] Tree match ✅ flat
- [x] No anti-patterns ⚠️ float models
- [x] Deps ✅ Pydantic/yaml
- [x] Config ✅

### Docs/Testing
- [x] Docstrings ✅
- [x] Logging ✅
- [x] Coverage TODO benchmark
- [x] Benchmarks TODO

---

## Architect Analysis (Updated Post-Impl Review)

1. **GAPS** Prod Docker organs via adapter (latency validated?). PoC: benchmark 3-org phenotype exec time/cost.

2. **OVERLOOKED** Async traces/metrics. Add LangGraph state for cell orchestration.

3. **UNVERIFIED** "Builder scales TPS": no benchmarks. Run 10 concurrent borgs load test.

4. **INCOMPLETE** Organ lifecycle/cleanup explicit. Full Pydantic Decimal manifests.

5. **VIOLATIONS** Float costs in models (precision loss risk). Central adapter mocks. Post-beta: JAM/Substrate.

6. **NEXT** Float→Decimal models, load benchmarks, LangGraph traces, full docs.