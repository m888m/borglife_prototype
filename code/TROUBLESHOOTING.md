# BorgLife Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the BorgLife prototype.

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

## 🛠️ Advanced Troubleshooting

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
./scripts/dev.sh restart
```

### Manual Service Testing

**Test Archon RAG:**
```bash
curl -X POST http://localhost:8181/api/knowledge/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

**Test MCP tool:**
```bash
curl -X POST http://localhost:8051/tools/test-tool/call \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

**Test phenotype execution:**
```python
from proto_borg import create_proto_borg
import asyncio

async def test():
    borg = await create_proto_borg()
    result = await borg.execute_task("Hello world")
    print(result)

asyncio.run(test())
```

### Log Analysis

**View all logs:**
```bash
./scripts/dev.sh logs
```

**Filter logs:**
```bash
# Errors only
./scripts/dev.sh logs 2>&1 | grep -i error

# Specific service
./scripts/dev.sh logs borglife-ui | tail -50
```

**Save logs for analysis:**
```bash
./scripts/dev.sh logs > debug_logs.txt
```

### Network Issues

**Check network connectivity:**
```bash
# Test internal network
docker-compose exec borglife-ui ping archon-server

# Test external connectivity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**DNS resolution:**
```bash
docker-compose exec borglife-ui nslookup google.com
```

### Environment Validation

Run comprehensive validation:
```bash
python3 scripts/validate_prerequisites.py --verbose
```

This checks:
- Environment variables
- Service connectivity
- Dependencies
- Permissions
- Resource availability

## 📞 Getting Help

### Community Support

- **GitHub Issues**: Report bugs and request features
- **Discord**: Real-time community support
- **Documentation**: Check README.md and API docs

### Diagnostic Information

When reporting issues, include:

```bash
# System info
uname -a
docker --version
python3 --version

# Service status
./scripts/dev.sh status

# Recent logs
./scripts/dev.sh logs | tail -100

# Environment (redact secrets)
cat .env | grep -v -E "(KEY|SECRET|PASSWORD)" | head -20
```

### Emergency Recovery

If all else fails:

```bash
# Nuclear option - complete reset
./scripts/dev.sh clean
rm -rf venv/
rm -f .env
git clean -fdx
# Then follow setup instructions again
```

## 🔍 Error Code Reference

| Error Code | Description | Solution |
|------------|-------------|----------|
| `ARCHON_UNAVAILABLE` | Archon services down | Check Archon containers |
| `DNA_INVALID` | DNA parsing failed | Validate YAML syntax |
| `INSUFFICIENT_FUNDS` | Borg wealth too low | Add funding |
| `RATE_LIMITED` | Too many requests | Wait or upgrade plan |
| `ORGAN_FAILED` | Docker MCP organ error | Check organ credentials |
| `VALIDATION_ERROR` | Input validation failed | Check input format |
| `NETWORK_ERROR` | Connection failed | Check network config |

## 🚀 Performance Tuning

### Memory Optimization

```yaml
# docker-compose.yml adjustments
services:
  borglife-ui:
    environment:
      - STREAMLIT_SERVER_MEMORY_LIMIT=1GB
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

### Caching Configuration

```python
# Increase cache TTL
config.cache_default_ttl = 3600  # 1 hour
config.redis_url = "redis://redis:6379/1"  # Use DB 1
```

### Rate Limiting

```python
# Adjust limits
config.rate_limit_requests_per_hour = 1000
config.rate_limit_burst_limit = 100
```

Remember: BorgLife is in active development. Most issues are resolved in updates, so ensure you're running the latest version!