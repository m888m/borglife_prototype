# Contributing to Borglife

Thanks for your interest in Borglife! 

We're building a JAM-based platform for evolving autonomous digital organisms ("borgs")— AI that can act autonomously and adapts through market forces and genetic programming. 

**Contributions are welcome**, big or small: code, docs, ideas, or feedback. 
This guide keeps it straightforward and focused on Phase 1 to build a working prototype fast.

## Why Contribute?

- Shape the future of decentralized AI: Borgs evolve on JAM's trustless substrate, solving real-world challenges like your own personalized teacher, automated passive income via your personal trading borg army, humanoid companions that evolve next to you without centralized monitoring, etc.
- Quick impact: Phase 1 prioritizes verifiable basics and user-friendly onboarding—perfect for AI builders, Polkadot/JAM devs, or anyone excited about off-chain/on-chain hybrid systems.
- Community-driven: Join discussions across ecosystems (e.g., Dynamous Community, Polkadot forums) and help foster open-ended evolution.

No rush—start small! If stuck, comment on an issue or ping in discussions.

## How to Contribute

1. **Fork and Clone**:
   1. Fork the repo: <https://github.com/m888m/borglife_prototype> .
   2. Clone locally:
   `git clone https://github.com/yourusername/borglife_prototype.git` .
2. **Discuss Ideas**: Open an issue for questions, bugs, or suggestions—label "discussion" or "prototype" to tie into Phase 1.
3. **Submit Changes**: Create a branch (e.g., `feature/proto-borg-phenotype`), commit with clear messages (e.g., "feat: add wallet integration to proto-borg"), and open a PR linking to relevant issues.
4. **Code Style**: Use Python for off-chain (PEP8, PyTest), Rust for on-chain (Rustfmt, Cargo test). Include docs/tests where possible.
5. **Review Process**: We'll check PRs within 1-2 days—emphasis on Phase 1 alignment (e.g., does it advance the simplified borg loop?).

Setup tip: Use Archon for off-chain synthesis[](https://github.com/coleam00/archon), Docker for the stack, py-substrate-interface for Python wallet ops, subxt for Rust JAM interactions, and Polkadot.js for testnet. Add lockfiles (requirements.txt/poetry for Python, Cargo.lock for Rust) for dependency consistency.

## Phase 1 Focus: Prototype (8-12 Weeks)

**We're starting simple:**

- Build a proto-borg phenotype as a static AI agent with wallet for sponsorships/bounties, derive DNA encoding, store wealth/DNA on Kusama testnet (with JAM mocks for phases like refine/accumulate), enable decoding.
- Leverage Archon for synthesis (extend its agents/MCP for cells/organs).
- Add basic sponsor UI.
  
**Goal**:
End-to-end demo of funding → execution → encoding → storage → decoding, with 80/20 pragmatism to remove blockers fast.

### Logical Task Overview

To build the prototype logically, tasks flow in a sequence with dependencies—start from the core phenotype and build outward.
This ensures we validate the borg lifecycle step-by-step.
In the prototype phase, we use Kusama testnet for on-chain (stable, JAM-compatible APIs) and mock JAM specifics to build reusable knowledge without delays:

1. **Proto-Borg Phenotype**:  Create a static AI agent with wallet for funds/costs. This is the foundation—everything else builds on a working "body."
   - Ties into: Provides the structure to encode into DNA; tests sponsorship intake.
2. **DNA Encoding/Decoding**: Serialize the phenotype into PVM DNA and reverse it to recreate the agent.
   - Depends on: Proto-borg (to derive real encoding from a concrete example).
   - Ties into: Enables on-chain storage and borg recreation.
3. **On-Chain Storage**: Anchor DNA hashes and wealth on Kusama testnet (mock JAM phases).
   - Depends on: Encoding/decoding (to have DNA ready for storage).
   - Ties into: Verifies trustless persistence; links off-chain runs to on-chain scarcity.
4. **Sponsor UI & Monitoring**: Build dashboard for funding and observing borgs.
   - Depends on: Proto-borg (for what to monitor) and storage (for wealth tracking).
   - Ties into: Drives adoption by enabling easy sponsorship and feedback loops.
5. **Archon Extensions & Infra**: Enhance Archon and Dockerize the stack for reproducibility.
   - Depends on: All above (integrates them into a cohesive off-chain environment).
   - Ties into: Supports the hybrid model; adds modularity for future organs/cells (e.g., via MCP/RAG hooks, defer ethics).

Parallel work is possible (e.g., docs alongside any), but aim for this flow to hit the demo milestone. We'll auto-organize via issues/PRs, with light top-down steering (e.g., priority labels).

### Soft Milestones

These are guides, not rigid—adjust based on contrib flow:

- Weeks 1-4: Phenotype + encoding (core loop basics).
- Weeks 5-8: Storage + UI (adoption hooks).
- Weeks 9-12: Integration, demo, and 80/20 polish (basic tests/ops).

### Notes

- **Risks**: Track in a dedicated issue (e.g., "Phase 1 Risks"): JAM alphas monitored for switch; fallback to Kusama ensures progress.
- **Security**: Use testnet-only; include basic logging in phenotype for future ethics.
- **Testing**: Basic unit/integration in PRs; add a smoke test script for the loop.
- **Ops**: GitHub Actions for lint/test on PRs to catch issues early.

- **License**: Code under MIT LICENSE; see LICENSE.md.

### Pick a task or suggest one

- **Easy: Feedback & Docs**
  - Review whitepaper Section 4; suggest clarifications or tutorials (e.g., "Proto-Borg Setup Guide" with Archon/wallet steps) or flow diagrams. Time: 30-60 mins. Good first issue!
- **Medium: Proto-Borg Phenotype**
  - Build a static AI agent in Python (e.g., using PydanticAI for basic task logic).
  - Integrate Polkadot wallet via py-substrate-interface for funding (sponsorships) and mock costs.
  - Test with simple bounty win; add basic logging. (Deps: Archon agents service)
- **Medium: DNA Encoding/Decoding**
  - From proto-borg, serialize config (cells/organs as YAML) to PVM bytecode DNA; implement forward (DNA to agent) and reverse mappings in Python.
  - Test round-trip integrity. (Deps: Archon for phenotype assembly)
- **Medium: UI for Sponsors** (Key for adoption!)
  - Create Streamlit dashboard for sponsorship creation (wallet transfers) and monitoring (borg logs, Δ(W), outputs).
  - Prototype bounty posting.
  - Use Archon's WebSockets for real-time.
- **Advanced: On-Chain Storage**
  - Use Rust/subxt to store DNA hashes and wealth on Kusama testnet (mock JAM phases).
  - Integrate with off-chain decoding to recreate borgs. (Deps: Docker/Substrate)
- **Advanced: Archon Extensions**
  - Enhance Archon for borg needs:
    - Add MCP wrappers for organs,
    - RAG queries for cells, or
    - libp2p for basic coordination.

    Defer ethical checks to Phase 2.
- **Open: Sponsorship & Infra**
  - Off-chain storage (Supabase/IPFS); ensure quick borg activation.
  - Suggest tools like py-substrate-interface tweaks. New ideas welcome!

All tasks tie to whitepaper: trustless JAM core, efficient off-chain synthesis via Archon, ethical safeguards. 

Let's get a demo running—questions? Open an issue or DM @m888m. 
Let's evolve this! 🚀
