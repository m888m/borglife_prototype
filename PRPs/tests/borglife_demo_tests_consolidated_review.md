# BorgLife Demo & Test Suite PRPs Consolidated Critical Review

**Date**: 2025-11-25  
**Scope**: All 6 PRPs in `PRPs/tests/` consolidated against codebase state.  
**Status**: Plans detailed and actionable; implementation partial (tests ~0-17% pass rate per [`test_suite_resolution_prp.md`](PRPs/tests/test_suite_resolution_prp.md:52) and [`README.md`](code/tests/README.md:102)); shifted to USDB/AssetHub from DOT/remark.

## Executive Summary
The PRPs define incremental prototype → production path for E2E demo (Phases 1A-D: mocks → Westend tx → optimization → hardening) and test suite (implementation → resolution). Codebase aligns structurally ([`proto_borg.py`](code/proto_borg.py:92) matches agent spec, [`demo_scenarios.py`](code/demo_scenarios.py:130) runs flows, tests/ fixtures exist) but incomplete: e2e_suite stubs ([`e2e_test_suite.py`](code/tests/e2e_test_suite.py:245)), async fixture bugs block 83% tests, mocks/JAM gaps post-Archon decoupling yield 0/5 success ([`README.md`](code/tests/README.md:106)). Evolution to jam_mock/USDB good, but PRPs DOT-centric.

**Overall Assessment**: Solid first-principles planning (incremental PoCs, validation gates). Currently unproven at scale; prototype validates happy-path but lacks metrics/load tests.

## 1. GAPS
* **Claims full prod-ready demo (1D) vs. partial mocks**: Phase1D promises security/UX/monitoring; [`demo_scenarios.py`](code/demo_scenarios.py:23) has basic metrics but no alerting/cost controls; tests README notes 0/5 post-decoupling. *Prototype: Run 10x [`demo_scenarios.py`](code/demo_scenarios.py:422) with concurrent=5, measure success/cost; exit if >95% pass <5min.*
* **100% test pass (test_suite_resolution)** vs. 17% pass/83% fixture fails: [`conftest.py`](code/tests/conftest.py:44) async generators rejected by pytest-asyncio. *Test: Fix to `@pytest_asyncio.fixture` per PRP, re-run `pytest tests/`; validate 53/53 pass.*
* **E2E DNA integrity/economics** vs. incomplete suite: [`e2e_test_suite.py`](code/tests/e2e_test_suite.py:52) stubs Phase2A USDB but class unfinished. *PoC: Complete `E2ETestSuite.run_all_scenarios()`, assert H(D')=H(D) via [`proto_borg.py`](code/proto_borg.py:406).*

## 2. OVERLOOKED ELEMENTS
* **Observability**: PRPs mention metrics but no traces/logs; [`demo_scenarios.py`](code/demo_scenarios.py:24) basic, no structured logging. *Incremental: Add `logging` with correlation IDs in [`proto_borg.py`](code/proto_borg.py:20) `execute_task`; integrate Prometheus in next PoC.*
* **Blockchain concerns**: DOT/Westend remark assumed; codebase USDB/AssetHub ([`asset_hub_adapter.py`](code/jam_mock/asset_hub_adapter.py)). No fee strategy/re-org/finality. *Add: Dynamic fees via substrate-interface query in JAM; test re-org simulation with local node.*
* **Data validation**: Pydantic in synthesis but no schema evolution/migrations. *Add Pydantic[`BorgDNA`](code/proto_borg.py:206) v1→v2 in tests/fixtures.*
* **Agent failure modes**: No retry/state in [`proto_borg.py`](code/proto_borg.py:319); mocks lack. *Add exponential backoff in `execute_task`; PoC LangGraph workflow trace.*

## 3. UNVERIFIED ASSUMPTIONS
* **Archon always available**: PRPs assume; [`conftest.py`](code/tests/conftest.py:186) skips if not. *Validate: Chaos test 20% Archon failure; measure fallback success via mock phenotype ([`proto_borg.py`](code/proto_borg.py:176)).*
* **JAM costs <0.01/run**: Phase1B; no benchmarks. *Benchmark: 100x [`demo_scenarios.py`](code/demo_scenarios.py:268) stress, log fees; shadow real Westend tx.*
* **<5min execution**: Claimed; README notes partial. *Script: `time pytest tests/`; if >5min, profile async bottlenecks.*
* **Mock=real behavior**: Assumed; post-decoupling gaps. *Diff: Run mock vs hybrid ([`demo_scenarios.py`](code/demo_scenarios.py:137)), assert parity.*

## 4. INCOMPLETE ASPECTS
* **Interfaces**: [`e2e_test_suite.py`](code/tests/e2e_test_suite.py:245) `E2ETestSuite` unfinished (self.arch cut); EconomicValidator/TransactionManager missing args per README failures. *Define: Pydantic models for `DemoResult` with `cost: Decimal`, `integrity: bool`; spec retry policy (3x exp backoff).*
* **Error behavior**: Graceful skips but no lifecycles (borg shutdown). *Add: `async shutdown()` in [`proto_borg.py`](code/proto_borg.py:560); data lifecycle (DNA prune after N tx).*
* **USDB evolution**: PRPs DOT; code AssetHub. *Clarify: Update PRPs to USDB pallet calls; define XCM for cross-hub.*

## 5. VIOLATIONS / RISKS
* **Centralized mocks**: Full reliance on LocalJAMMock; violates decentralization. *Remediation: PoC Substrate local node post-tests (cannot wait); secure mocks with rate-limits now ([`rate_limiter.py`](code/security/rate_limiter.py)).*
* **Security/privacy**: Keyring in tests ([`conftest.py`](code/tests/conftest.py:157)); prod keys exposed. *Immediate: Env vars only, no hardcode; PoC key rotation.*
* **Reliability hazards**: Async generators flake tests; no CI. *Remediation: Fix fixtures now; add GitHub Actions per README.*

## 6. NEXT ACTIONS (CHECKLIST)
- [ ] Fix async fixtures in [`conftest.py`](code/tests/conftest.py:186) per test_suite_resolution (2h; unblocks 83% tests).
- [ ] Complete mocks/JAM methods (update_wealth etc.) in jam_mock/ (4h; fixes 0/5).
- [ ] Run `pytest tests/ -v` + `./scripts/run_e2e_tests.sh`; baseline report (1h).
- [ ] Prototype 10x concurrent demo via [`demo_scenarios.py`](code/demo_scenarios.py:287) stress_test; measure (2h).
- [ ] Update PRPs to USDB/AssetHub; merge phases into single master PRP (3h).
- [ ] Add CI YAML for tests (per README); push to validate.

**Motto Applied**: Prototype validated incrementally; now refine tests pragmatically before scaling to prod hardening.