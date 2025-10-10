# Product Requirements Prompts (PRPs) for Borglife Phase 1 Prototype

## Overview

These PRPs provide structured, high-quality prompts for AI-driven development of the Borglife Phase 1 prototype. They capture detailed product specifications, user needs, and technical constraints, serving as foundational input for efficient implementation. The prototype builds a proto-borg as a static AI agent with wallet integration for sponsorships/bounties on Kusama testnet, validating end-to-end autonomy.

**Core Objectives**:
- Demonstrate borg autonomy through self-managed wealth and task execution.
- Establish hybrid on-chain/off-chain architecture with JAM anchors.
- Enable sponsor interactions via bounties and monitoring.
- Lay groundwork for evolutionary mechanics (deferred to Phase 2).

**Technical Decisions**:
- **Languages**: Python for agent logic and UI (via Archon), Rust for PVM bytecode and JAM interactions.
- **Architecture**: Hybrid Python/Rust with Archon orchestration for synthesis.
- **On-Chain**: Kusama testnet with mock JAM phases initially.
- **Off-Chain**: Archon for phenotype, Supabase/IPFS for data.
- **Testing**: Unit for components, integration for flows, fuzzing for robustness.
- **Deployment**: Docker Compose for reproducibility.

**User Needs**:
- Sponsors: Easy bounty posting, wealth tracking, borg output monitoring.
- Developers: Clear APIs, modular components, iterative feedback.
- Borgs: Autonomous execution, cost management, verifiable settlements.

**Constraints**:
- Phase 1 scope: Static agent, no full evolution/GP.
- JAM compatibility: Use testnet, mock phases to avoid delays.
- Ethical: Basic manual checks, defer full oracles.
- Performance: Sub-second responses, scalable to 50 borgs.

## Task Breakdown

### Task 1: Proto-Borg Phenotype Development

**Description**: Create a static AI agent in Python using PydanticAI for basic task logic (e.g., data processing). Integrate wallet operations via py-substrate-interface for sponsorship intake and mock cost tracking. Add logging for actions and wealth changes.

**Dependencies**: None (foundational).

**Technical Specs**:
- Use PydanticAI for agent framework.
- Implement basic tasks: Data summarization, simple computations.
- Wallet: Connect to Kusama testnet for DOT/USDC transfers.
- Logging: Structured JSON logs for audits.

**Testing Strategy**:
- Unit: Agent logic correctness (PyTest).
- Integration: Wallet transfers succeed.
- Criteria: Agent processes 10 sample tasks without errors; wallet receives/sends 1 DOT.

**Acceptance Criteria**:
- Agent executes tasks autonomously.
- Logs include wealth deltas and task outcomes.
- No external intervention required for basic operations.

**Risk Mitigation**: Mock costs initially; validate with real transfers.

**AI Prompt**: "Implement a Python-based static AI agent using PydanticAI that performs data processing tasks, integrates with Polkadot wallet via py-substrate-interface for sponsorships, and logs all actions. Ensure autonomy and basic cost tracking."

### Task 2: DNA Encoding/Decoding System

**Description**: Serialize proto-borg config to simplified DNA (YAML initially, evolve to PVM). Implement forward (YAML → Python classes) and reverse (classes → YAML) mappings with round-trip integrity. Use Rust for PVM foundations.

**Dependencies**: Task 1 (derive DNA from phenotype).

**Technical Specs**:
- YAML structure: Header (gas limits), cells (logic subroutines), organs (MCP pointers), manifesto hash.
- Rust crate for PVM disassembly (pvm-disassembler).
- Python wrappers for mappings.

**Testing Strategy**:
- Unit: Mapping functions (PyTest/Rust tests).
- Integration: Round-trip H(D') = H(D).
- Fuzzing: Randomized configs for corruption detection.
- Criteria: 95% accuracy on 100 test vectors; no data loss in mappings.

**Acceptance Criteria**:
- DNA faithfully represents phenotype.
- Mappings are bidirectional and deterministic.
- Integrates with Task 1 agent.

**Risk Mitigation**: Start with YAML; validate before bytecode.

**AI Prompt**: "Build a DNA encoding/decoding system in Python/Rust that serializes borg configs to YAML/PVM, with forward/reverse mappings ensuring integrity. Include round-trip validation and basic PVM support."

### Task 3: On-Chain Storage and Wealth Management

**Description**: Store DNA hashes and wealth on Kusama testnet using Rust/subxt. Implement mock JAM phases for refine/accumulate. Enable borg autonomy in asset management.

**Dependencies**: Task 2 (DNA ready for storage).

**Technical Specs**:
- Substrate Rust SDK for JAM/Kusama interactions.
- Mock phases: Simulate parallel execution locally.
- Wealth: Track \(\Delta(W)\) with XCM for settlements.

**Testing Strategy**:
- Unit: Storage operations.
- Integration: End-to-end storage/retrieval.
- Criteria: DNA hashes stored verifiably; wealth updates in <1s.

**Acceptance Criteria**:
- Borgs hold/manage assets without external control.
- On-chain anchors enable audits.
- Mocks transition smoothly to real JAM.

**Risk Mitigation**: Use testnet fallbacks; monitor JAM alphas.

**AI Prompt**: "Implement on-chain storage for borg DNA and wealth on Kusama testnet using Rust, with mock JAM phases. Ensure autonomous asset management and verifiable anchors."

### Task 4: Sponsor UI and Monitoring Dashboard

**Description**: Build Streamlit/React UI for DNA design, bounty posting, sponsorship transfers, and borg monitoring. Integrate with Archon for real-time updates.

**Dependencies**: Tasks 1-3 (components to monitor).

**Technical Specs**:
- Streamlit for rapid prototyping; React for polish.
- Features: YAML editor, wallet integration, log visualization.
- Archon WebSockets for updates.

**Testing Strategy**:
- Unit: UI components render correctly.
- Integration: Full bounty flow (post → execute → monitor).
- User testing: A/B for usability.
- Criteria: 75% user task completion; <2s load times.

**Acceptance Criteria**:
- Sponsors post bounties easily.
- Real-time monitoring of borg wealth and outputs.
- Intuitive interface for non-technical users.

**Risk Mitigation**: Beta feedback loops; fallback to CLI.

**AI Prompt**: "Create a web dashboard using Streamlit/React for borg DNA design, bounty management, and monitoring. Integrate wallet ops and real-time updates via Archon."

### Task 5: Archon Extensions and Infrastructure

**Description**: Extend Archon with MCP wrappers for organs, RAG for cells, and libp2p for coordination. Dockerize stack for reproducibility.

**Dependencies**: All previous (integrate into cohesive system).

**Technical Specs**:
- MCP server for reusable organs (e.g., LLM APIs).
- Supabase for vectors/logs.
- Docker Compose for deployment.

**Testing Strategy**:
- Unit: MCP tools function.
- Integration: Full synthesis flow.
- Load testing: 10 concurrent borgs.
- Criteria: Organs swap without downtime; system deploys in <5min.

**Acceptance Criteria**:
- Modularity enables organ reuse.
- Off-chain efficiency with on-chain anchors.
- Scalable to prototype needs.

**Risk Mitigation**: Redundant pointers; health monitoring.

**AI Prompt**: "Extend Archon framework with MCP organs, RAG cells, and Docker orchestration for borg synthesis. Ensure integration with on-chain components."

### Task 6: End-to-End Integration and Validation

**Description**: Assemble all components into demo loop: Funding → execution → encoding → storage → decoding. Validate autonomy and scarcity.

**Dependencies**: All tasks.

**Technical Specs**:
- Orchestrate via Docker Compose.
- Demo: Sponsor posts bounty, borg executes, settles on-chain.

**Testing Strategy**:
- System: Full loop smoke tests.
- Fuzzing: Ethical/log edge cases.
- Criteria: 100% success on 50 demo runs; <10% failure rate.

**Acceptance Criteria**:
- End-to-end autonomy demonstrated.
- Scarcity enforced via wealth tracking.
- Ready for Phase 2 expansion.

**Risk Mitigation**: Iterative validation; community beta.

**AI Prompt**: "Integrate all prototype components into an end-to-end demo validating borg autonomy, hybrid architecture, and sponsor interactions. Include comprehensive testing."

## Dependencies Chain

- Task 1 → Task 2 (phenotype for DNA)
- Task 2 → Task 3 (DNA for storage)
- Tasks 1-3 → Task 4 (components for UI)
- Tasks 1-5 → Task 6 (full integration)

## Overall Testing Strategy

- **Unit**: Component isolation (PyTest, Rust tests).
- **Integration**: Cross-component flows (e.g., DNA → storage).
- **System**: End-to-end scenarios.
- **Fuzzing**: Robustness against inputs (e.g., corrupt DNA).
- **Performance**: Latency <1s, throughput for 50 borgs.
- **Security**: Audit wallet ops, no key leaks.

## Risk Mitigation Approaches

- **JAM Delays**: Mock phases with real Kusama anchors.
- **Mapping Errors**: Round-trip checks, golden fixtures.
- **Adoption Lag**: Tutorials, marketing outreach.
- **Ethical Drift**: Manual flags, log audits.
- **Ops Issues**: GitHub Actions for CI/CD, linting.

## Conclusion

These PRPs enable competent developers to execute Phase 1 efficiently with minimal ambiguity. Each task is discrete, sequenced logically, with clear criteria and mitigations. AI can use these prompts directly for implementation, ensuring alignment with Borglife's vision.