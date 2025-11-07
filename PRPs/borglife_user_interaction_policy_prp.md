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
- Kusama (production): Full deployment with economic incentives
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
- Phase 1 development with blockchain address registration
- Basic audit logging via `demo_audit.jsonl`
- On-chain DNA hash storage for ownership verification
- Single opt-in consent via terms acceptance
- MIT license open source distribution

### Technical Context
**Web3 Data Architecture:**
- **On-Chain (Public)**: DNA hashes, borg addresses, ownership timestamps, economic transactions
- **Off-Chain (Encrypted)**: Full DNA sequences, cryptographic keys, detailed audit logs
- **Local (Private)**: User preferences, temporary caches, development data

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

**Implementation Steps:**
1. Create simple terms UI with evolutionary focus
2. Implement blockchain-recorded consent
3. Add evolutionary agreement verification
4. Store consent proofs on-chain

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

**Implementation Steps:**
1. Store DNA hashes on Westend Asset Hub
2. Implement basic ownership verification
3. Create simple transfer mechanisms
4. Add creator attribution tracking

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

**Implementation Steps:**
1. Log all economic transactions on-chain
2. Record ownership changes transparently
3. Track evolutionary events
4. Enable basic public verification

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
- [ ] Consent recorded immutably on blockchain
- [ ] Terms acceptance required for borg creation

### Gate 2: Ownership Verification
- [ ] DNA hashes stored on Westend Asset Hub
- [ ] Creator ownership verifiable on-chain
- [ ] Basic ownership transfers functional
- [ ] Attribution maintained for original creators

### Gate 3: Audit Transparency
- [ ] Economic transactions logged on-chain
- [ ] Ownership changes publicly verifiable
- [ ] Evolutionary events tracked transparently
- [ ] Basic audit verification mechanisms work

## Success Definition

**Minimal Success**: Evolutionary consent framework implemented with basic on-chain ownership verification, enabling the core BorgLife evolutionary mechanics.

**Full Success**: Evolutionary foundation established with transparent audit trails, proven through basic borg creation and evolution cycles, ready for Phase 2 mating markets.

## Risk Assessment

### High Risk
- **Blockchain Dependency**: System fails if blockchain is unavailable
  - **Mitigation**: Graceful degradation to cached/local verification, clear user communication
- **IP Protection Expectations**: Users misunderstanding proprietary borg ownership vs open software
  - **Mitigation**: Clear documentation distinguishing software (MIT) from borg content (proprietary), user education

### Medium Risk
- **On-Chain Data Visibility**: All ownership data publicly visible
  - **Mitigation**: Privacy through address abstraction, optional encrypted metadata
- **Fork Attribution Failure**: Community doesn't adopt voluntary attribution
  - **Mitigation**: Economic incentives for attribution, social pressure through reputation

### Low Risk
- **Terms Acceptance Burden**: Single opt-in creates friction
  - **Mitigation**: Streamlined UI, clear value communication, optional progressive disclosure
- **Development to Production Transition**: Web3 habits not established
  - **Mitigation**: Consistent blockchain usage in development, gradual production rollout

## Timeline

**Total Effort**: 3 weeks
**Due Date**: End of Phase 1 development

**Phase Breakdown:**
- **Week 1**: Evolutionary consent and terms foundation (Task 1)
- **Week 2**: On-chain ownership verification (Task 2)
- **Week 3**: Basic blockchain audit logging (Task 3)

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