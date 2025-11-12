"""
BorgLife Phase 1 End-to-End Test Suite

This package contains comprehensive tests for the BorgLife Phase 1 prototype,
validating the complete demo flow: funding → borg creation → task execution →
DNA encoding → on-chain storage → decoding validation.

Test Organization:
- conftest.py: Pytest fixtures and configuration
- test_service_integration.py: Archon adapter and service connectivity
- test_dna_integrity.py: DNA parsing, validation, and round-trip integrity
- test_economic_model.py: Wealth tracking and cost calculation
- test_demo_scenarios.py: End-to-end demo scenario execution
- test_performance.py: Performance benchmarks
- e2e_test_suite.py: Main test orchestrator
- fixtures/: Test data (DNA samples, task scenarios, expected results)

Usage:
    pytest tests/ -v                    # Run all tests
    pytest tests/test_dna_integrity.py  # Run specific test module
    ./scripts/run_e2e_tests.sh          # Run complete test suite with services
"""

__version__ = "0.1.0"
__all__ = [
    "conftest",
    "test_service_integration",
    "test_dna_integrity",
    "test_economic_model",
    "test_demo_scenarios",
    "test_performance",
    "e2e_test_suite",
]
