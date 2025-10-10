# Borglife-Archon Integration Strategy: Comprehensive Architecture Plan

## Executive Summary

This plan designs a flexible, future-proof integration between borglife_prototype and archon that accommodates archon's rapid evolution without creating brittle coupling. The strategy uses an **Adapter Pattern with Service Discovery** to isolate borglife from archon's internal changes while exposing necessary functionality through stable interfaces.

---

## 1. Architecture Analysis

### 1.1 Archon's Stable Integration Points

Based on analysis of archon's codebase, the following are **stable integration surfaces**:

**Stable (Safe to depend on):**
- **HTTP REST APIs** (port 8181): Core business logic endpoints
- **MCP Protocol Interface** (port 8051): Standardized MCP tools via SSE/HTTP
- **Database Schema**: Supabase tables (sources, documents, projects, tasks)
- **Environment Variables**: SUPABASE_URL, SUPABASE_SERVICE_KEY
- **Docker Compose Services**: archon-server, archon-mcp, archon-agents

**Volatile (Avoid direct coupling):**
- Internal Python modules (`src/server/services/*`)
- Frontend components and UI state
- WebSocket event formats (recently migrated to HTTP polling)
- Internal service discovery mechanisms
- Specific library versions (crawl4ai, pydantic-ai)

### 1.2 Borglife's Integration Needs

From [`discussion.md`](discussion.md) and [`prps.md`](prps.md):

1. **MCP Organs**: Reusable AI services (LLM inference, RAG queries)
2. **Knowledge Management**: Document storage and semantic search
3. **Task Management**: Project/task tracking for borg operations
4. **Real-time Updates**: Progress monitoring for async operations
5. **Supabase Access**: Shared database for off-chain data

---

## 2. Integration Architecture Design

### 2.1 Abstraction Layer: The Archon Service Adapter

```
┌─────────────────────────────────────────────────────────────┐
│                    Borglife Prototype                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐    │
│  │ Proto-Borg │  │ DNA System │  │ Sponsor UI         │    │
│  └─────┬──────┘  └─────┬──────┘  └──────┬─────────────┘    │
│        │               │                 │                   │
│        └───────────────┴─────────────────┘                   │
│                        │                                      │
│        ┌───────────────▼────────────────────┐                │
│        │   ArchonServiceAdapter (Facade)    │                │
│        │  - Stable interface for borglife   │                │
│        │  - Version compatibility checks    │                │
│        │  - Graceful degradation            │                │
│        │  - Retry logic & circuit breakers  │                │
│        └───────────────┬────────────────────┘                │
│                        │                                      │
└────────────────────────┼──────────────────────────────────────┘
                         │ HTTP/MCP Protocol
                         │
┌────────────────────────▼──────────────────────────────────────┐
│                      Archon Services                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ archon-server│  │  archon-mcp  │  │  archon-agents   │   │
│  │  (port 8181) │  │  (port 8051) │  │  (port 8052)     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────────┘   │
│         └──────────────────┴──────────────────┘               │
│                            │                                   │
│                    ┌───────▼────────┐                         │
│                    │    Supabase    │                         │
│                    │   PostgreSQL   │                         │
│                    └────────────────┘                         │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 Adapter Pattern Implementation

**Core Principles:**
1. **Interface Segregation**: Borglife only depends on what it needs
2. **Dependency Inversion**: Depend on abstractions, not implementations
3. **Circuit Breaker**: Fail gracefully when archon is unavailable
4. **Version Negotiation**: Check compatibility at runtime

**Key Components:**

```python
# borglife_prototype/archon_adapter/
├── __init__.py
├── adapter.py           # Main ArchonServiceAdapter class
├── config.py            # Configuration and environment handling
├── exceptions.py        # Custom exceptions for integration
├── health.py            # Health checks and service discovery
├── mcp_client.py        # MCP protocol client wrapper
├── rest_client.py       # HTTP REST API client wrapper
└── version.py           # Version compatibility checks
```

---

## 3. Dependency Management Strategy

### 3.1 Recommended Approach: **Docker Compose Service Integration**

**Rationale:**
- ✅ **Loose Coupling**: Services communicate via HTTP, no code dependencies
- ✅ **Independent Versioning**: Each service can update independently
- ✅ **Easy Updates**: `docker compose pull && docker compose up -d`
- ✅ **Production-Ready**: Same pattern for dev and deployment
- ✅ **Service Discovery**: Docker DNS handles host resolution

**Implementation:**

```yaml
# borglife_prototype/docker-compose.yml (UPDATED)
version: '3.8'

services:
  # Existing borglife services
  borglife-mcp:
    build: .
    ports:
      - "8051:8051"
    environment:
      - ARCHON_SERVER_URL=http://archon-server:8181
      - ARCHON_MCP_URL=http://archon-mcp:8051
    depends_on:
      - archon-server
    networks:
      - borglife-network
      - archon-network

  borglife-ui:
    build: .
    ports:
      - "8501:8501"
    depends_on:
      - borglife-mcp
      - archon-server
    networks:
      - borglife-network
      - archon-network

  # Archon services (external reference)
  archon-server:
    image: archon-server:latest  # Or build from ../archon
    ports:
      - "8181:8181"
    env_file:
      - .env
    networks:
      - archon-network

  archon-mcp:
    image: archon-mcp:latest
    ports:
      - "8051:8051"
    env_file:
      - .env
    depends_on:
      - archon-server
    networks:
      - archon-network

networks:
  borglife-network:
    driver: bridge
  archon-network:
    driver: bridge
```

### 3.2 Alternative Approaches (Evaluated but Not Recommended)

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Git Submodules** | Version pinning, local source | Merge conflicts, manual updates | ❌ Too brittle |
| **Symbolic Links** | Simple, shared code | Breaks on different machines | ❌ Not portable |
| **Python Package (editable)** | pip install -e ../archon | Tight coupling to internals | ❌ Violates abstraction |
| **Vendoring** | Full control | Massive duplication, stale code | ❌ Maintenance nightmare |

---

## 4. Environment Configuration

### 4.1 Comprehensive .env.example Template

```bash
# ============================================================================
# BORGLIFE PROTOTYPE - ENVIRONMENT CONFIGURATION
# ============================================================================
# This file contains ALL required environment variables for borglife_prototype
# integration with Archon services and Supabase.
#
# SETUP INSTRUCTIONS:
# 1. Copy this file: cp .env.example .env
# 2. Fill in your Supabase credentials (REQUIRED)
# 3. Adjust service URLs if running archon on different host/ports
# 4. Configure optional features as needed
# ============================================================================

# ----------------------------------------------------------------------------
# SUPABASE CONFIGURATION (REQUIRED)
# ----------------------------------------------------------------------------
# Get these from: https://supabase.com/dashboard/project/<project-id>/settings/api
#
# CRITICAL: Use the SERVICE ROLE key, NOT the anon key!
# The service_role key is longer and contains "service_role" in the JWT payload.
# Using the wrong key will cause "permission denied" errors on all database operations.

# Your Supabase project URL (e.g., https://xxxxx.supabase.co)
SUPABASE_URL=

# Your Supabase SERVICE ROLE key (the longer one, ~200+ characters)
# ⚠️  NEVER commit this to version control! Keep it secret.
SUPABASE_SERVICE_KEY=

# Optional: Supabase anon key (for read-only public access, if needed)
# SUPABASE_ANON_KEY=

# ----------------------------------------------------------------------------
# ARCHON SERVICE DISCOVERY (REQUIRED)
# ----------------------------------------------------------------------------
# URLs for archon microservices. Defaults assume Docker Compose networking.
# If running archon separately, update these to match your deployment.

# Archon main server (FastAPI + business logic)
ARCHON_SERVER_URL=http://archon-server:8181

# Archon MCP server (Model Context Protocol interface)
ARCHON_MCP_URL=http://archon-mcp:8051

# Archon agents service (PydanticAI agents, optional)
ARCHON_AGENTS_URL=http://archon-agents:8052

# Enable/disable archon agents integration
ARCHON_AGENTS_ENABLED=false

# ----------------------------------------------------------------------------
# BORGLIFE SERVICE PORTS
# ----------------------------------------------------------------------------
# Ports for borglife services (external access)

# Borglife MCP server port
BORGLIFE_MCP_PORT=8053

# Borglife Sponsor UI port (Streamlit)
BORGLIFE_UI_PORT=8501

# Borglife agent port (proto-borg)
BORGLIFE_AGENT_PORT=8054

# ----------------------------------------------------------------------------
# BLOCKCHAIN CONFIGURATION
# ----------------------------------------------------------------------------
# Kusama testnet and JAM integration settings

# Kusama RPC endpoint (testnet)
KUSAMA_RPC_URL=wss://kusama-rpc.polkadot.io

# Wallet seed phrase or private key (for borg wallet operations)
# ⚠️  NEVER commit this to version control! Use testnet funds only.
BORG_WALLET_SEED=

# JAM mock mode (true = local simulation, false = real JAM when available)
JAM_MOCK_MODE=true

# ----------------------------------------------------------------------------
# AI/ML CONFIGURATION
# ----------------------------------------------------------------------------
# API keys for LLM providers (used by proto-borg and archon organs)

# OpenAI API key (for GPT models)
OPENAI_API_KEY=

# Optional: Google Gemini API key
# GEMINI_API_KEY=

# Optional: Ollama endpoint (for local models)
# OLLAMA_URL=http://localhost:11434

# Default model for borg inference
DEFAULT_LLM_MODEL=gpt-4

# Embedding model for RAG (must match archon's configuration)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# ----------------------------------------------------------------------------
# LOGGING & OBSERVABILITY
# ----------------------------------------------------------------------------

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Optional: Logfire token for observability (same as archon)
LOGFIRE_TOKEN=

# Enable structured JSON logging
JSON_LOGGING=true

# ----------------------------------------------------------------------------
# DEVELOPMENT & TESTING
# ----------------------------------------------------------------------------

# Environment mode (development, staging, production)
ENVIRONMENT=development

# Enable debug mode (verbose logging, no auth checks)
DEBUG=false

# Enable test mode (use mock data, skip external calls)
TEST_MODE=false

# ----------------------------------------------------------------------------
# ARCHON INTEGRATION FEATURES
# ----------------------------------------------------------------------------
# Control which archon features borglife uses

# Enable RAG (Retrieval-Augmented Generation) via archon
ENABLE_ARCHON_RAG=true

# Enable task management via archon projects
ENABLE_ARCHON_TASKS=true

# Enable document crawling via archon
ENABLE_ARCHON_CRAWLING=true

# Enable code example extraction
ENABLE_CODE_EXAMPLES=true

# ----------------------------------------------------------------------------
# ADVANCED CONFIGURATION
# ----------------------------------------------------------------------------

# Service discovery mode (docker_compose, kubernetes, manual)
SERVICE_DISCOVERY_MODE=docker_compose

# Health check interval (seconds)
HEALTH_CHECK_INTERVAL=30

# Request timeout for archon services (seconds)
ARCHON_REQUEST_TIMEOUT=30

# Retry attempts for failed archon requests
ARCHON_RETRY_ATTEMPTS=3

# Circuit breaker threshold (failures before opening circuit)
CIRCUIT_BREAKER_THRESHOLD=5

# ----------------------------------------------------------------------------
# OPTIONAL: DATABASE CONNECTION STRINGS
# ----------------------------------------------------------------------------
# If you need direct PostgreSQL access (bypassing Supabase client)

# PostgreSQL connection string (derived from SUPABASE_URL if not set)
# DATABASE_URL=postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres

# ----------------------------------------------------------------------------
# NOTES
# ----------------------------------------------------------------------------
# - All URLs should include protocol (http:// or https://)
# - Docker Compose services use service names as hostnames
# - For local development outside Docker, use localhost:PORT
# - Keep secrets (.env file) out of version control (.gitignore)
# - Refer to README.md for detailed setup instructions
```

### 4.2 Configuration Management Class

```python
# borglife_prototype/archon_adapter/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class ArchonConfig(BaseSettings):
    """Configuration for Archon integration with validation."""
    
    # Supabase (required)
    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: Optional[str] = None
    
    # Archon services
    archon_server_url: str = "http://archon-server:8181"
    archon_mcp_url: str = "http://archon-mcp:8051"
    archon_agents_url: str = "http://archon-agents:8052"
    archon_agents_enabled: bool = False
    
    # Integration features
    enable_archon_rag: bool = True
    enable_archon_tasks: bool = True
    enable_archon_crawling: bool = True
    
    # Resilience
    archon_request_timeout: int = 30
    archon_retry_attempts: int = 3
    circuit_breaker_threshold: int = 5
    health_check_interval: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

---

## 5. Adapter Implementation Design

### 5.1 Core Adapter Interface

```python
# borglife_prototype/archon_adapter/adapter.py
from typing import Dict, Any, List, Optional
import httpx
from .config import ArchonConfig
from .exceptions import ArchonUnavailableError, ArchonVersionMismatchError
from .health import HealthChecker
from .mcp_client import MCPClient
from .rest_client import RESTClient

class ArchonServiceAdapter:
    """
    Facade for borglife-archon integration.
    
    Provides stable interface that isolates borglife from archon's internal changes.
    Implements circuit breaker, retry logic, and version compatibility checks.
    """
    
    def __init__(self, config: Optional[ArchonConfig] = None):
        self.config = config or ArchonConfig()
        self.health_checker = HealthChecker(self.config)
        self.mcp_client = MCPClient(self.config)
        self.rest_client = RESTClient(self.config)
        self._circuit_open = False
        self._failure_count = 0
    
    async def initialize(self) -> bool:
        """
        Initialize connection to archon services.
        
        Returns:
            True if all required services are healthy
        
        Raises:
            ArchonUnavailableError: If critical services are down
            ArchonVersionMismatchError: If version incompatible
        """
        # Check service health
        health = await self.health_checker.check_all()
        if not health['archon_server']:
            raise ArchonUnavailableError("Archon server is unavailable")
        
        # Verify version compatibility
        version = await self.rest_client.get_version()
        if not self._is_compatible_version(version):
            raise ArchonVersionMismatchError(
                f"Archon version {version} incompatible with adapter"
            )
        
        return True
    
    # ========================================================================
    # MCP ORGAN OPERATIONS
    # ========================================================================
    
    async def perform_rag_query(
        self, 
        query: str, 
        context: Optional[str] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Perform RAG query via archon's MCP interface.
        
        Args:
            query: Search query
            context: Optional context for query
            max_results: Maximum results to return
        
        Returns:
            Dict with 'results' (list of documents) and 'metadata'
        """
        if not self.config.enable_archon_rag:
            return {'results': [], 'metadata': {'disabled': True}}
        
        return await self.mcp_client.call_tool(
            'archon:perform_rag_query',
            {
                'query': query,
                'context': context,
                'max_results': max_results
            }
        )
    
    async def search_code_examples(
        self,
        query: str,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for code examples in archon's knowledge base."""
        if not self.config.enable_code_examples:
            return []
        
        result = await self.mcp_client.call_tool(
            'archon:search_code_examples',
            {'query': query, 'language': language}
        )
        return result.get('examples', [])
    
    # ========================================================================
    # TASK MANAGEMENT OPERATIONS
    # ========================================================================
    
    async def create_task(
        self,
        title: str,
        description: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create task in archon's project management."""
        if not self.config.enable_archon_tasks:
            return {'id': 'mock', 'status': 'disabled'}
        
        return await self.mcp_client.call_tool(
            'archon:create_task',
            {
                'title': title,
                'description': description,
                'project_id': project_id
            }
        )
    
    async def list_tasks(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List tasks from archon."""
        if not self.config.enable_archon_tasks:
            return []
        
        result = await self.mcp_client.call_tool(
            'archon:list_tasks',
            {'project_id': project_id, 'status': status}
        )
        return result.get('tasks', [])
    
    # ========================================================================
    # KNOWLEDGE MANAGEMENT OPERATIONS
    # ========================================================================
    
    async def crawl_website(
        self,
        url: str,
        max_pages: int = 50
    ) -> Dict[str, Any]:
        """Crawl website via archon's crawler."""
        if not self.config.enable_archon_crawling:
            return {'status': 'disabled'}
        
        return await self.rest_client.post(
            '/api/sources/crawl',
            {'url': url, 'max_pages': max_pages}
        )
    
    async def upload_document(
        self,
        content: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload document to archon's knowledge base."""
        return await self.rest_client.post_multipart(
            '/api/documents/upload',
            files={'file': (filename, content)},
            data={'metadata': metadata}
        )
    
    # ========================================================================
    # HEALTH & MONITORING
    # ========================================================================
    
    async def check_health(self) -> Dict[str, bool]:
        """Check health of all archon services."""
        return await self.health_checker.check_all()
    
    def _is_compatible_version(self, version: str) -> bool:
        """Check if archon version is compatible."""
        # Implement semantic versioning check
        # For now, accept any version (to be refined)
        return True
```

### 5.2 Circuit Breaker & Retry Logic

```python
# borglife_prototype/archon_adapter/rest_client.py
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class RESTClient:
    """HTTP client with retry logic and circuit breaker."""
    
    def __init__(self, config: ArchonConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.archon_server_url,
            timeout=config.archon_request_timeout
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """GET request with retry logic."""
        response = await self.client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """POST request with retry logic."""
        response = await self.client.post(path, **kwargs)
        response.raise_for_status()
        return response.json()
```

---

## 6. Version Pinning Strategy

### 6.1 Recommended Approach: **Semantic Versioning with Feature Flags**

**Strategy:**
1. **Track archon version** via health endpoint or git tags
2. **Feature flags** for gradual migration when APIs change
3. **Compatibility matrix** documented in README
4. **Automated tests** against multiple archon versions

**Implementation:**

```python
# borglife_prototype/archon_adapter/version.py
from packaging import version
from typing import Dict, List

class VersionCompatibility:
    """Manage version compatibility between borglife and archon."""
    
    # Minimum supported archon version
    MIN_VERSION = "0.1.0"
    
    # Maximum tested archon version
    MAX_VERSION = "0.2.0"
    
    # Feature compatibility matrix
    FEATURES: Dict[str, List[str]] = {
        'rag_query': ['0.1.0', '0.2.0'],  # Supported in these versions
        'task_management': ['0.1.5', '0.2.0'],
        'code_examples': ['0.1.8', '0.2.0'],
    }
    
    @classmethod
    def is_compatible(cls, archon_version: str) -> bool:
        """Check if archon version is compatible."""
        v = version.parse(archon_version)
        min_v = version.parse(cls.MIN_VERSION)
        max_v = version.parse(cls.MAX_VERSION)
        return min_v <= v <= max_v
    
    @classmethod
    def supports_feature(cls, feature: str, archon_version: str) -> bool:
        """Check if specific feature is supported in version."""
        if feature not in cls.FEATURES:
            return False
        
        v = version.parse(archon_version)
        supported_versions = [version.parse(sv) for sv in cls.FEATURES[feature]]
        return any(v >= sv for sv in supported_versions)
```

### 6.2 Update Procedure

```bash
# borglife_prototype/scripts/update_archon.sh
#!/bin/bash
set -e

echo "Updating Archon services..."

# 1. Pull latest archon images
cd ../archon
git pull origin stable
docker compose build

# 2. Run compatibility tests
cd ../borglife_prototype
python -m pytest tests/integration/test_archon_compatibility.py

# 3. Update if tests pass
if [ $? -eq 0 ]; then
    echo "✅ Compatibility tests passed"
    cd ../archon
    docker compose up -d
    echo "✅ Archon services updated"
else
    echo "❌ Compatibility tests failed - review changes before updating"
    exit 1
fi
```

---

## 7. Implementation Steps

### 7.1 Phase 1: Foundation (Week 1)

1. **Create `.env.example`** with complete Supabase and archon variables
2. **Set up archon dependency** via Docker Compose service references
3. **Implement `ArchonServiceAdapter`** base class with health checks
4. **Add configuration management** with Pydantic validation

**Deliverables:**
- `.env.example` file
- `archon_adapter/` module structure
- Basic health check integration
- Documentation in README.md

### 7.2 Phase 2: Core Integration (Week 2)

1. **Implement MCP client wrapper** for organ operations
2. **Implement REST client wrapper** for knowledge management
3. **Add retry logic and circuit breaker** for resilience
4. **Create integration tests** against live archon instance

**Deliverables:**
- Full adapter implementation
- Integration test suite
- Error handling and logging

### 7.3 Phase 3: Production Readiness (Week 3)

1. **Version compatibility checks** and feature flags
2. **Automated update procedure** with compatibility tests
3. **Monitoring and observability** integration
4. **Documentation and examples** for developers

**Deliverables:**
- Version management system
- Update scripts and CI/CD integration
- Comprehensive documentation

---

## 8. Testing Strategy

### 8.1 Compatibility Test Suite

```python
# tests/integration/test_archon_compatibility.py
import pytest
from archon_adapter import ArchonServiceAdapter

@pytest.mark.asyncio
async def test_archon_health():
    """Verify archon services are reachable."""
    adapter = ArchonServiceAdapter()
    health = await adapter.check_health()
    assert health['archon_server'] is True

@pytest.mark.asyncio
async def test_rag_query_compatibility():
    """Test RAG query across archon versions."""
    adapter = ArchonServiceAdapter()
    result = await adapter.perform_rag_query("test query")
    assert 'results' in result
    assert isinstance(result['results'], list)

@pytest.mark.asyncio
async def test_graceful_degradation():
    """Verify adapter handles archon unavailability."""
    adapter = ArchonServiceAdapter()
    # Simulate archon down
    adapter.config.archon_server_url = "http://invalid:9999"
    
    with pytest.raises(ArchonUnavailableError):
        await adapter.initialize()
```

### 8.2 Version Matrix Testing

```yaml
# .github/workflows/archon-compatibility.yml
name: Archon Compatibility Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        archon-version: ['0.1.0', '0.1.5', '0.2.0']
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Start Archon ${{ matrix.archon-version }}
        run: |
          cd ../archon
          git checkout v${{ matrix.archon-version }}
          docker compose up -d
      
      - name: Run Compatibility Tests
        run: |
          pytest tests/integration/test_archon_compatibility.py
```

---

## 9. Documentation Requirements

### 9.1 README.md Updates

```markdown
## Archon Integration

Borglife integrates with [Archon](https://github.com/coleam00/archon) for knowledge management and MCP organs.

### Setup

1. **Install Archon** (in parallel directory):
   ```bash
   cd ..
   git clone -b stable https://github.com/coleam00/archon.git
   cd archon
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

2. **Configure Borglife**:
   ```bash
   cd ../borglife_prototype
   cp .env.example .env
   # Use same Supabase credentials as archon
   ```

3. **Start Services**:
   ```bash
   docker compose up -d
   ```

### Supported Archon Versions

- **Minimum**: 0.1.0
- **Recommended**: 0.2.0 (stable branch)
- **Maximum Tested**: 0.2.0

### Updating Archon

```bash
./scripts/update_archon.sh
```

This script:
1. Pulls latest archon changes
2. Runs compatibility tests
3. Updates services if tests pass

### Troubleshooting

**Issue**: "Archon services unavailable"
- **Solution**: Verify archon is running: `cd ../archon && docker compose ps`

**Issue**: "Version mismatch error"
- **Solution**: Update archon to supported version or disable incompatible features

**Issue**: "Supabase permission denied"
- **Solution**: Ensure using SERVICE ROLE key, not anon key
```

---

## 10. Risk Mitigation

### 10.1 Identified Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Archon API breaking changes | High | Medium | Version pinning, compatibility tests, feature flags |
| Archon service unavailable | Medium | Low | Circuit breaker, graceful degradation, local fallbacks |
| Supabase schema changes | High | Low | Adapter isolates schema access, migration scripts |
| Performance degradation | Medium | Medium | Caching, async operations, monitoring |
| Security vulnerabilities | High | Low | Regular updates, security audits, secret management |

### 10.2 Rollback Strategy

```bash
# If archon update breaks compatibility
cd ../archon
git checkout v0.1.5  # Last known good version
docker compose up -d --build

cd ../borglife_prototype
# Revert .env changes if needed
docker compose restart
```

---

## 11. Success Criteria

### 11.1 Integration Quality Metrics

- ✅ **Loose Coupling**: Borglife has zero direct imports from archon codebase
- ✅ **Resilience**: System degrades gracefully when archon unavailable
- ✅ **Compatibility**: Supports archon versions 0.1.0 - 0.2.0
- ✅ **Performance**: <100ms overhead for adapter layer
- ✅ **Maintainability**: Update archon without borglife code changes
- ✅ **Testability**: 90%+ test coverage for adapter module

### 11.2 Developer Experience

- ✅ **Setup Time**: <10 minutes from clone to running system
- ✅ **Documentation**: Complete setup guide with troubleshooting
- ✅ **Error Messages**: Clear, actionable error messages
- ✅ **Update Process**: One-command archon updates with safety checks

---

## 12. Next Steps

1. **Review this plan** with stakeholders and iterate
2. **Create `.env.example`** file with all variables
3. **Implement Phase 1** (foundation) over 1 week
4. **Test integration** with live archon instance
5. **Document** setup procedure and troubleshooting
6. **Iterate** based on feedback and real-world usage

---

## Appendix A: File Structure

```
borglife_prototype/
├── .env.example                    # ← NEW: Complete environment template
├── .gitignore                      # ← UPDATE: Add .env
├── docker-compose.yml              # ← UPDATE: Add archon services
├── README.md                       # ← UPDATE: Add archon integration docs
├── archon_adapter/                 # ← NEW: Adapter module
│   ├── __init__.py
│   ├── adapter.py                  # Main ArchonServiceAdapter
│   ├── config.py                   # Configuration management
│   ├── exceptions.py               # Custom exceptions
│   ├── health.py                   # Health checks
│   ├── mcp_client.py               # MCP protocol wrapper
│   ├── rest_client.py              # HTTP REST wrapper
│   └── version.py                  # Version compatibility
├── archon_integration.py           # ← UPDATE: Use adapter instead of direct calls
├── proto_borg.py                   # ← UPDATE: Integrate archon organs
├── sponsor_ui.py                   # ← UPDATE: Display archon data
├── scripts/
│   └── update_archon.sh            # ← NEW: Archon update script
└── tests/
    └── integration/
        └── test_archon_compatibility.py  # ← NEW: Compatibility tests
```

---

## Appendix B: Key Design Decisions

1. **Why Docker Compose over Git Submodules?**
   - Services communicate via HTTP, not code imports
   - Independent versioning and deployment
   - Production-ready pattern

2. **Why Adapter Pattern over Direct Integration?**
   - Isolates borglife from archon's internal changes
   - Enables graceful degradation
   - Simplifies testing and mocking

3. **Why Semantic Versioning with Feature Flags?**
   - Balances stability (pinned versions) and currency (gradual updates)
   - Allows testing against multiple versions
   - Enables incremental migration

4. **Why Shared Supabase over Separate Databases?**
   - Reduces infrastructure complexity
   - Enables data sharing (knowledge base, tasks)
   - Aligns with archon's architecture

---

**This plan is ready for review and iteration. Please provide feedback on:**
1. Dependency management approach (Docker Compose vs alternatives)
2. Adapter interface design (missing operations?)
3. Version pinning strategy (too strict/loose?)
4. Implementation timeline (realistic?)
5. Any concerns about archon's evolution affecting this design