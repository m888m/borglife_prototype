name: "BorgLife Phase 1 End-to-End Test Implementation PRP"
description: |

---

## Goal

**Feature Goal**: Implement comprehensive end-to-end testing for BorgLife Phase 1 demo flow (funding → borg creation → task execution → DNA encoding → on-chain storage → decoding validation)

**Deliverable**: Complete test suite that validates the entire BorgLife Phase 1 user journey using Archon infrastructure, ensuring 100% success rate for demo scenarios

**Success Definition**: All test scenarios pass consistently, demo flow executes successfully from start to finish, and round-trip DNA integrity (H(D') = H(D)) is maintained

## User Persona (if applicable)

**Target User**: BorgLife Phase 1 sponsors and demo participants

**Use Case**: Validating that the complete BorgLife Phase 1 demo works end-to-end before public demonstrations

**User Journey**:
1. Start Archon services
2. Run end-to-end test suite
3. Review test results and identify any failures
4. Fix identified issues
5. Re-run tests until 100% pass rate
6. Proceed with live demos

**Pain Points Addressed**: Uncertainty about demo reliability, fear of public demo failures, difficulty identifying integration issues

## Why

- **Business value**: Ensures BorgLife Phase 1 demos are reliable and impressive for sponsors
- **Integration with existing features**: Leverages existing BorgLife prototype code and Archon infrastructure
- **Problems this solves**: Prevents demo failures, identifies integration issues early, provides confidence in system stability

## What

End-to-end test suite that validates:
- Archon service health and connectivity
- BorgLife component initialization
- Complete demo flow: funding → creation → execution → encoding → storage → decoding
- DNA integrity validation (H(D') = H(D))
- Economic model correctness (wealth tracking, cost calculation)
- Error handling and recovery scenarios
- Performance benchmarks for demo scenarios

### Success Criteria

- [ ] All 5 core demo scenarios execute successfully
- [ ] DNA round-trip integrity maintained (H(D') = H(D))
- [ ] Economic calculations accurate within 0.001 DOT
- [ ] Test execution completes within 5 minutes
- [ ] No service crashes or hangs during testing
- [ ] Comprehensive error reporting for failures

## All Needed Context

### Context Completeness Check

_Before writing this PRP, validate: "If someone knew nothing about this codebase, would they have everything needed to implement this successfully?"_

### Documentation & References

```yaml
- file: ../borglife/borglife_proto_private/code/proto_borg.py
  why: Core ProtoBorgAgent implementation and lifecycle management
  pattern: Wealth tracking, task execution, DNA management patterns
  gotcha: Async initialization required before use

- file: ../borglife/borglife_proto_private/code/synthesis/dna_parser.py
  why: DNA parsing, validation, and round-trip integrity checking
  pattern: Pydantic model validation, hash computation
  gotcha: YAML canonical serialization for consistent hashing

- file: ../borglife/borglife_proto_private/code/synthesis/phenotype_builder.py
  why: Phenotype construction from DNA with cell/organ injection
  pattern: Async cell building, organ callable registration
  gotcha: Cell-organ bridge protocol for seamless integration

- file: ../borglife/borglife_proto_private/code/archon_adapter/adapter.py
  why: Archon service integration with circuit breakers and fallbacks
  pattern: HTTP client with retry logic, health checking
  gotcha: Circuit breaker state management and recovery

- file: ../borglife/borglife_proto_private/code/jam_mock/interface.py
  why: JAM mock interface for wealth tracking and on-chain simulation
  pattern: Wealth balance management, transaction logging
  gotcha: Decimal precision for DOT calculations

- file: ../borglife/borglife_proto_private/code/demo_scenarios.py
  why: Existing demo metrics and test patterns
  pattern: Demo execution tracking, success/failure metrics
  gotcha: Async context management for service lifecycles

- url: https://github.com/coleam00/archon/blob/stable/docker-compose.yml
  why: Archon service orchestration and health check patterns
  critical: Service dependency management and startup ordering

- docfile: ../borglife/borglife_proto_private/borglife-archon-strategy.md
  why: Phase 1 requirements and integration architecture
  section: Part 6 - Success Metrics & Monitoring
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase

```bash
../borglife/borglife_proto_private/code/
├── .env.example
├── =2.0.0
├── =6.0
├── archon_adapter/
│   ├── __init__.py
│   ├── adapter.py
│   ├── cache_manager.py
│   ├── compatibility_matrix.py
│   ├── config.py
│   ├── dependency_monitor.py
│   ├── docker_discovery.py
│   ├── docker_mcp_auth.py
│   ├── docker_mcp_billing.py
│   ├── docker_monitor.py
│   ├── exceptions.py
│   ├── fallback_manager.py
│   ├── health.py
│   ├── mcp_client.py
│   ├── version.py
├── billing/
├── borg_designer_ui.py
├── borg_dna.yaml
├── borg_lifecycle/
│   ├── __init__.py
│   ├── manager.py
├── demo_scenarios.py
├── docker-compose.yml
├── FUNCTION_ARCHITECTURE_OVERVIEW.md
├── jam_mock/
│   ├── __init__.py
│   ├── interface.py
│   ├── kusama_adapter.py
│   ├── local_mock.py
│   ├── recovery.py
├── monitoring/
├── project_management/
├── proto_borg.py
├── README.md
├── reputation/
├── requirements.txt
├── scripts/
├── security/
├── sponsor_ui.py
├── synthesis/
│   ├── __init__.py
│   ├── cell_organ_protocol.py
│   ├── dna_parser.py
│   ├── dna_validator.py
│   ├── phenotype_builder.py
│   ├── phenotype_encoder.py
├── tests/
├── TROUBLESHOOTING.md
```

### Desired Codebase tree with files to be added and responsibility of file

```bash
../borglife/borglife_proto_private/code/
├── .env.test                       # Test environment configuration
├── tests/
│   ├── __init__.py
│   ├── e2e_test_suite.py           # Main test orchestrator (funding → creation → execution → encoding → storage → decoding)
│   ├── test_service_integration.py # Archon/BorgLife integration tests
│   ├── test_dna_integrity.py       # DNA round-trip validation H(D') = H(D)
│   ├── test_economic_model.py      # Wealth tracking and cost validation (within 0.001 DOT)
│   ├── test_error_handling.py      # Circuit breaker recovery, timeouts, async context management
│   ├── fixtures/
│   │   ├── test_dna_samples.yaml   # Test DNA configurations (minimal, complex, edge cases)
│   │   ├── demo_tasks.json         # Test task scenarios with expected outcomes
│   │   └── expected_results.json   # Expected test outcomes and validation criteria
│   └── conftest.py                 # Pytest fixtures (existing - enhanced with test-specific setup)
├── scripts/
│   ├── run_e2e_tests.sh           # Test execution script with service management
│   └── validate_demo_readiness.sh # Pre-demo validation with comprehensive checks
└── tests/README.md                # Test documentation and troubleshooting guide
```

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: Async initialization required for all BorgLife components
# All services (Archon adapter, phenotype builder, JAM) need async initialize() calls

# CRITICAL: Circuit breaker state in Archon adapter can cause test flakes
# Reset circuit breakers between tests to ensure clean state

# CRITICAL: DNA hash computation requires canonical YAML serialization
# Use yaml.dump(..., sort_keys=True) for consistent hashing

# CRITICAL: Wealth calculations use Decimal for precision
# Never use float for DOT amounts - always use Decimal

# CRITICAL: Service health checks need time to stabilize
# Add asyncio.sleep(2) after service startup before health checks

# CRITICAL: Docker MCP organs may not be available in test environment
# Mock organ responses or ensure Docker containers are running
```

## Implementation Blueprint

### Data models and structure

Create the core data models for test scenarios and validation:

```python
# tests/fixtures/demo_tasks.json
{
  "scenarios": [
    {
      "name": "basic_rag_task",
      "description": "Test basic RAG functionality with knowledge retrieval",
      "task": "Summarize the key evolution mechanisms in BorgLife whitepaper sections 4-7",
      "expected_cell": "rag_agent",
      "expected_cost_range": [0.0005, 0.002],
      "timeout": 30
    },
    {
      "name": "decision_making_task",
      "description": "Test decision making cell with complex reasoning",
      "task": "As a borg, decide whether to prioritize research or business development given limited resources",
      "expected_cell": "decision_maker",
      "expected_cost_range": [0.0008, 0.003],
      "timeout": 45
    }
  ]
}

# tests/fixtures/test_dna_samples.yaml
test_dna_minimal:
  header:
    code_length: 1024
    gas_limit: 1000000
    service_index: "test-borg-001"
  cells:
    - name: "basic_agent"
      logic_type: "rag_agent"
      parameters: {"model": "gpt-4", "max_tokens": 500}
      cost_estimate: 0.001
  organs: []
  manifesto_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

test_dna_complex:
  header:
    code_length: 2048
    gas_limit: 2000000
    service_index: "test-borg-002"
  cells:
    - name: "data_processor"
      logic_type: "data_processor"
      parameters: {"model": "gpt-4", "max_tokens": 500}
      cost_estimate: 0.001
    - name: "decision_maker"
      logic_type: "decision_maker"
      parameters: {"strategy": "utility_maximization"}
      cost_estimate: 0.0005
  organs:
    - name: "knowledge_base"
      mcp_tool: "archon:perform_rag_query"
      url: "http://archon-mcp:8051"
      abi_version: "1.0"
      price_cap: 0.0001
  manifesto_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
```

### Implementation Tasks (Complete - 9 Tasks with Proper Dependencies)

**Infrastructure Already Available:**
- ✅ Supabase database (via Archon)
- ✅ Docker Compose services (archon-server, archon-mcp, archon-agents)
- ✅ Test framework setup (pytest, existing conftest.py)
- ✅ Service health checks and startup scripts

```yaml
Task 1: Environment Setup
  - IMPLEMENT: .env.test file with E2E_TEST_TIMEOUT=300, E2E_TEST_PARALLEL=false
  - VALIDATE: Python dependencies and required packages
  - PLACEMENT: Root directory
  - DEPENDS: None (critical prerequisite)

Task 2: Infrastructure Verification
  - VERIFY: Docker services running (archon-server:8181, archon-mcp:8051, archon-agents:8052)
  - VALIDATE: Supabase connectivity and .env configuration
  - CHECK: BorgLife dependencies available
  - DEPENDS: Task 1 (environment setup)

Task 3: Test Fixtures & Data
  - IMPLEMENT: test_dna_samples.yaml, demo_tasks.json, expected_results.json
  - FOLLOW: Existing borg_dna.yaml and demo_scenarios.py patterns
  - PLACEMENT: tests/fixtures/
  - DEPENDS: Task 2 (infrastructure verified)

Task 4: Core Test Modules
  - IMPLEMENT: test_service_integration.py, test_dna_integrity.py, test_economic_model.py
  - INCLUDE: Circuit breaker reset logic, async initialization patterns, decimal precision
  - LEVERAGE: Existing conftest.py Supabase mocking
  - DEPENDS: Task 3 (fixtures available)

Task 5: Error Handling & Recovery Tests
  - IMPLEMENT: test_error_handling.py for circuit breaker recovery, timeouts, async context
  - ADDRESS: All gotchas from PRP (circuit breakers, async init, decimal precision)
  - DEPENDS: Task 4 (core modules exist)

Task 6: E2E Orchestrator
  - IMPLEMENT: e2e_test_suite.py with complete demo flow (funding → creation → execution → encoding → storage → decoding)
  - INTEGRATE: With existing Docker Compose setup and Supabase mocking
  - DEPENDS: Task 5 (error handling implemented)

Task 7: Execution Scripts
  - IMPLEMENT: run_e2e_tests.sh and validate_demo_readiness.sh
  - INCLUDE: Comprehensive health checks, service validation, error reporting
  - LEVERAGE: docker-compose.yml already handles services
  - DEPENDS: Task 6 (orchestrator complete)

Task 8: Documentation
  - IMPLEMENT: tests/README.md with structure, execution instructions, troubleshooting
  - FOLLOW: Existing codebase documentation patterns
  - DEPENDS: Task 7 (all components exist)

Task 9: Final Validation
  - EXECUTE: Complete validation loop with all PRP success criteria
  - VALIDATE: DNA integrity H(D')=H(D), economic accuracy within 0.001 DOT, 5-minute execution
  - DEPENDS: Tasks 1-8 (all components complete)
```

### Implementation Patterns & Key Details

```python
# Critical patterns for E2E testing

# Service lifecycle management pattern
async def setup_test_services():
    """Setup pattern for reliable service initialization"""
    # Start Archon services first
    await start_archon_services()
    await asyncio.sleep(5)  # Allow stabilization

    # Initialize BorgLife components
    adapter = ArchonServiceAdapter()
    await adapter.initialize()

    # Verify health before proceeding
    health = await adapter.check_health()
    assert health['overall'], f"Services not healthy: {health}"

    return adapter

# DNA integrity validation pattern
def validate_dna_round_trip(original_dna: BorgDNA) -> bool:
    """Critical pattern for DNA integrity validation"""
    # Serialize with canonical formatting
    yaml_str = DNAParser.to_yaml(original_dna)

    # Parse back
    parsed_dna = DNAParser.from_yaml(yaml_str)

    # Compare hashes for integrity
    original_hash = original_dna.compute_hash()
    parsed_hash = parsed_dna.compute_hash()

    return original_hash == parsed_hash

# Economic validation pattern
def validate_economic_accuracy(borg: ProtoBorgAgent, expected_cost: Decimal, tolerance: Decimal = Decimal('0.001')):
    """Pattern for economic model validation"""
    actual_balance = borg.wealth.get_balance()
    expected_balance = borg.config.initial_wealth - expected_cost

    # Use absolute difference for precision
    difference = abs(actual_balance - expected_balance)
    assert difference <= tolerance, f"Economic inaccuracy: {difference} > {tolerance}"

# Demo flow orchestration pattern
async def execute_demo_flow(borg_id: str, dna_config: dict, task: str) -> dict:
    """Complete demo flow execution pattern"""
    # 1. Initialize services
    adapter = await setup_test_services()

    # 2. Create borg with funding
    borg = ProtoBorgAgent(BorgConfig(service_index=borg_id))
    await borg.initialize()

    # 3. Load and validate DNA
    dna = DNAParser.from_yaml(yaml.dump(dna_config))
    assert dna.validate_integrity()

    # 4. Build phenotype
    phenotype = await adapter.phenotype_builder.build(dna)
    borg.phenotype = phenotype

    # 5. Execute task
    result = await borg.execute_task(task)

    # 6. Validate economics
    validate_economic_accuracy(borg, Decimal(str(result['cost'])))

    # 7. Test DNA encoding/decoding
    encoded_dna = await borg.update_dna(DNAParser.to_yaml(dna))
    assert validate_dna_round_trip(dna)

    return {
        'success': True,
        'result': result,
        'economic_valid': True,
        'dna_integrity': True
    }
```

### Integration Points (Leveraging Existing Infrastructure)

```yaml
SERVICES (Already Running):
  - archon-server: REST API (port 8181) - handles all data operations
  - archon-mcp: MCP protocol (port 8051) - AI assistant tools
  - archon-agents: PydanticAI (port 8052) - cell execution
  - supabase: Database (via Archon) - all data persistence

DOCKER_COMPOSE: Use existing docker-compose.yml
TEST_FRAMEWORK: Leverage existing conftest.py with Supabase mocking
```

## Validation Loop (Complete - 9 Tasks)

### Level 1: Environment & Dependencies (Task 1 Complete)

```bash
cd ../borglife/borglife_proto_private/code
# Verify .env.test exists and dependencies installed
python -c "import pytest, yaml, archon_adapter, synthesis; print('✅ Dependencies OK')"
```

### Level 2: Infrastructure Verification (Task 2 Complete)

```bash
# Services should be running via Docker Compose
curl -f http://localhost:8181/health && echo "✅ Archon Server OK"
curl -f http://localhost:8051/health && echo "✅ Archon MCP OK"
curl -f http://localhost:8052/health && echo "✅ Archon Agents OK"
```

### Level 3: Component Testing (Tasks 3-5 Complete)

```bash
cd ../borglife/borglife_proto_private/code
python -m pytest tests/test_service_integration.py -v
python -m pytest tests/test_dna_integrity.py -v
python -m pytest tests/test_economic_model.py -v
python -m pytest tests/test_error_handling.py -v
```

### Level 4: Integration Testing (Tasks 6-7 Complete)

```bash
cd ../borglife/borglife_proto_private
# Run complete E2E test suite
./code/scripts/run_e2e_tests.sh
```

### Level 5: Demo Readiness & Documentation (Tasks 8-9 Complete)

```bash
# Final validation before demos
./code/scripts/validate_demo_readiness.sh

# Verify documentation
test -f ./code/tests/README.md && echo "✅ Documentation complete"
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] No linting errors: `python -m ruff check .`
- [ ] No type errors: `python -m mypy .`
- [ ] No formatting issues: `python -m ruff format . --check`

### Feature Validation

- [ ] All success criteria from "What" section met
- [ ] Manual testing successful: `./scripts/run_e2e_tests.sh`
- [ ] Error cases handled gracefully with proper error messages
- [ ] Integration points work as specified
- [ ] Demo scenarios execute reliably with 100% success rate

### Code Quality Validation

- [ ] Follows existing codebase patterns and naming conventions
- [ ] File placement matches desired codebase tree structure
- [ ] Anti-patterns avoided (check against Anti-Patterns section)
- [ ] Dependencies properly managed and imported
- [ ] Configuration changes properly integrated

### Documentation & Deployment

- [ ] Code is self-documenting with clear variable/function names
- [ ] Logs are informative but not verbose
- [ ] Environment variables documented if new ones added

---

## Anti-Patterns to Avoid

- ❌ Don't create new patterns when existing ones work
- ❌ Don't skip validation because "it should work"
- ❌ Don't ignore failing tests - fix them
- ❌ Don't use sync functions in async context
- ❌ Don't hardcode values that should be config
- ❌ Don't catch all exceptions - be specific
- ❌ Don't test happy path only - include error scenarios
- ❌ Don't forget service cleanup between tests
- ❌ Don't assume service availability - check health first
- ❌ Don't compare floating point numbers directly - use tolerance