# BorgLife Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the BorgLife prototype.

## 🚀 Quick Diagnosis

Run the diagnostic script:
```bash
./scripts/validate_prerequisites.py
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
docker-compose restart archon-server archon-mcp archon-agents
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

**Check borg wealth:**
```python
from proto_borg import create_proto_borg
import asyncio

async def check_wealth():
    borg = await create_proto_borg("test-borg")
    status = await borg.get_status()
    print(f"Wealth: {status['wealth']} DOT")

asyncio.run(check_wealth())
```

**Add funding:**
```python
# In UI: Go to Funding tab and add DOT
# Or programmatically:
borg.wealth.log_transaction("funding", 1.0, "DOT", "Manual funding")
```

**Check rate limits:**
```python
# Check if rate limited
from archon_adapter import ArchonServiceAdapter
adapter = ArchonServiceAdapter()
allowed, usage, limit = await adapter.rate_limiter.check_limit("borg-id", "organ-name", 1.0)
print(f"Rate limit: {usage}/{limit}")
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