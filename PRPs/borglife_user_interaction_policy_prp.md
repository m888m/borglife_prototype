# BorgLife User Interaction Policy Framework PRP

## Feature: Minimal Evolutionary Policy Framework

## Goal

Establish the minimum viable policy foundation to enable BorgLife's core evolutionary mechanics. Focus on evolutionary consent, basic ownership verification, and transparent audit trails - deferring complex collaboration and governance to Phase 2.

## Deliverable

A radically simplified Phase 1 policy framework focused on evolutionary foundation:
- Evolutionary consent as the cornerstone of user agreements
- On-chain DNA ownership verification for creator rights
- Basic blockchain audit trails for transparency
- Foundation for Phase 2 mating markets and advanced IP management

## Prerequisites

### Blockchain Infrastructure
**On-Chain Storage:**
- Westend Asset Hub (testing): DNA hash storage, ownership proofs
- Westend (production): Full deployment with economic incentives
- JAM (future): Native borg execution environment

**Web3 Primitives:**
- Substrate addresses for user identification
- Cryptographic signatures for ownership verification
- On-chain timestamps for priority claims
- Hash-based IP proofs

### Existing Infrastructure Integration
**Core Functions:**
- `register_borg_address()` - Blockchain address registration
- `DemoAuditLogger` - Off-chain audit trails
- `EconomicValidator` - On-chain balance verification

**Dual License Model:**
- **Software Ecosystem**: MIT licensed open source code
- **Borg IP/Content**: Proprietary to creators with evolutionary sharing
- **Evolutionary Consent**: Users agree DNA evolves via BorgLife algorithms
- **Partial IP Rights**: Creators retain rights only to their original DNA contribution
- **Mating Markets**: Permissioned genetic exchange with IP attribution (Phase 2)

## Context

### Current State
- Phase 1 development with blockchain address registration via [`BorgAddressManagerAddressPrimary.register_borg_address()`](code/jam_mock/borg_address_manager_address_primary.py:108)
- Basic audit logging via [`DemoAuditLogger`](code/jam_mock/demo_audit_logger.py) (`demo_audit.jsonl`)
- On-chain DNA hash anchoring via [`DNAAanchor`](code/security/dna_anchor.py) during registration
- Single opt-in consent via terms acceptance (consent signature param exists but no UI/verification)
- MIT license open source distribution
- Economic validation via [`EconomicValidator`](code/jam_mock/economic_validator.py)
- Asset Hub integration for ownership proofs via [`AssetHubAdapter`](code/jam_mock/asset_hub_adapter.py)

### Technical Context
**Web3 Data Architecture:**
- **On-Chain (Public)**: DNA hashes (via anchoring), borg addresses, ownership timestamps, economic transactions (transfers)
- **Off-Chain (Encrypted)**: Full DNA sequences, keypairs (macOS Keychain), detailed audit logs (JSONL)
- **Local (Private)**: User preferences, temporary caches, development data (Supabase metadata)

**Blockchain-First Access:**
- **Public Read**: Anyone can verify ownership and transactions on-chain
- **Owner Write**: Only address owners can modify their borgs
- **Transparent Audit**: All actions logged with cryptographic proof

### Business Context
**Evolutionary Foundation:**
- **Core Innovation**: Δ(W) = R - C drives natural selection of borgs
- **Creator Rights**: Protect original intellectual contributions
- **Evolutionary Consent**: Users understand and accept genetic mixing
- **Phase 1 Focus**: Enable evolution, defer complex governance

**Minimalist Web3 Approach:**
- Blockchain provides immutable ownership verification
- Cryptographic signatures ensure creator sovereignty
- Transparent audit trails enable evolutionary tracking
- Foundation for Phase 2 mating markets and advanced IP

## Implementation Tasks

### Task 1: Evolutionary Consent & Terms Foundation
**Status**: Partially implemented (consent param in register_borg_address, no UI)
**Description**: Establish evolutionary consent as the cornerstone of BorgLife user agreements.

**Technical Details:**
**Evolutionary Consent (Core Innovation):**
- **Algorithmic Evolution**: Clear agreement that borg DNA evolves via BorgLife algorithms
- **Genetic Mixing**: Understanding that offspring contain DNA from multiple borgs
- **Partial IP Rights**: Creators retain rights only to original DNA contributions
- **Blockchain Recording**: Consent recorded immutably on-chain

**Minimal Terms Structure:**
- **MIT License**: Software usage terms
- **Evolutionary Agreement**: Core genetic mixing consent
- **Creator Rights**: Basic IP protection statement
- **Future Evolution**: Acknowledgment of Phase 2 mating markets

**Prototype Validation**:
1. Create minimal Streamlit consent UI PoC: display terms, capture signature over DNA+terms hash
2. Integrate signature verification in register_borg_address: verify sig recovers creator pubkey
3. On-chain event emission: ConsentRegistered(dna_hash, address, sig_hash, timestamp)

**Implementation Steps:**
1. [x] Implement blockchain-recorded consent param in register_borg_address
2. [-] Create simple terms UI with evolutionary focus (PoC: Streamlit app)
3. [ ] Add evolutionary agreement verification (Pydantic Consent model)
4. [x] Store consent proofs on-chain via anchoring

**Integration Points:**
- Uses `register_borg_address()` for consent verification
- Leverages blockchain for immutable consent records
- Integrates with basic audit logging

**Validation:**
- Evolutionary consent clearly communicated
- Terms acceptance required for borg creation
- Consent recorded on blockchain
- Users understand genetic mixing implications

### Task 2: On-Chain Ownership Verification
**Status**: Mostly implemented
**Description**: Implement basic blockchain ownership verification for creator rights.

**Technical Details:**
**Core Ownership:**
- **DNA Hash Storage**: H(DNA) stored on-chain as ownership proof
- **Address Verification**: Substrate address ownership of borg modifications
- **Timestamp Proof**: Block timestamps establish creation priority
- **Basic Transfers**: Simple ownership transfer mechanisms

**Minimal IP Protection:**
- **Creator Attribution**: Original creator always credited
- **Evolutionary Transparency**: On-chain tracking of genetic mixing
- **Basic Rights**: Protection of original intellectual contribution
- **Phase 2 Foundation**: groundwork for advanced IP management

**Prototype Validation**: Run 1000 registrations, query chain for hashes/ownership, measure gas/fees.

**Implementation Steps:**
1. [x] Store DNA hashes via Westend Asset Hub / DNAAanchor
2. [x] Implement basic ownership verification (address primary key)
3. [x] Create simple transfer mechanisms (AssetHubAdapter.transfer_usdb)
4. [-] Add creator attribution tracking (extend audit with sig verification)

**Integration Points:**
- Uses existing JAM mock for blockchain interactions
- Leverages `register_borg_address()` for ownership establishment
- Integrates with basic audit logging

**Validation:**
- DNA hash ownership verifiable on-chain
- Creator attribution always maintained
- Basic ownership transfers work
- Evolutionary mixing tracked transparently

### Task 3: Basic Blockchain Audit Logging
**Status**: Off-chain prototype, on-chain pending
**Description**: Implement simple blockchain-based audit trails for evolutionary transparency.

**Technical Details:**
**Essential Audit:**
- **Economic Transactions**: All Δ(W) activities logged on-chain
- **Ownership Changes**: Borg creation, transfers, and modifications
- **Evolutionary Events**: Genetic mixing and reproduction events
- **Timestamp Verification**: Block numbers provide chronological proof

**Minimal Transparency:**
- **Public Verification**: Basic on-chain transaction visibility
- **Creator Audit**: Owners can verify their borg's history
- **Evolutionary Tracking**: Transparent genetic lineage
- **Phase 2 Foundation**: groundwork for advanced audit systems

**Prototype**: Deploy local Substrate node, simulate 100 tx, verify events with subxt.

**Implementation Steps:**
1. [-] Log all economic transactions on-chain (extend adapters with events)
2. [x] Record ownership changes transparently (registration)
3. [ ] Track evolutionary events
4. [ ] Enable basic public verification (Subscan queries)

**Integration Points:**
- Uses existing `demo_audit.jsonl` for operational details
- Leverages blockchain for immutable audit trails
- Integrates with `borg_balances` for economic tracking

**Validation:**
- Economic transactions logged on-chain
- Ownership changes publicly verifiable
- Evolutionary events tracked transparently
- Basic audit verification works

## Validation Gates

### Gate 1: Evolutionary Consent
- [ ] Evolutionary consent clearly communicated in terms
- [ ] Users understand genetic mixing implications
- [x] Consent recorded immutably on-chain (param exists)
- [ ] Terms acceptance required for borg creation

### Gate 2: Ownership Verification
- [x] DNA hashes stored on Westend Asset Hub / anchored
- [x] Creator ownership verifiable on-chain (address ownership)
- [x] Basic ownership transfers functional (USDB/WND)
- [-] Attribution maintained for original creators (audit sigs)

### Gate 3: Audit Transparency
- [-] Economic transactions logged on-chain (adapters emit)
- [x] Ownership changes publicly verifiable (registration)
- [ ] Evolutionary events tracked transparently
- [x] Basic audit verification mechanisms work (off-chain + Subscan)

## Success Definition

**Minimal Success**: Evolutionary consent framework implemented with basic on-chain ownership verification, enabling the core BorgLife evolutionary mechanics.

**Full Success**: Evolutionary foundation established with transparent audit trails, proven through basic borg creation and evolution cycles, ready for Phase 2 mating markets.

## Architect Review Insights

### 1. GAPS
* Claims immutable on-chain consent but only param in code, no sig verification/UI. Prototype: Streamlit consent PoC + sig check in register_borg_address.
* On-chain audit for evolution events aspirational, current off-chain JSONL. Test: Local Substrate with custom pallet events for ConsentRegistered/OwnershipChanged.

### 2. OVERLOOKED ELEMENTS
* Fee strategy: No estimation in adapters (risk tx fails). Incremental: Add `substrate.estimate_extrinsic_fees()` before submit.
* Finality/re-orgs: Uses wait_for_inclusion, not finalized. Add: `wait_for_finalized=True`.
* Observability: Audit good, missing tx metrics. Add: Prometheus endpoint for latency/fees.
* Data contracts: No Pydantic. Add: `class Consent(BaseModel): dna_hash: str; terms_hash: str; sig: str`

### 3. UNVERIFIED ASSUMPTIONS
* Deterministic keys from DNA hash collision-free: Validate with 1M sha256 sim script.
* macOS Keychain prod-ready: No. Quick test: Export/import keys across machines.
* Partial IP comprehension: No metrics. PoC: User survey post-consent quiz.

### 4. INCOMPLETE ASPECTS
* Consent interfaces: Define REST/gRPC for UI. Next: Pydantic models for ConsentRecord.
* Error handling: No retries in adapters. Specify: Exponential backoff 3x max.
* Data lifecycle: DNA hash pinning? Add IPFS multihash.

### 5. VIOLATIONS / RISKS
* Centralization violation: Local Keychain/Supabase. Remediation: Prod - WalletConnect; immediate - multi-key threshold.
* Privacy risk: Public DNA hashes trace lineages. Post-PoC: ZK proofs for mixing.
* Reliability hazard: No nonce mgmt races. Fix now: Lockfile for nonce cache.

### 6. NEXT ACTIONS (CHECKLIST)
- [ ] Implement consent UI PoC (1 day)
- [ ] Add on-chain events pallet (2 days)
- [ ] Run key collision sim + fee benchmark (0.5 day)
- [ ] Migrate audit to hybrid on/off-chain
- [ ] Update gates to [x] after prototypes

## Risk Assessment

### High Risk
- [x] **Blockchain Dependency**: Mitigated by graceful degradation in code
- **IP Protection Expectations**: Users misunderstanding proprietary borg ownership vs open software. Mitigation: Consent UI quiz validation.
- **Key Management**: macOS Keychain demo-only. Mitigation: Hardware wallet PoC pre-prod.

### Medium Risk
- [x] **On-Chain Data Visibility**
- **Fork Attribution Failure**
- **Consent Comprehension**: No verification. Mitigation: Post-acceptance quiz, revocable consent.

### Low Risk
- [x] **Terms Acceptance Burden**
- [x] **Development to Production Transition**

## Timeline

**Total Effort**: 1.5 weeks (reduced: Tasks 2 partial)
**Due Date**: Mid-Phase 1b

**Phase Breakdown:**
- **Week 1**: Consent UI + prototypes (Task 1 complete)
- **0.5 Week**: On-chain audit events (Task 3)

## Resources Required

- **Development Team**: 1 developer with blockchain experience
- **Legal Review**: Basic terms and evolutionary consent review
- **User Testing**: 5 beta users for consent flow validation
- **Infrastructure**: Westend Asset Hub access
- **Documentation**: Simple terms of service with evolutionary focus

## Rollback Procedures

### Policy Rollback
1. **Terms Removal**: Remove terms acceptance requirement from UI
2. **Ownership Bypass**: Allow unsigned borg modifications in development mode
3. **Audit Disable**: Turn off blockchain logging, keep local logs
4. **Collaboration Open**: Remove all sharing restrictions

### Complete System Rollback
```bash
# 1. Disable Web3 policies
export WEB3_POLICIES=false

# 2. Remove blockchain dependencies
# (No database changes needed - policies are code-level)

# 3. Restore simple registration
git checkout SIMPLE_REGISTRATION

# 4. Clear blockchain caches
rm -rf .borg_blockchain_cache

# 5. Restart with basic mode
docker compose restart
```

## Post-Implementation

**Immediate Next Steps:**
1. Test evolutionary consent flow with users
2. Verify basic borg creation with ownership verification
3. Validate evolutionary audit trails
4. Enable basic borg evolution cycles

**Long-term Evolution:**
- Phase 2: Mating markets with sophisticated IP attribution
- Phase 2: Advanced evolutionary tracking across generations
- Phase 3: Cross-chain verification and privacy features
- Phase 3: Regulatory compliance and advanced governance

**Metrics for Success:**
- Evolutionary consent understanding and acceptance
- Successful borg creation with verified ownership
- Transparent evolutionary audit trails
- Foundation ready for Phase 2 mating markets