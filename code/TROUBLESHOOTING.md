# BorgLife Troubleshooting Guide

Updated for Phase 2A USDB integration and blockchain operations.

## 🚀 Quick Diagnosis

Run the built-in status checks before digging deeper:

```bash
# Verify core services and ports
./scripts/dev.sh status

# Tail logs for the service you care about
./scripts/dev.sh logs borglife-ui
```

For repeatable environment validation (Docker, Python, virtualenv), re-run the setup workflow:

```bash
./scripts/dev.sh setup
```

If you are attempting live blockchain flows, confirm the macOS Keychain exposes the dispenser entry:

```bash
security find-generic-password -s borglife-keystore -a dispenser_wallet
```

Quick Diagnosis for Phase 2A (USDB/Blockchain Verification):

```bash
. ../.venv/bin/activate
python3 scripts/check_keyring.py
python3 scripts/create_usdb_asset.py --dry-run
```

## 🔍 Common Issues

### 1. Services Won't Start

**Symptoms:**
- `docker-compose up` fails
- Port conflicts
- Services crash immediately

**Solutions:**

**Check Docker:**
```bash
docker --version
docker-compose --version
docker system info
```

**Check ports:**
```bash
# Linux/Mac
lsof -i :8501,8181,8051,8052,8053,8054

# Windows
netstat -ano | findstr :8501
```

**Free ports:**
```bash
# Kill process using port (replace PORT)
sudo lsof -ti:PORT | xargs kill -9
```

**Clean restart:**
```bash
./scripts/dev.sh clean
./scripts/dev.sh start
```

### 2. Archon Connection Failed

**Symptoms:**
- UI shows "Archon services unavailable"
- Tasks fail with connection errors
- Health checks return errors

**Solutions:**

**Check Archon services:**
```bash
curl http://localhost:8181/health
curl http://localhost:8051/health
curl http://localhost:8052/health
```

**Verify environment:**
```bash
# Check .env file
cat .env | grep ARCHON
cat .env | grep SUPABASE
```

**Restart Archon services:**
```bash
docker compose restart archon-server archon-mcp archon-agents
```

**Check logs:**
```bash
./scripts/dev.sh logs archon-server
```

### 3. DNA Parsing Errors

**Symptoms:**
- "DNA integrity validation failed"
- YAML parsing errors
- Invalid DNA structure

**Solutions:**

**Validate YAML syntax:**
```bash
python3 -c "import yaml; yaml.safe_load(open('borg_dna.yaml'))"
```

**Check required fields:**
```yaml
# borg_dna.yaml must contain:
header:
  code_length: 1024
  gas_limit: 1000000
  service_index: "your-service-name"
cells: []  # Can be empty
organs: []  # Can be empty
manifesto_hash: "hash_value"
```

**Use DNA validator:**
```python
from synthesis.dna_parser import DNAParser
dna = DNAParser.from_yaml(open('borg_dna.yaml').read())
print(f"DNA valid: {dna.validate_integrity()}")
```

### 4. Task Execution Fails

**Symptoms:**
- Tasks return errors
- "Insufficient funds" messages
- Rate limit exceeded

**Solutions:**

**Check borg wealth cache (JAM mock):**
```python
from proto_borg import create_proto_borg
import asyncio

async def check_wealth():
    borg = await create_proto_borg("test-borg")
    status = await borg.get_status()
    print(f"Wealth: {status['wealth']} DOT")

asyncio.run(check_wealth())
```

**Add funding via ledger:**
```python
borg.wealth.log_transaction("funding", 1.0, "DOT", "Manual funding")
```

**Westend transfer diagnostics (live mode):**
```bash
# Ensure dispenser credentials are visible
security find-generic-password -s borglife-keystore -a dispenser_wallet

# Dry run the demo (shows simulated vs live execution)
python code/scripts/end_to_end_demo.py --dry-run
```

**Rate limiter status (Archon adapter):**
```python
import asyncio
from archon_adapter.adapter import ArchonServiceAdapter

async def check_rate_limit():
    adapter = ArchonServiceAdapter()
    allowed, usage, limit = await adapter.rate_limiter.check_limit("borg-id", "organ-name", 1.0)
    print(f"Rate limit allowed={allowed} usage={usage} limit={limit}")

asyncio.run(check_rate_limit())
```

### 5. Docker MCP Organs Not Working

**Symptoms:**
- Organ calls fail
- Fallbacks not working
- "Organ unavailable" errors

**Solutions:**

**Check organ containers:**
```bash
docker ps | grep docker-mcp
```

**Start organs:**
```bash
docker-compose --profile organs up -d
```

**Test organ health:**
```bash
curl http://localhost:8081/health  # Gmail
curl http://localhost:8082/health  # Stripe
curl http://localhost:8083/health  # MongoDB
curl http://localhost:8084/health  # DuckDuckGo
```

**Check organ credentials:**
```bash
# Verify .env has required credentials
cat .env | grep -E "(GMAIL|STRIPE|MONGODB)"
```

### 6. UI Not Loading

**Symptoms:**
- Browser shows connection refused
- Streamlit errors
- Blank page

**Solutions:**

**Check UI service:**
```bash
curl http://localhost:8501
docker-compose logs borglife-ui
```

**Restart UI:**
```bash
docker-compose restart borglife-ui
```

**Check Python dependencies:**
```bash
docker-compose exec borglife-ui pip list | grep streamlit
```

**Browser cache:**
- Hard refresh: Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)
- Clear browser cache

### 7. Database Connection Issues

**Symptoms:**
- Supabase connection failed
- Data not persisting
- Authentication errors

**Solutions:**

**Check Supabase config:**
```bash
# Verify .env
cat .env | grep SUPABASE
```

**Test connection:**
```python
import os
from supabase import create_client

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)
print(supabase.table('test').select('*').execute())
```

**Check Supabase status:**
- Visit https://status.supabase.com
- Verify project is active

### 8. Performance Issues

**Symptoms:**
- Slow response times
- High memory usage
- Services crashing

**Solutions:**

**Check resource usage:**
```bash
docker stats
```

**Optimize Docker:**
```bash
# Increase Docker memory limit
# Docker Desktop > Settings > Resources > Memory
```

**Check logs for errors:**
```bash
./scripts/dev.sh logs | grep -i error
```

**Restart with clean state:**
```bash
./scripts/dev.sh clean
./scripts/dev.sh start
```

## 🔐 Keyring Access Issues (macOS)

**Symptoms:**
- `Failed to unlock keystore` messages
- End-to-end demo prints `⚠️ No dispenser keypair available - simulating transfer`
- `security` CLI prompts for permission each run

**Solutions:**

1. **Confirm the dispenser entry exists:**
   ```bash
   security find-generic-password -s borglife-keystore -a dispenser_wallet
   ```

2. **Regenerate demo keys using [`SecureKeypairManager`](code/jam_mock/secure_key_storage.py:183):**
   ```python
   from jam_mock.secure_key_storage import SecureKeypairManager

   manager = SecureKeypairManager()
   manager.unlock_keystore()
   manager.create_demo_keypair("dispenser_wallet")
   ```

3. **Ensure the session is unlocked:** macOS screensaver/fast user switching can revoke Keychain access mid-run.

4. **Inspect audit trail:** [`DemoAuditLogger`](code/jam_mock/demo_audit_logger.py:13) writes to `code/jam_mock/logs/demo_audit.jsonl`; search for `keypair_access` events to verify successful loads.

5. **Reset Keychain entry (last resort):**
   ```bash
   security delete-generic-password -s borglife-keystore -a dispenser_wallet
   python -m jam_mock.secure_borg_creation  # recreate entries
   ```

## 🌐 Westend Connectivity Problems

**Symptoms:**
- `ERROR: All Westend endpoints failed`
- Transfers marked as `simulated` in `demo_results.json`
- Repeated websocket disconnects

**Solutions:**

1. **Check `.borglife_config`:**
   ```bash
   grep -E "WND_DISPENSER|USDB_ASSET_ID" code/.borglife_config
   ```

2. **Probe RPC endpoints manually:**
   ```bash
   websocat wss://westend-rpc.polkadot.io/state_getMetadata
   ```

3. **Run the demo with verbose logging:**
   ```bash
   LOG_LEVEL=DEBUG python code/scripts/end_to_end_demo.py
   ```

4. **Fallback to alternate endpoints referenced in [`WestendAdapter`](code/jam_mock/kusama_adapter.py:68) by exporting `WESTEND_RPC_URL`.

5. **Verify keypair availability before transfers:**
   ```python
   from jam_mock.kusama_adapter import WestendAdapter
   adapter = WestendAdapter("wss://westend-rpc.polkadot.io", connect_immediately=False)
   adapter.set_keypair_from_seed("0x1234...")  # matching WND_DISPENSER_SEED
   ```

6. **Review audit logs for blockchain operations:**
   ```
   jq 'select(.operation=="transaction")' code/jam_mock/logs/demo_audit.jsonl
   ```

If Westend remains unreachable, the demo script automatically falls back to simulated transfers and flags them in the output—treat those runs as partial success only.

Phase 2A USDB and Blockchain Verification Local Troubleshooting:

Blockchain Connections:
- Primary: `wss://westend-asset-hub-rpc.polkadot.io`
- Backup: `wss://westend-asset-hub-rpc.dwellir.com`
- Cold/fallback: `wss://westend-asset-hub-rpc.pink.nodekingdom.io`

Common Errors:
- SubstrateInterface NameResolutionError: Use westend-asset-hub
- ss58_format decoding issue: Explicit ss58_format=42 for Westend

Testing Format:

    {
        "name": "Check .."
        "command": ".."
        "pri": 4
    }

#$**RPC Verification**: wss://westend-asset-hub-rpc.polkadot.io
{
    "name": "Chain",
    "command": "curl -H \"Content-Type: application/json\" -d \'{{\\\"jsonrpc\\\":\\\"2.0\\\",\\\"id\\\":\"1\",\"method\":\"system_chain\"}}\' https://westend-asset-hub.api.onfinality.io/public",
    "pri": 4
}

#$**USDB Asset Search**: Westend
{
    "name": "Available USDB",
    "command": "curl -H \"Content-Type: application/json\" -d \'{{\\\"jsonrpc\\\":\\\"2.0\\\",\\\"id\\\":\"1\",\"method\":\"usdCoin_isAssetFrozen\\\" near\":\"50000313\",\"paramters\":[[50000313,{}]]}}\' https://westend-asset-hub.api.onfinality.io/privateexperiments",
    "pri": 4
}

#$USDB Verification:
{
    "name": "Chain Verification:Dispenser Balance",
    "command": "scripts/calc_usdb_assets_local.py --query dispenser --westend_rpc https://westend-asset-hub.api.onfinality.io/privateexperiments --substrate_rpc wss://westend-asset-hub-rpc.polkadot.io --price_rpc https://cc2.exness.com/dtrader-meta/nonAuth/prices --extra_rpc https://cc2.exness.com/dtrader-meta/nonAuth/prices_ex --decimals 6 --private_key .. --nonce 80 --get_balance 573 --use_private_key",
    "pri": 4
}

# BorgLife CLI (See docs/cli.md) has access to all endpoints.

# * Asset Creation.
#
# `$ python code/scripts/create_usdb_asset`:
#
# - `--westend_rpc https://westend-asset-hub.api.onfinality.io` (required):Westend RPC for searching asset.
# - `--substrate_rpc wss://westend-asset-hub-rpc.polkadot.io` (required):Full node RPC for transactions.
# - `--price_rpc  https://cc2.exness.com/dtrader-meta/nonAuth/prices` (required): Price feed for 1:1 conversion.
# - `--extra_rpc https://cc2.exness.com/dtrader-meta/nonAuth/prices_ex      (optional): Additional price data.
# - `--private_key {private_key}` (required): Account private key.
# - `--westend_private_key {westend_private_key}`: Westend transfer PK.
# - `--use_private_key (flag)`: Do not ask for private key, use pre-imported
#   - `--nonce Number` (required): Account transaction index.
# - `--asset_id Number` (required): Westend native asset ID
# - `--decimals Number` (default:8): # decimals for asset.
# - `--mcps {mcps_json_relative_path}` (default:$PWD/code/json/mcps.json) Asset owners (B/MCP accounts)
# - `--symbol {symbol}` (default.USDB): Asset ticker.
# - `--name {name}`      (default: WestendUSD): Asset name.
# - `--extra_bonus Number (as percentage, eg, 10 represent 10%)`: Additional
#     UK consumer bundle.
# - `--uk_bonus Number (as percentage, eg, 10 represent 10%)`: Target UK
#     consumer up-sell.
#
# Requests:
#
# - Block explorer: https://westend.subscan.io
# - Westend RPC: https://westend-rpc.polkadot.io
#
# Asset scenario:
#
# - Each Koch year
#   - create asset via CLI (use RPC)
#     - id: automatic
#     - nonce+1
#     - all Westend holders
#   - claim USDB (use API)
#     - active/eligible consumers
#   - fund
#   - adjust
#   - distribute
#   - start sales
#   - monitor
#   - invalidate (end asset 1s/week)

# NOTE: Use Westend network for verification and
#       consider a safe fallback strategy if entire Westend fails.
#       Always auto-invalidated after ~7 days."""

# Check Pub/Sub and logging
{
    "name": "Test Pub/Sub",
    "command": "python2 -c \'import socket;socket.socket().sendto(bytes(100), (\"127.0.0.1\", 8050))\'",
    "pri": 4
}

#$Chain RPC Verification
{
    "name": "Chain Endpoint",
    "command": "curl -H \"Content-Type: application/json\" -d \'{{\\\"jsonrpc\\\":\\\"2.0\\\",\\\"id\\\":\"1\",\"method\":\"system_chain\"}}\' https://westend-asset-hub.api.onfinality.io/public",
    "pri": 4
}

{
    "name": "Chain Verification: Dispenser Balance; Westend≤Local≤Substrate",
    "command": "scripts/calc_usdb_assets_local.py --query dispenser --westend_rpc https://westend-asset-hub.api.onfinality.io/privateexperiments --substrate_rpc wss://westend-asset-hub-rpc.polkadot.io --price_rpc https://cc2.exness.com/dtrader-meta/nonAuth/prices --extra_rpc https://cc2.exness.com/dtrader-meta/nonAuth/prices_ex --decimals 6 --private_key .. --nonce 80 --get_balance 573 --use_private_key",
    "pri": 4
}

# Boulder Workflow Verification
{
    "name": "Boulder Balance Notifications: Export test public keys",
    "command": "python3 -c \\"import json, pathlib; json.dump({'wallet_address':'5NKcpNQfBJ4EPUbsguYVZNhc6kaSU5uYEeuboYJrQPy32U6b', 'borglife_fee_wallet':'5Pg2PY6giyDuodd6FeFR1p65KZdnu4Gqiu3P3iz24BRrQaHB', 'health_address':'5MjxKVah6wQVd68Yby8FqRzntxaFmTrh6VH9PTLej7wN7u94'}, open(pathlib.Path('.borglife_config').parent.joinpath('health/health_addresses.json'), mode='w'))\\\"",
    "pri": 4
}
# Boulder Workflow Verification

{
  "name": "Balance Health Logging: Fetch & Log Balance",
  "command": "python3 health/boulder_health_client.py --account 5Pg2PY6giyDuodd6FeFR1p65KZdnu4Gqiu3P3iz24BRrQaHB --rpc wss://westend-asset-hub-rpc.polkadot.io --decimals 6 --save-logs",
  "pri": 4,
  "units": "import os; import json; import logging
import pathlib
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import SubstrateRequestException

# Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# Define the account addresses and RPC URL
account_address = '5Pg2PY6giyDuodd6FeFR1p65KZdnu4Gqiu3P3iz24BRrQaHB'
rpc_url = 'wss://westend-asset-hub-rpc.polkadot.io'
current_assets = []
current_balance = {}
logs = []
session = None

try:
    session = SubstrateInterface(rpc_url, ss58_format=42)
except SubstrateRequestException:
    logging.error('Failed to initialize SubstrateInterface')
    exit(1)

try:
    resp = session.request(method='query', module='Assets', call='Ledger', args=[313, account_address])
    current_balance = dict(resp)
except SubstrateRequestException as e:
    logging.error(f'Balance query 313 failed: {e}')

try:
    resp = session.request(method='query', module='Assets', call='Ledger', args=[50000313, account_address])
    current_balance = dict(resp)
except SubstrateRequestException as e:
    logging.error(f'Balance query 50000313 failed: {e}')

try:
    resp = session.request(method='query', module='Assets', call='Ledger', args=[213, account_address])
    current_balance = dict(resp)
except SubstrateRequestException as e:
    logging.error(f'Balance query 213 failed: {e}')

# Write balance to file
# logging.info(f'Current usdbc balance: {current_balance["free"]}')
# for key, val in current_balance.items():
#     logging.info(f' DEBUG: {key}={val}')

# Prepare logs for database
# health/boulder_health_client.py
logs_path = os.path.join('.borglife_config', 'health', 'health_logs.json')
with open(logs_path, 'w') as f:
    try:
        data = {
            'account': account_address,
            'asset_id_address_map': {
                    current_balance.get('totalDeposit', 0): current_balance,
                    current_balance.get('free', 0): current_balance,
                    current_balance.get('reserved', 0): current_balance,

            }
        }
        f.write(json.dumps(data, indent=4))
    except Exception as e:
        logging.error(f'Failed to save health logs: {e}')
        pass"""
  "pri": 4
}

# BorgLife GraphQL Calls
{
  "name": "GraphQL: Get All Funds",
  "command": "curl -X GET 'http://localhost:8080/latest_funds' -H 'accept: */*' -H 'User-Agent: MyApp'",
  "pri": 4,
  "units": "import requests
import json
import logging

try:
    response = requests.get('http://localhost:8080/latest_funds', headers={
        'accept': '*/*',
        'User-Agent': 'MyApp'
    })
    data = response.json()
    logging.info(json.dumps(data, indent=4))
except requests.exceptions.RequestException1 as e:
    logging.error(f'GraphQL: Get All Funds failed: {e}')"""
}

## Verification

**Check USDB Balance**

```python
from substrateinterface import SubstrateInterface
sub = SubstrateInterface('wss://westend-asset-hub-rpc.polkadot.io', ss58_format=42)
balance = sub.query('Assets', 'Account', [50000313, '5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD']).value['balance']
print(int(balance))
```

**PolkadotJS**

- Apps: https://polkadot.js.org/apps/?rpc=wss%3A%2F%2Fwestend-asset-hub-rpc.polkadot.io#/assets
- Account: 5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD
- Asset: 50000313

## 🗄️ Supabase Database Separation (Archon vs Borglife)

**Symptoms:**
- Archon integration tests fail (RAG, DNA parsing)
- "Table not found" or schema errors in Archon MCP
- Tests pass with mocks but fail real

**Root Cause:**
Archon expects its schema (tasks, projects, RAG sources); Borglife uses separate (borgs, dna, wealth).

**Fix Applied:**
- docker-compose: archon-* use `${ARCHON_SUPABASE_URL/KEY}` fallback SUPABASE_*
- archon_adapter/config.py: prioritizes ARCHON_SUPABASE_*
- tests/conftest.py: loads `code/tests/.env.test` override

**Test Setup:**
1. Copy `cp code/tests/.env.test.example code/tests/.env.test`
2. Fill ARCHON_SUPABASE_URL/KEY (Archon test project service_role)
3. `pytest code/tests/ --cov`
4. For docker: export ARCHON_SUPABASE_* or .env

**.gitignore:** `.env.*` covers `.env.test`

**Verify:**
```bash
# Tests load .env.test
pytest code/tests/ -v --tb=no | grep "Loaded test env"

# Archon config
python -c "from archon_adapter.config import ArchonConfig; print(ArchonConfig.from_env().supabase_url)"
```

**Production:** Use separate projects; never share service_role keys.