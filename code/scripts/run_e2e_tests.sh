#!/bin/bash
# BorgLife Phase 1 End-to-End Test Execution Script
#
# This script executes the complete E2E test suite for BorgLife Phase 1,
# including service startup, test execution, and comprehensive reporting.
#
# Usage: ./scripts/run_e2e_tests.sh [--no-docker] [--verbose] [--report-only]
#
# Options:
#   --no-docker    Run tests without Docker services (for development)
#   --verbose      Enable verbose output
#   --report-only  Only generate reports from existing test results

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
TEST_TIMEOUT=300  # 5 minutes
START_TIME=$(date +%s)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
USE_DOCKER=true
VERBOSE=false
REPORT_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --report-only)
            REPORT_ONLY=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Usage: $0 [--no-docker] [--verbose] [--report-only]"
            exit 1
            ;;
    esac
done

# Health check functions
check_service_health() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    if [ "$VERBOSE" = true ]; then
        log_info "Checking $service_name health at $url..."
    fi

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            if [ "$VERBOSE" = true ]; then
                log_success "$service_name is healthy"
            fi
            return 0
        fi

        if [ "$VERBOSE" = true ]; then
            echo -n "."
        fi

        sleep 2
        ((attempt++))
    done

    log_error "$service_name failed health check after $max_attempts attempts"
    return 1
}

check_docker_services() {
    log_info "Checking Docker services..."

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
        log_error "Docker/Docker Compose not found"
        return 1
    fi

    # Check if services are running
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        log_warning "Docker services not running, starting them..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

        # Wait for services to be healthy
        log_info "Waiting for services to start..."
        sleep 10
    fi

    # Health checks for each service
    check_service_health "Archon Server" "http://localhost:8181/health" || return 1
    check_service_health "Archon MCP" "http://localhost:8051/health" || return 1
    check_service_health "Archon Agents" "http://localhost:8052/health" || return 1

    log_success "All Docker services are healthy"
    return 0
}

validate_environment() {
    log_info "Validating test environment..."

    # Check if we're in the right directory
    if [ ! -f "tests/e2e_test_suite.py" ]; then
        log_error "tests/e2e_test_suite.py not found. Run from project root."
        return 1
    fi

    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found"
        return 1
    fi

    # Check pytest availability
    if ! python3 -c "import pytest" 2>/dev/null; then
        log_error "pytest not available"
        return 1
    fi

    # Check required test files exist
    local required_files=(
        "tests/e2e_test_suite.py"
        "tests/fixtures/demo_tasks.json"
        "tests/fixtures/test_dna_samples.yaml"
        "tests/fixtures/expected_results.json"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file missing: $file"
            return 1
        fi
    done

    # Check .env.test exists
    if [ ! -f ".env.test" ]; then
        log_warning ".env.test not found, creating basic version..."
        cat > .env.test << EOF
# BorgLife E2E Test Environment
E2E_TEST_TIMEOUT=300
E2E_TEST_PARALLEL=false
LOG_LEVEL=INFO

# Archon Service URLs (adjust for your environment)
ARCHON_SERVER_URL=http://localhost:8181
ARCHON_MCP_URL=http://localhost:8051
ARCHON_AGENTS_URL=http://localhost:8052
EOF
    fi

    log_success "Environment validation passed"
    return 0
}

run_tests() {
    log_info "Running E2E test suite..."

    local test_start=$(date +%s)
    local test_output_file="e2e_test_output_$(date +%Y%m%d_%H%M%S).log"

    # Set environment variables
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    export E2E_TEST_TIMEOUT=$TEST_TIMEOUT

    # Run pytest with timeout and output capture
    if [ "$VERBOSE" = true ]; then
        pytest tests/e2e_test_suite.py -v --tb=short --timeout=$TEST_TIMEOUT 2>&1 | tee "$test_output_file"
    else
        pytest tests/e2e_test_suite.py --tb=short --timeout=$TEST_TIMEOUT > "$test_output_file" 2>&1
    fi

    local test_exit_code=$?
    local test_end=$(date +%s)
    local test_duration=$((test_end - test_start))

    if [ $test_exit_code -eq 0 ]; then
        log_success "E2E tests completed successfully in ${test_duration}s"
        echo "Test output saved to: $test_output_file"
        return 0
    else
        log_error "E2E tests failed with exit code $test_exit_code in ${test_duration}s"
        echo "Check test output in: $test_output_file"
        echo "Last 20 lines of test output:"
        tail -20 "$test_output_file"
        return 1
    fi
}

generate_report() {
    log_info "Generating test report..."

    # Find the latest test report generated by the test suite
    local latest_report=$(find . -name "e2e_test_report_*.json" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)

    if [ -n "$latest_report" ]; then
        log_success "Latest test report: $latest_report"

        # Display summary from the report
        if command -v jq &> /dev/null; then
            echo "Test Summary:"
            jq -r '.summary | "  Total Tests: \(.total_tests)", "  Successful: \(.successful_tests)", "  Failed: \(.failed_tests)", "  Success Rate: \(.success_rate_percent)%", "  Execution Time: \(.total_execution_time_seconds)s"' "$latest_report"
        else
            log_warning "jq not available for detailed report parsing"
            echo "Raw report content:"
            head -20 "$latest_report"
        fi
    else
        log_warning "No test report found"
    fi
}

cleanup() {
    local exit_code=$?

    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))

    echo
    log_info "Test execution completed in ${total_duration}s"

    if [ $exit_code -eq 0 ]; then
        log_success "E2E test run completed successfully!"
    else
        log_error "E2E test run failed with exit code $exit_code"
    fi

    # Cleanup Docker services if we started them
    if [ "$USE_DOCKER" = true ] && [ "$exit_code" -ne 0 ]; then
        log_info "Leaving Docker services running for debugging"
        echo "To stop services manually: docker-compose -f $DOCKER_COMPOSE_FILE down"
    fi
}

# Main execution
main() {
    trap cleanup EXIT

    log_info "Starting BorgLife Phase 1 E2E Test Execution"
    echo "=========================================="

    # Report-only mode
    if [ "$REPORT_ONLY" = true ]; then
        generate_report
        exit 0
    fi

    # Environment validation
    validate_environment || exit 1

    # Docker services check
    if [ "$USE_DOCKER" = true ]; then
        check_docker_services || exit 1
    else
        log_info "Skipping Docker services check (--no-docker mode)"
    fi

    # Run tests
    run_tests || exit 1

    # Generate final report
    generate_report || exit 1

    log_success "All E2E tests completed successfully!"
}

# Run main function
main "$@"