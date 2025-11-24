# BorgLife Phase 1 End-to-End Test Suite

This directory contains the comprehensive end-to-end testing framework for BorgLife Phase 1, validating the complete demo flow from funding through DNA encoding and on-chain storage.

## 🏗️ Test Structure

```
tests/
├── __init__.py                          # Python package initialization
├── conftest.py                          # Pytest fixtures and configuration
├── e2e_test_suite.py                    # Main E2E orchestrator (400+ lines)
├── README.md                           # This documentation
├── fixtures/                           # Test data and configurations
│   ├── __init__.py
│   ├── demo_tasks.json                 # Demo scenario definitions
│   ├── test_dna_samples.yaml           # DNA test configurations
│   └── expected_results.json           # Expected test outcomes
├── test_service_integration.py         # Archon service connectivity tests
├── test_dna_integrity.py               # DNA parsing and validation tests
├── test_economic_model.py              # Wealth tracking and cost validation
├── test_error_handling.py              # Error scenarios and recovery tests
├── test_fixtures_setup.py              # Fixture validation tests
├── test_async_initialization.py        # Async lifecycle validation
├── test_demo_scenarios.py              # End-to-end demo execution
├── test_concurrent_execution.py        # Concurrent borg execution tests
└── test_performance.py                 # Performance benchmarks
```

## 🎯 Test Objectives

The test suite validates BorgLife Phase 1's core requirements:

- **Complete Demo Flow**: Funding → Creation → Execution → Encoding → Storage → Decoding
- **DNA Integrity**: H(D') = H(D) round-trip validation
- **Economic Accuracy**: Cost calculations within 0.001 DOT tolerance
- **Service Reliability**: No crashes or hangs during execution
- **Performance**: All tests complete within 5 minutes

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Archon services running
- All test fixtures present

### Environment Setup

1. **Navigate to project root:**
   ```bash
   cd borglife_proto_private/code
   ```

2. **Ensure services are running:**
   ```bash
   # From project root
   docker-compose up -d
   ```

3. **Validate environment:**
   ```bash
   ./scripts/validate_demo_readiness.sh --verbose
   ```

### Running Tests

#### Full E2E Test Suite
```bash
# Run complete E2E validation
./scripts/run_e2e_tests.sh --verbose

# Run without Docker services (development mode)
./scripts/run_e2e_tests.sh --no-docker --verbose

# Generate reports only
./scripts/run_e2e_tests.sh --report-only
```

#### Individual Test Execution
```bash
# Run specific test file
python -m pytest tests/test_service_integration.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run specific test method
python -m pytest tests/e2e_test_suite.py::TestE2ETestSuite::test_individual_scenario_execution -v
```

#### Development Testing
```bash
# Run tests in watch mode
python -m pytest tests/ -v --watch

# Run with debugging
python -m pytest tests/ -v -s --pdb
```

## 🔄 Post-Archon Decoupling Test Status (2025-11-23)

**Status**: Partial success - Archon decoupled, main flow executes mocks (0/5 success due JAM gaps).

**Latest Report** (ARCHON_ENABLED=false):
```
Total Tests: 5
Successful: 0
Failed: 5
Success Rate: 0.0%
PRP: Fail scenarios/integrity/economic, Pass time/error reporting
```

**Failures**:
- demo_flow: JAMInterface no update_wealth (mock incomplete)
- individual: same
- usdb_asset: pallet "Assets" not found (substrate config)
- usdb_dist: dotenv import 'create_client' error
- inter_borg: jam_mock.kusama_adapter missing (use westend_adapter?)
- economic_validation: EconomicValidator missing args
- transaction_manager: TransactionManager missing args
- teardown: CacheManager no close

**Next Steps**:
1. Impl JAM mock methods (update_wealth etc.)
2. Fix substrate pallet (Assets Hub RPC?)
3. Fix imports/args in phase2a tests
4. Add CacheManager.close()
5. Run with ARCHON_ENABLED=true for full validation

**Verification**:
```bash
export ARCHON_ENABLED=false
pytest tests/e2e_test_suite.py -v
```

## 📋 Test Categories

1. E2E Orchestrator (`e2e_test_suite.py`)
2. Service Integration (`test_service_integration.py`)
3. DNA Integrity (`test_dna_integrity.py`)
4. Economic Model (`test_economic_model.py`)
5. Error Handling (`test_error_handling.py`)
6. Fixture Validation (`test_fixtures_setup.py`)
7. Async Initialization (`test_async_initialization.py`)
8. Demo Scenarios (`test_demo_scenarios.py`)
9. Concurrent Execution (`test_concurrent_execution.py`)
10. Performance (`test_performance.py`)

## 🔧 Configuration

### Environment Variables

Create `.env.test` in the project root:

```bash
# BorgLife E2E Test Environment
E2E_TEST_TIMEOUT=300
E2E_TEST_PARALLEL=false
LOG_LEVEL=INFO

# Archon Service URLs
ARCHON_SERVER_URL=http://localhost:8181
ARCHON_MCP_URL=http://localhost:8051
ARCHON_AGENTS_URL=http://localhost:8052
```

### Test Fixtures

#### Demo Tasks (`fixtures/demo_tasks.json`)
```json
{
  "scenarios": [
    {
      "name": "basic_funding_execution",
      "task": "Analyze the evolution mechanisms in BorgLife",
      "expected_cost_range": [0.001, 0.010]
    }
  ]
}
```

#### DNA Samples (`fixtures/test_dna_samples.yaml`)
```yaml
test_dna_minimal:
  header:
    code_length: 1024
  cells: []
  organs: []

test_dna_complex:
  header:
    code_length: 2048
  cells:
    - type: "neuron"
      connections: 1000
  organs:
    - type: "brain"
      cells: 100
```

## 📊 Test Reports

### E2E Test Report
Generated automatically by `run_e2e_tests.sh`:

```
Test Summary:
  Total Tests: 5
  Successful: 5
  Failed: 0
  Success Rate: 100.0%
  Execution Time: 142.50s
  DNA Integrity Rate: 100.0%
  Economic Accuracy Rate: 100.0%

PRP SUCCESS CRITERIA:
  ✅ All 5 core demo scenarios execute successfully
  ✅ DNA round-trip integrity maintained
  ✅ Economic calculations accurate within 0.001 DOT
  ✅ Test execution completes within 5 minutes
  ✅ No service crashes or hangs
  ✅ Comprehensive error reporting for failures
```

### Coverage Reports
```bash
# Generate HTML coverage report
python -m pytest tests/ --cov=. --cov-report=html
# View: open htmlcov/index.html
```

## 🐛 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check Docker services
docker-compose ps

# View service logs
docker-compose logs archon-server
docker-compose logs archon-mcp

# Restart services
docker-compose restart
```

#### Test Timeouts
```bash
# Increase timeout for slow environments
export E2E_TEST_TIMEOUT=600
./scripts/run_e2e_tests.sh
```

#### Fixture Validation Errors
```bash
# Validate JSON fixtures
python -c "import json; json.load(open('tests/fixtures/demo_tasks.json'))"

# Validate YAML fixtures
python -c "import yaml; yaml.safe_load(open('tests/fixtures/test_dna_samples.yaml'))"
```

#### Permission Issues
```bash
# Fix script permissions
chmod +x scripts/run_e2e_tests.sh
chmod +x scripts/validate_demo_readiness.sh
```

### Debug Mode
```bash
# Run with maximum verbosity
./scripts/run_e2e_tests.sh --verbose

# Run individual test with debugging
python -m pytest tests/e2e_test_suite.py -v -s --pdb
```

### Performance Issues
```bash
# Check system resources
df -h /          # Disk space
free -h          # Memory
top -p $(pgrep -f pytest)  # Process monitoring
```

## 📈 Performance Benchmarks

### Expected Performance (on standard hardware)

| Test Category | Expected Runtime | Memory Usage | CPU Usage |
|---------------|------------------|--------------|-----------|
| E2E Orchestrator | 3-5 minutes | < 500MB | < 80% |
| Service Integration | 30 seconds | < 100MB | < 50% |
| DNA Integrity | 15 seconds | < 50MB | < 30% |
| Economic Model | 20 seconds | < 50MB | < 30% |
| Error Handling | 25 seconds | < 100MB | < 50% |
| Concurrent Execution | 60 seconds | < 300MB | < 70% |
| Performance Tests | 90 seconds | < 200MB | < 60% |

### Performance Optimization

```bash
# Run tests in parallel (if fixtures support)
export E2E_TEST_PARALLEL=true

# Adjust timeouts for slower systems
export E2E_TEST_TIMEOUT=600

# Profile test execution
python -m pytest tests/ --profile
```

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: BorgLife E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      - name: Start services
        run: docker-compose up -d
      - name: Validate readiness
        run: ./scripts/validate_demo_readiness.sh
      - name: Run E2E tests
        run: ./scripts/run_e2e_tests.sh
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: e2e_test_report_*.json
```

## 📚 API Reference

### E2ETestSuite Class

```python
from tests.e2e_test_suite import E2ETestSuite

# Initialize suite
suite = E2ETestSuite()

# Setup environment
await suite.setup_test_environment()

# Run all scenarios
results = await suite.run_all_scenarios()

# Generate report
report = suite.generate_test_report(results)
suite.save_report(report)

# Cleanup
await suite.teardown_test_environment()
```

### Test Fixtures

```python
# Access fixtures in tests
@pytest.fixture
async def e2e_suite():
    suite = E2ETestSuite()
    await suite.setup_test_environment()
    yield suite
    await suite.teardown_test_environment()
```

## 🤝 Contributing

### Adding New Tests

1. **Create test file**: `tests/test_new_feature.py`
2. **Follow naming convention**: `test_*` functions
3. **Use async fixtures**: `@pytest.mark.asyncio`
4. **Add to E2E suite**: Update `e2e_test_suite.py` if needed
5. **Update documentation**: Add to this README

### Test Data Management

1. **Add fixtures**: Place in `tests/fixtures/`
2. **Validate format**: JSON for structured data, YAML for configurations
3. **Update references**: Ensure all test files can access new fixtures
4. **Version control**: Include fixture changes in commits

## 📞 Support

### Getting Help

1. **Check logs**: Review `e2e_test_output_*.log` files
2. **Validate environment**: Run `./scripts/validate_demo_readiness.sh`
3. **Check service health**: Verify Docker containers are running
4. **Review fixtures**: Ensure test data is valid and accessible

### Reporting Issues

When reporting test failures, include:

- Test output logs
- Environment details (`docker-compose ps`, `python --version`)
- Fixture validation results
- Service health status
- System resource usage

---

**BorgLife Phase 1 E2E Test Suite** - Ensuring demo reliability through comprehensive validation 🧬⚡