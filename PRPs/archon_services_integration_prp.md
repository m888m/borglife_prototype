name: "BorgLife-Archon Services Integration PRP"
description: |

---

## Goal

**Feature Goal**: Implement complete real integration between BorgLife components and Archon services, replacing all mock implementations with actual service calls and circuit breaker protection.

**Deliverable**: Fully integrated BorgLife system that communicates with real Archon services (server, MCP, agents) through proper async patterns, error handling, and circuit breaker protection.

**Success Definition**: All BorgLife operations (DNA parsing, phenotype building, task execution, wealth tracking) work with real Archon services, with proper error recovery and performance within requirements.

## User Persona (if applicable)

**Target User**: BorgLife Phase 1 developers and demo operators

**Use Case**: Running BorgLife demos with real Archon infrastructure instead of mocks

**User Journey**:
1. Start Archon services (server, MCP, agents)
2. Initialize BorgLife with real service connections
3. Execute borg tasks through actual MCP tools
4. Monitor real wealth tracking and cost calculations
5. Handle service failures gracefully with circuit breakers

**Pain Points Addressed**: Mock implementations prevent real testing, service failures cause demo failures, lack of proper error recovery

## Why

- **Business value**: Enables reliable Phase 1 demos with real Archon integration
- **Integration with existing features**: Builds on existing archon_adapter and service infrastructure
- **Problems this solves**: Mock fallbacks prevent real validation, service integration issues cause failures

## What

Complete Archon services integration implementation:

### Real Service Connections
- Archon server integration for data operations
- MCP tool execution through real endpoints
- Agent services for cell execution
- Supabase integration for persistence

### Circuit Breaker Protection
- Service health monitoring and automatic failover
- Configurable timeout and retry logic
- Graceful degradation when services unavailable
- Recovery mechanisms for service restoration

### Error Handling & Recovery
- Comprehensive error propagation from services
- Async context management for resource cleanup
- Service unavailability handling with fallbacks
- Network failure recovery patterns

### Performance Optimization
- Connection pooling and reuse
- Async batch operations where possible
- Resource usage monitoring
- 5-minute execution limit compliance

## All Needed Context

### Context Completeness Check

_Before writing this PRP, validate: "If someone knew nothing about this codebase, would they have everything needed to implement this successfully?"_

### Documentation & References

```yaml
- file: code/archon_adapter/adapter.py
  why: Current adapter implementation with mock fallbacks
  pattern: Service initialization, health checking, MCP tool calls
  gotcha: Circuit breaker integration needed, async patterns required

- file: code/archon_adapter/config.py
  why: Service configuration and endpoint management
  pattern: Environment variable handling, URL construction
  gotcha: Docker vs local environment configuration differences

- file: code/tests/test_service_integration.py
  why: Integration test patterns and expected behaviors
  pattern: Health checks, MCP tool availability, error scenarios
  gotcha: Tests currently use mocks, need real service validation

- file: code/proto_borg.py
  why: Borg lifecycle and service integration points
  pattern: Async initialization, task execution flow, wealth tracking
  gotcha: Currently uses mock adapter, needs real integration

- url: https://github.com/coleam00/archon/blob/stable/docker-compose.yml
  why: Archon service orchestration and configuration
  critical: Service dependencies, port mappings, health check endpoints

- docfile: borglife-archon-strategy.md
  why: Integration architecture and Phase 1 requirements
  section: Part 4 - Integration Architecture, Part 5 - Service Dependencies
```

### Current Codebase tree

```bash
code/archon_adapter/
├── __init__.py                 # Adapter module exports
├── adapter.py                  # Main adapter (currently mocked)
├── cache_manager.py           # Response caching
├── compatibility_matrix.py    # Version compatibility
├── config.py                  # Configuration management
├── dependency_monitor.py      # Service dependency tracking
├── docker_discovery.py        # Docker service discovery
├── docker_mcp_auth.py         # MCP authentication
├── docker_mcp_billing.py      # MCP billing integration
├── docker_monitor.py          # Docker service monitoring
├── exceptions.py              # Adapter-specific exceptions
├── fallback_manager.py        # Fallback handling
├── health.py                  # Health check utilities
├── mcp_client.py              # MCP protocol client
├── rate_limiter.py            # Rate limiting
└── version.py                 # Version management
```

### Desired Codebase tree with files to be added and responsibility of file

```bash
code/archon_adapter/
├── __init__.py                 # Export real adapter implementation
├── adapter.py                  # COMPLETE: Real Archon service integration
├── cache_manager.py           # COMPLETE: Response caching with TTL
├── compatibility_matrix.py    # COMPLETE: Version compatibility checking
├── config.py                  # COMPLETE: Environment-based configuration
├── dependency_monitor.py      # COMPLETE: Service health and dependency tracking
├── docker_discovery.py        # COMPLETE: Docker service auto-discovery
├── docker_mcp_auth.py         # COMPLETE: Real MCP authentication flow
├── docker_mcp_billing.py      # COMPLETE: Real billing integration
├── docker_monitor.py          # COMPLETE: Docker service monitoring
├── exceptions.py              # COMPLETE: Comprehensive exception hierarchy
├── fallback_manager.py        # COMPLETE: Circuit breaker and fallback logic
├── health.py                  # COMPLETE: Multi-service health checking
├── mcp_client.py              # COMPLETE: Real MCP protocol implementation
├── rate_limiter.py            # COMPLETE: Request rate limiting
├── version.py                 # COMPLETE: Version negotiation and compatibility
├── circuit_breaker.py         # NEW: Circuit breaker implementation
└── connection_pool.py         # NEW: Connection pooling for performance
```

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: All service calls must go through circuit breaker protection
# Never make direct HTTP calls - always use circuit_breaker.call()

# CRITICAL: Async initialization required for all adapter components
# All services need async initialize() calls before use

# CRITICAL: Connection pooling essential for performance
# Reuse connections to avoid overhead in rapid service calls

# CRITICAL: Circuit breaker state affects error handling
# OPEN state means fast-fail, CLOSED means normal operation

# CRITICAL: Service health checks need stabilization time
# Add asyncio.sleep(2) after service startup before health checks

# CRITICAL: Docker MCP organs may not be available in test environment
# Graceful fallback to mock implementations when services unavailable

# CRITICAL: Rate limiting applies to all MCP tool calls
# Respect rate limits to avoid service throttling
```

## Implementation Blueprint

### Data models and structure

```python
# Core integration data structures

@dataclass
class ServiceConfig:
    """Configuration for Archon service connections."""
    server_url: str
    mcp_url: str
    agents_url: str
    supabase_url: str
    supabase_key: str
    timeout: int = 30
    retry_attempts: int = 3
    circuit_breaker_threshold: int = 5

@dataclass
class ServiceHealth:
    """Health status for all Archon services."""
    archon_server: bool
    archon_mcp: bool
    archon_agents: bool
    supabase: bool
    overall: bool
    last_check: datetime
    response_times: Dict[str, float]

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerStatus:
    """Circuit breaker status information."""
    state: CircuitBreakerState
    failure_count: int
    last_failure_time: Optional[datetime]
    next_retry_time: Optional[datetime]

class ArchonServiceError(Exception):
    """Base exception for Archon service errors."""
    pass

class ServiceUnavailableError(ArchonServiceError):
    """Service is not available."""
    pass

class CircuitBreakerOpenError(ArchonServiceError):
    """Circuit breaker is open."""
    pass
```

### Implementation Tasks (Complete - 15 Tasks with Proper Dependencies)

**Infrastructure Already Available:**
- ✅ HTTP client libraries (aiohttp/httpx)
- ✅ Asyncio for concurrent operations
- ✅ Docker Compose for service orchestration
- ✅ Environment variable configuration
- ✅ Logging infrastructure

```yaml
Task 1: Service Configuration Management
  - IMPLEMENT: config.py with environment-based service URLs and timeouts
  - INCLUDE: Docker vs local environment detection, validation logic
  - VALIDATE: All required environment variables present
  - DEPENDS: None (foundational configuration)

Task 2: Circuit Breaker Implementation
  - IMPLEMENT: circuit_breaker.py with state management and recovery logic
  - INCLUDE: CLOSED/OPEN/HALF_OPEN states, failure thresholds, retry timing
  - TEST: State transitions and recovery mechanisms
  - DEPENDS: Task 1 (needs configuration for thresholds)

Task 3: Connection Pool Implementation
  - IMPLEMENT: connection_pool.py for HTTP connection reuse
  - INCLUDE: Pool management, cleanup, performance monitoring
  - OPTIMIZE: Reduce connection overhead for rapid service calls
  - DEPENDS: Task 1 (needs service URLs for pool configuration)

Task 4: Real MCP Client Implementation
  - IMPLEMENT: mcp_client.py with actual MCP protocol communication
  - INCLUDE: Tool discovery, execution, error handling
  - INTEGRATE: With circuit breaker protection for all calls
  - DEPENDS: Tasks 2-3 (needs circuit breaker and connection pool)

Task 5: Health Check System Overhaul
  - UPDATE: health.py with real service health checking
  - INCLUDE: Parallel health checks, response time monitoring
  - VALIDATE: Service availability and responsiveness
  - DEPENDS: Task 3 (needs connection pool for efficient checks)

Task 6: Archon Adapter Core Integration
  - UPDATE: adapter.py to use real services instead of mocks
  - REMOVE: All mock fallbacks and conditional imports
  - INTEGRATE: Circuit breaker, connection pool, real MCP client
  - DEPENDS: Tasks 4-5 (needs MCP client and health checks)

Task 7: Docker Service Discovery
  - IMPLEMENT: docker_discovery.py for automatic service detection
  - INCLUDE: Docker API integration, service endpoint resolution
  - SUPPORT: Dynamic service discovery in container environments
  - DEPENDS: Task 1 (needs base configuration)

Task 8: Authentication & Security
  - IMPLEMENT: docker_mcp_auth.py with real authentication flows
  - INCLUDE: Token management, session handling, security validation
  - INTEGRATE: With MCP client for authenticated requests
  - DEPENDS: Task 4 (needs MCP client foundation)

Task 9: Billing Integration
  - IMPLEMENT: docker_mcp_billing.py with real billing operations
  - INCLUDE: Cost tracking, payment processing, transaction logging
  - VALIDATE: Economic model compliance with decimal precision
  - DEPENDS: Task 6 (needs integrated adapter)

Task 10: Rate Limiting Implementation
  - IMPLEMENT: rate_limiter.py with configurable limits and backoff
  - INCLUDE: Per-service limits, exponential backoff, queue management
  - PREVENT: Service throttling and resource exhaustion
  - DEPENDS: Task 3 (needs connection pool for request tracking)

Task 11: Fallback Manager Enhancement
  - UPDATE: fallback_manager.py with real fallback logic
  - INCLUDE: Service degradation handling, mock fallbacks for testing
  - SUPPORT: Graceful degradation when primary services fail
  - DEPENDS: Tasks 6-10 (needs all service integrations)

Task 12: Proto-Borg Real Integration
  - UPDATE: proto_borg.py to use real archon_adapter
  - REMOVE: Mock fallbacks and conditional imports
  - VALIDATE: Borg initialization and task execution with real services
  - DEPENDS: Task 11 (needs complete adapter implementation)

Task 13: Test Suite Real Service Updates
  - UPDATE: All test files to use real services instead of mocks
  - ENABLE: test_service_integration.py, test_error_handling.py with real calls
  - VALIDATE: Tests pass against actual Archon infrastructure
  - DEPENDS: Task 12 (needs real proto_borg integration)

Task 14: Performance Optimization & Monitoring
  - IMPLEMENT: Performance monitoring across all service calls
  - OPTIMIZE: Connection reuse, async batching, resource cleanup
  - VALIDATE: 5-minute E2E execution limit compliance
  - DEPENDS: Tasks 1-13 (needs complete implementation)

Task 15: Production Readiness & Documentation
  - DOCUMENT: Service integration patterns and troubleshooting
  - CREATE: Runbooks for service failure scenarios
  - VALIDATE: Production deployment and monitoring readiness
  - DEPENDS: Tasks 1-14 (needs complete system for documentation)
```

### Implementation Patterns & Key Details

```python
# Circuit Breaker implementation pattern
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

# Real MCP Client implementation pattern
class MCPClient:
    def __init__(self, base_url: str, circuit_breaker: CircuitBreaker):
        self.base_url = base_url
        self.circuit_breaker = circuit_breaker
        self.session = None

    async def initialize(self):
        """Initialize MCP client connection."""
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=10),  # Connection pool
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools."""
        async def _list_tools():
            async with self.session.get(f"{self.base_url}/tools") as response:
                response.raise_for_status()
                return await response.json()

        return await self.circuit_breaker.call(_list_tools)

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool with circuit breaker protection."""
        async def _call_tool():
            payload = {
                "tool": tool_name,
                "parameters": parameters
            }
            async with self.session.post(
                f"{self.base_url}/call",
                json=payload
            ) as response:
                response.raise_for_status()
                return await response.json()

        return await self.circuit_breaker.call(_call_tool)

# Archon Adapter integration pattern
class ArchonServiceAdapter:
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold
        )
        self.mcp_client = MCPClient(config.mcp_url, self.circuit_breaker)
        self.connection_pool = ConnectionPool(config)

    async def initialize(self) -> bool:
        """Initialize all service connections."""
        try:
            # Initialize MCP client
            await self.mcp_client.initialize()

            # Initialize connection pool
            await self.connection_pool.initialize()

            # Verify service health
            health = await self.check_health()
            return health.overall

        except Exception as e:
            logger.error(f"Adapter initialization failed: {e}")
            return False

    async def check_health(self) -> ServiceHealth:
        """Check health of all Archon services."""
        # Parallel health checks for performance
        tasks = [
            self._check_service_health("archon_server", self.config.server_url),
            self._check_service_health("archon_mcp", self.config.mcp_url),
            self._check_service_health("archon_agents", self.config.agents_url),
            self._check_supabase_health()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        health_status = {}
        response_times = {}
        all_healthy = True

        for i, result in enumerate(results):
            service_name = ["archon_server", "archon_mcp", "archon_agents", "supabase"][i]
            if isinstance(result, Exception):
                health_status[service_name] = False
                response_times[service_name] = 0.0
                all_healthy = False
            else:
                healthy, response_time = result
                health_status[service_name] = healthy
                response_times[service_name] = response_time
                if not healthy:
                    all_healthy = False

        return ServiceHealth(
            archon_server=health_status["archon_server"],
            archon_mcp=health_status["archon_mcp"],
            archon_agents=health_status["archon_agents"],
            supabase=health_status["supabase"],
            overall=all_healthy,
            last_check=datetime.utcnow(),
            response_times=response_times
        )
```

### Integration Points (Leveraging Existing Infrastructure)

```yaml
SERVICES (Real Integration Required):
  - archon-server:8181 - REST API for data operations and orchestration
  - archon-mcp:8051 - MCP protocol for AI assistant tools and RAG queries
  - archon-agents:8052 - PydanticAI for cell execution and task processing
  - supabase - PostgreSQL database for all data persistence and state management

PROTOCOLS (To Be Implemented):
  - Circuit Breaker Protocol - Service protection and automatic recovery
  - Connection Pool Protocol - HTTP connection reuse and performance
  - Health Check Protocol - Multi-service availability monitoring
  - Rate Limiting Protocol - Request throttling and backoff strategies
```

## Validation Loop (Complete - 15 Tasks)

### Level 1: Component Implementation (Tasks 1-5 Complete)

```bash
cd borglife_proto_private/code
# Test individual component imports
python -c "from archon_adapter.circuit_breaker import CircuitBreaker; print('✅ Circuit Breaker OK')"
python -c "from archon_adapter.connection_pool import ConnectionPool; print('✅ Connection Pool OK')"
python -c "from archon_adapter.mcp_client import MCPClient; print('✅ MCP Client OK')"
```

### Level 2: Service Integration (Tasks 6-10 Complete)

```bash
cd borglife_proto_private/code
# Test adapter integration
python -c "from archon_adapter import ArchonServiceAdapter; print('✅ Adapter Integration OK')"
python -c "import archon_adapter; print('✅ Module Integration OK')"
```

### Level 3: Proto-Borg Integration (Tasks 11-12 Complete)

```bash
cd borglife_proto_private/code
# Test proto_borg with real adapter
python -c "
from proto_borg import ProtoBorgAgent, BorgConfig
from archon_adapter import ArchonServiceAdapter
config = BorgConfig(service_index='test-borg')
borg = ProtoBorgAgent(config)
print('✅ Proto-Borg Real Integration OK')
"
```

### Level 4: End-to-End Validation (Tasks 13-15 Complete)

```bash
cd borglife_proto_private
# Start services
docker-compose up -d

# Wait for stabilization
sleep 10

# Run integration tests
cd code
python -m pytest tests/test_service_integration.py -v --tb=short
python -m pytest tests/test_error_handling.py -v --tb=short
python -m pytest tests/e2e_test_suite.py -v --tb=short
```

## Final Validation Checklist

### Technical Validation

- [ ] All 15 implementation tasks completed successfully
- [ ] All Archon services integrate without mock fallbacks
- [ ] Circuit breaker protection active for all service calls
- [ ] Connection pooling reduces HTTP overhead
- [ ] Health checks work for all service endpoints
- [ ] Error handling provides meaningful recovery options
- [ ] Rate limiting prevents service throttling

### Feature Validation

- [ ] Proto-borg initializes with real Archon services
- [ ] MCP tool calls execute through actual endpoints
- [ ] Task execution uses real agent services
- [ ] Wealth tracking integrates with actual billing
- [ ] Service failures trigger circuit breaker protection
- [ ] Recovery mechanisms restore service functionality

### Code Quality Validation

- [ ] Follows existing async patterns and error handling
- [ ] File placement matches desired codebase tree structure
- [ ] Anti-patterns avoided (no direct HTTP calls without circuit breaker)
- [ ] Dependencies properly managed and imported
- [ ] Configuration properly environment-driven

### Documentation & Deployment

- [ ] Service integration documented with troubleshooting guides
- [ ] Circuit breaker behavior and recovery documented
- [ ] Environment configuration documented
- [ ] Docker deployment validated with real services
- [ ] Performance benchmarks meet 5-minute execution requirement

---

## Anti-Patterns to Avoid

- ❌ Don't make direct HTTP calls without circuit breaker protection
- ❌ Don't skip async initialization for service connections
- ❌ Don't hardcode service URLs - use environment configuration
- ❌ Don't ignore circuit breaker state in error handling
- ❌ Don't create tight coupling between services
- ❌ Don't forget connection cleanup in async contexts
- ❌ Don't bypass rate limiting for performance reasons
- ❌ Don't use synchronous operations in async service calls