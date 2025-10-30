#!/bin/bash
# BorgLife Phase 1 Demo Readiness Validation Script
#
# This script performs comprehensive pre-demo validation to ensure
# the BorgLife Phase 1 system is ready for live demonstrations.
#
# Validates:
# - Service health and connectivity
# - Test suite integrity and execution
# - Demo scenario readiness
# - Performance benchmarks
# - Configuration completeness
#
# Usage: ./scripts/validate_demo_readiness.sh [--quick] [--verbose] [--fix-issues]

set -e  # Exit on any error

# Configuration - Load dynamic path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/path_config.sh"
VALIDATION_TIMEOUT=60  # 1 minute for quick validation
START_TIME=$(date +%s)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation results
VALIDATION_PASSED=0
VALIDATION_FAILED=0
ISSUES_FOUND=()

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    ((VALIDATION_PASSED++))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((VALIDATION_FAILED++))
    ISSUES_FOUND+=("$1")
}

log_header() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Parse command line arguments
QUICK_MODE=false
VERBOSE=false
FIX_ISSUES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --fix-issues)
            FIX_ISSUES=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Usage: $0 [--quick] [--verbose] [--fix-issues]"
            exit 1
            ;;
    esac
done

# Validation functions
validate_environment() {
    log_header "ENVIRONMENT VALIDATION"

    # Check if we're in the right directory
    if [ ! -f "tests/e2e_test_suite.py" ]; then
        log_error "Not in correct directory. Run from BorgLife code root."
        return 1
    fi

    # Check required commands
    local required_commands=("python3" "curl" "docker" "docker-compose")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            return 1
        fi
    done
    log_success "Required commands available"

    # Check Python dependencies
    if ! python3 -c "import pytest, yaml, asyncio" 2>/dev/null; then
        log_error "Required Python packages not available"
        return 1
    fi
    log_success "Python dependencies available"

    # Check file structure
    local required_files=(
        "tests/e2e_test_suite.py"
        "tests/fixtures/demo_tasks.json"
        "tests/fixtures/test_dna_samples.yaml"
        "tests/fixtures/expected_results.json"
        ".env.test"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file missing: $file"
            return 1
        fi
    done
    log_success "Required files present"

    return 0
}

validate_services() {
    log_header "SERVICE VALIDATION"

    # Check Docker services
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        log_error "Docker services not running"
        if [ "$FIX_ISSUES" = true ]; then
            log_info "Starting Docker services..."
            docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
            sleep 15
        else
            return 1
        fi
    fi

    # Service health checks
    local services=(
        "Archon Server:http://localhost:8181/health"
        "Archon MCP:http://localhost:8051/health"
        "Archon Agents:http://localhost:8052/health"
    )

    for service_info in "${services[@]}"; do
        IFS=':' read -r service_name service_url <<< "$service_info"

        if [ "$VERBOSE" = true ]; then
            log_info "Checking $service_name..."
        fi

        local max_attempts=15
        local attempt=1
        local success=false

        while [ $attempt -le $max_attempts ]; do
            if curl -f -s "$service_url" > /dev/null 2>&1; then
                success=true
                break
            fi
            sleep 2
            ((attempt++))
        done

        if [ "$success" = true ]; then
            log_success "$service_name healthy"
        else
            log_error "$service_name failed health check"
            return 1
        fi
    done

    return 0
}

validate_test_integrity() {
    log_header "TEST INTEGRITY VALIDATION"

    # Syntax check Python files
    local python_files=(
        "tests/e2e_test_suite.py"
        "tests/test_service_integration.py"
        "tests/test_dna_integrity.py"
        "tests/test_economic_model.py"
        "tests/test_error_handling.py"
    )

    for file in "${python_files[@]}"; do
        if [ -f "$file" ]; then
            if python3 -m py_compile "$file" 2>/dev/null; then
                if [ "$VERBOSE" = true ]; then
                    log_success "$file syntax OK"
                fi
            else
                log_error "$file has syntax errors"
                return 1
            fi
        else
            log_warning "$file not found (optional)"
        fi
    done

    if [ "$VERBOSE" = true ]; then
        log_success "All Python files syntax validated"
    fi

    # Validate JSON fixtures
    local json_files=(
        "tests/fixtures/demo_tasks.json"
        "tests/fixtures/expected_results.json"
    )

    for file in "${json_files[@]}"; do
        if [ -f "$file" ]; then
            if python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
                log_success "$file JSON valid"
            else
                log_error "$file has invalid JSON"
                return 1
            fi
        else
            log_error "$file not found"
            return 1
        fi
    done

    # Validate YAML fixtures
    if [ -f "tests/fixtures/test_dna_samples.yaml" ]; then
        if python3 -c "import yaml; yaml.safe_load(open('tests/fixtures/test_dna_samples.yaml'))" 2>/dev/null; then
            log_success "test_dna_samples.yaml YAML valid"
        else
            log_error "test_dna_samples.yaml has invalid YAML"
            return 1
        fi
    else
        log_error "test_dna_samples.yaml not found"
        return 1
    fi

    return 0
}

validate_demo_scenarios() {
    log_header "DEMO SCENARIO VALIDATION"

    # Load and validate demo tasks
    if ! python3 -c "
import json
with open('tests/fixtures/demo_tasks.json') as f:
    data = json.load(f)
scenarios = data.get('scenarios', [])
if len(scenarios) >= 5:
    print(f'SUCCESS: {len(scenarios)} demo scenarios available')
    exit(0)
else:
    print(f'ERROR: Only {len(scenarios)} scenarios (need ≥5)')
    exit(1)
" 2>/dev/null; then
        log_error "Demo scenarios validation failed"
        return 1
    fi

    # Validate DNA samples
    if ! python3 -c "
import yaml
with open('tests/fixtures/test_dna_samples.yaml') as f:
    data = yaml.safe_load(f)
if 'test_dna_minimal' in data:
    print('SUCCESS: DNA samples available')
    exit(0)
else:
    print('ERROR: test_dna_minimal not found')
    exit(1)
" 2>/dev/null; then
        log_error "DNA samples validation failed"
        return 1
    fi

    log_success "Demo scenarios and fixtures validated"
    return 0
}

run_quick_test() {
    log_header "QUICK TEST EXECUTION"

    if [ "$QUICK_MODE" = true ]; then
        log_info "Skipping full test execution in quick mode"
        return 0
    fi

    log_info "Running quick test validation..."

    # Run a single test method to verify everything works
    local test_start=$(date +%s)

    if timeout 30 python3 -m pytest tests/e2e_test_suite.py::TestE2ETestSuite::test_individual_scenario_execution -v --tb=short > /tmp/quick_test.log 2>&1; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        log_success "Quick test passed in ${duration}s"
        return 0
    else
        log_error "Quick test failed"
        if [ "$VERBOSE" = true ]; then
            echo "Test output:"
            cat /tmp/quick_test.log
        fi
        return 1
    fi
}

validate_performance() {
    log_header "PERFORMANCE VALIDATION"

    if [ "$QUICK_MODE" = true ]; then
        log_info "Skipping performance validation in quick mode"
        return 0
    fi

    # Check system resources
    local available_memory=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
    if [ "$available_memory" -lt 100000 ]; then  # Rough check for available memory
        log_warning "Low system memory detected"
    else
        log_success "System memory adequate"
    fi

    # Check disk space
    local available_space=$(df / | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 1000000 ]; then  # 1GB in KB
        log_warning "Low disk space detected"
    else
        log_success "Disk space adequate"
    fi

    return 0
}

generate_validation_report() {
    log_header "VALIDATION REPORT"

    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))

    echo "Validation completed in ${duration}s"
    echo "Passed checks: $VALIDATION_PASSED"
    echo "Failed checks: $VALIDATION_FAILED"

    if [ $VALIDATION_FAILED -eq 0 ]; then
        log_success "🎉 ALL VALIDATION CHECKS PASSED!"
        log_success "BorgLife Phase 1 is READY FOR DEMO!"
        echo
        echo "Next steps:"
        echo "1. Run full E2E tests: ./scripts/run_e2e_tests.sh"
        echo "2. Start demo scenarios"
        echo "3. Monitor system performance"
        return 0
    else
        log_error "❌ VALIDATION FAILED - $VALIDATION_FAILED issues found"
        echo
        echo "Issues found:"
        for issue in "${ISSUES_FOUND[@]}"; do
            echo "  - $issue"
        done
        echo
        if [ "$FIX_ISSUES" = true ]; then
            echo "Attempted to fix issues automatically."
            echo "Re-run validation to check if issues are resolved."
        else
            echo "Run with --fix-issues to attempt automatic fixes."
        fi
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting BorgLife Phase 1 Demo Readiness Validation"

    # Run all validations
    validate_environment || exit 1
    validate_services || exit 1
    validate_test_integrity || exit 1
    validate_demo_scenarios || exit 1
    run_quick_test || exit 1
    validate_performance || exit 1

    # Generate final report
    generate_validation_report
}

# Run main function
main "$@"