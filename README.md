# Borglife prototype

Borglife is a prototype implementation of autonomous digital organisms ("borgs") that synthesize executable phenotypes from DNA configurations using Archon as the off-chain synthesis engine, integrated with Westend blockchain for asset management and JAM mock for on-chain operations.

## 🎯 Current Status
- ✅ Phase 1: DNA synthesis and phenotype execution
- ✅ Phase 2A: USDB stablecoin created (ID [`code/.borglife_config`](code/.borglife_config:17):50000313), fund holding, inter-borg transfers
- ✅ Security: Keyring-backed dispenser, signature verification, DNA anchoring
- ✅ UI: Borg Designer and Sponsor UIs at localhost:8501
- ✅ Testing: Unit, integration, E2E suites >90% coverage

## 🚀 Quick Start

### Prerequisites
- Python 3.12
- Docker Desktop
- Funded Westend account in keyring (dispenser ready with 13+ WND)

### Installation
```bash
pip install -r [`code/requirements.txt`](code/requirements.txt)
```

### Verify Setup
```bash
bash -c ". .venv/bin/activate && python3 [`code/scripts/check_keyring.py`](code/scripts/check_keyring.py)"
```

### Create USDB Asset
```bash
bash -c ". .venv/bin/activate && python3 [`code/scripts/create_usdb_asset.py`](code/scripts/create_usdb_asset.py)"
```

### Launch UIs
```bash
streamlit run [`code/borg_designer_ui.py`](code/borg_designer_ui.py)  # Designer
streamlit run [`code/sponsor_ui.py`](code/sponsor_ui.py)  # Sponsor
```

## 🏗️ Architecture

See [`code/FUNCTION_ARCHITECTURE_OVERVIEW.md`](code/FUNCTION_ARCHITECTURE_OVERVIEW.md)

Key modules:
- [`code/archon_adapter`](code/archon_adapter/) - Archon MCP/RAG integration
- [`code/synthesis`](code/synthesis/) - DNA parsing/phenotype building
- [`code/jam_mock`](code/jam_mock/) - Westend adapter, transfers
- [`code/security`](code/security/) - Keyring, compliance
- [`code/tests`](code/tests/) - Comprehensive suite

## 📖 Usage

### Blockchain Operations
- USDB transfers: [`code/jam_mock/westend_adapter.py`](code/jam_mock/westend_adapter.py:742)`transfer_usdb`
- WND transfers: [`code/security/secure_dispenser.py`](code/security/secure_dispenser.py:260)`transfer_wnd_to_borg`

### Demo Workflow
1. Design phenotype in UI
2. Test execution with organs
3. Encode to DNA
4. Fund with USDB/WND
5. Store on-chain

## 🔧 Scripts
See [`code/scripts/README.md`](code/scripts/README.md)

Key:
- [`create_usdb_asset.py`](code/scripts/create_usdb_asset.py) - Create/mint USDB
- [`check_keyring.py`](code/scripts/check_keyring.py) - Validate keys/balances
- [`usdb_faucet.py`](code/scripts/usdb_faucet.py) - Distribute USDB

## 🛡️ Security
- Keyring macOS/Linux backend
- Dispenser [`code/jam_mock/.dispenser_keystore.enc`](code/jam_mock/.dispenser_keystore.enc)
- Rate limiting, audit logs

## 🧪 Testing
```bash
pytest [`code/tests`](code/tests/) -v --cov
```

## 🔗 Blockchain
- Westend Asset Hub RPC: wss://westend-asset-hub-rpc.polkadot.io
- USDB ID: 50000313
- Dispenser: 5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD

## 📚 Docs
- Architecture: [`code/FUNCTION_ARCHITECTURE_OVERVIEW.md`](code/FUNCTION_ARCHITECTURE_OVERVIEW.md)
- Troubleshooting: [`code/TROUBLESHOOTING.md`](code/TROUBLESHOOTING.md)
- PRPs: [`PRPs/`](PRPs/)

## Contributing
See CONTRIBUTING.md
