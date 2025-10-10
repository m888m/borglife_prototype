# Borglife Phase 1 Prototype

A decentralized compute platform enabling the evolution of autonomous digital organisms ("borgs") on JAM, implementing the first phase as described in the [Borglife Whitepaper](../borglife_whitepaper/borglife-whitepaper.md).

## Overview

This prototype demonstrates borg autonomy through:
- **Static AI Agent**: PydanticAI-powered task execution with wallet integration
- **DNA System**: YAML-based encoding/decoding with PVM foundations
- **On-Chain Storage**: Kusama testnet anchoring with mock JAM phases
- **Sponsor UI**: Streamlit dashboard for interactions and monitoring
- **Archon Integration**: MCP organs and Docker orchestration
- **End-to-End Validation**: Comprehensive testing and demo loop

## Architecture

```
Proto-Borg (Python/PydanticAI)
    ↓
DNA Encoding (YAML/PVM)
    ↓
On-Chain Storage (Kusama/Mock JAM)
    ↓
Sponsor UI (Streamlit)
    ↓
Archon MCP (FastAPI)
```

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install pydantic-ai substrate-interface streamlit fastapi uvicorn pyyaml
   ```

2. **Run Demo**:
   ```bash
   python integration_test.py
   ```

3. **Start UI**:
   ```bash
   streamlit run sponsor_ui.py
   ```

4. **Run MCP Server**:
   ```bash
   python archon_integration.py
   ```

5. **Docker Deployment**:
   ```bash
   docker-compose up --build
   ```

## Components

- `proto_borg.py`: Main AI agent with wealth tracking
- `dna_system.py`: DNA encoding/decoding system
- `pvm_foundation.rs`: Rust foundations for PVM bytecode
- `on_chain.py`: Kusama storage and JAM mocks
- `sponsor_ui.py`: Streamlit dashboard
- `archon_integration.py`: MCP server for organs
- `integration_test.py`: End-to-end testing and demo

## Key Features

- **Autonomous Wealth Management**: \(\Delta(W) = R - C\) enforcement
- **Hybrid Architecture**: On-chain verifiability, off-chain flexibility
- **Round-Trip Integrity**: DNA encoding/decoding validation
- **Mock JAM Phases**: Simulate refine/accumulate without delays
- **MCP Organs**: Swappable AI services via Archon
- **Real-Time Monitoring**: UI for sponsors and borg tracking

## Testing

Run integration tests:
```bash
python -m pytest integration_test.py -v
```

Or run demo:
```bash
python integration_test.py
```

## Documentation

- [Discussion Document](discussion.md): Implementation approaches and trade-offs
- [PRPs](prps.md): Detailed blueprint with tasks and criteria
- [Whitepaper](../borglife_whitepaper/borglife-whitepaper.md): Full technical specification

## Next Steps

Phase 2 will introduce:
- Dynamic GP evolution
- Full PVM bytecode
- Real JAM integration
- Ethical oracles
- Multi-borg swarms

## License

See [LICENSE.md](LICENSE.md) for details.