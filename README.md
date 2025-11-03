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
   pip install -r code/requirements.txt
   ```

2. **Run Demo**:
   ```bash
   python -m code.tests.e2e_test_suite
   ```

3. **Start UI**:
   ```bash
   streamlit run code/sponsor_ui.py
   ```

4. **Run MCP Server**:
   ```bash
   python -m code.archon_adapter.adapter
   ```

5. **Docker Deployment**:
   ```bash
   docker-compose -f code/docker-compose.yml up --build
   ```

## Components

- `code/proto_borg.py`: Main AI agent with wealth tracking
- `code/synthesis/`: DNA encoding/decoding system (dna_parser.py, phenotype_builder.py)
- `code/jam_mock/`: JAM blockchain mock and on-chain storage simulation
- `code/sponsor_ui.py`: Streamlit dashboard
- `code/archon_adapter/`: MCP server for organs and Archon integration
- `code/tests/e2e_test_suite.py`: End-to-end testing and demo

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
python -m pytest code/tests/ -v
```

Or run demo:
```bash
python -m code.tests.e2e_test_suite
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