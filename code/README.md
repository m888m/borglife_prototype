# BorgLife Code Directory

The `code/` directory contains the core BorgLife prototype implementation.

## Current Status
- **Phase 1 Complete**: DNA synthesis, phenotype execution, Archon integration
- **Phase 2A Complete**: USDB stablecoin (ID 50000313), fund holding, transfers
- **Security**: Keyring dispenser, signature verification, DNA anchoring
- **UIs**: Borg Designer [`code/borg_designer_ui.py`](code/borg_designer_ui.py), Sponsor [`code/sponsor_ui.py`](code/sponsor_ui.py)
- **Testing**: >90% coverage, E2E suite [`code/tests/e2e_test_suite.py`](code/tests/e2e_test_suite.py)

## Quick Start
```bash
# Activate venv
. ../.venv/bin/activate

# Check keyring & balances
python3 scripts/check_keyring.py

# Create USDB asset
python3 scripts/create_usdb_asset.py

# Launch UIs
streamlit run borg_designer_ui.py
streamlit run sponsor_ui.py
```

## Key Modules

### Archon Adapter [`code/archon_adapter`](code/archon_adapter/)
- Adapter for Archon MCP/RAG services
- Fallback manager, rate limiter, health checks

### Synthesis Engine [`code/synthesis`](code/synthesis/)
- DNA parser [`code/synthesis/dna_parser.py`](code/synthesis/dna_parser.py)
- Phenotype builder [`code/synthesis/phenotype_builder.py`](code/synthesis/phenotype_builder.py)

### JAM Mock & Blockchain [`code/jam_mock`](code/jam_mock/)
- Westend adapter [`code/jam_mock/westend_adapter.py`](code/jam_mock/westend_adapter.py)
- Inter-borg transfers [`code/jam_mock/inter_borg_transfer.py`](code/jam_mock/inter_borg_transfer.py)

### Security [`code/security`](code/security/)
- Secure dispenser [`code/security/secure_dispenser.py`](code/security/secure_dispenser.py)
- Keyring service [`code/security/keyring_service.py`](code/security/keyring_service.py)

### UIs
- Borg Designer: Phenotype composition
- Sponsor UI: Funding and task execution

## Scripts [`code/scripts`](code/scripts/)
See [`code/scripts/README.md`](code/scripts/README.md)

## Testing
```bash
pytest tests/ -v --cov
```

## Blockchain
- **Chain**: Westend Asset Hub
- **RPC**: wss://westend-asset-hub-rpc.polkadot.io
- **USDB**: ID 50000313, dispenser 5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD

## Docs
- Architecture: [`code/FUNCTION_ARCHITECTURE_OVERVIEW.md`](code/FUNCTION_ARCHITECTURE_OVERVIEW.md)
- Troubleshooting: [`code/TROUBLESHOOTING.md`](code/TROUBLESHOOTING.md)