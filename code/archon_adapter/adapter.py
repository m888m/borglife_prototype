# borglife_prototype/archon_adapter/adapter.py
"""
Archon Service Adapter - Main integration point between Borglife and Archon

This adapter provides a stable interface to Archon's services while isolating
Borglife from Archon implementation changes. It implements the adapter pattern
with circuit breakers, retry logic, and graceful degradation.
"""

from typing import Dict, Any, Optional, List
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from datetime import datetime, timedelta

from .config import ArchonConfig
from .exceptions import ArchonError, ServiceUnavailableError
from .health import HealthChecker
from .version import VersionCompatibility
from .fallback_manager import OrganFallbackManager
from .cache_manager import CacheManager
# from .rate_limiter import OrganRateLimiter  # Not implemented yet
from .docker_mcp_billing import DockerMCPBilling

logger = logging.getLogger(__name__)

class ArchonServiceAdapter:
    """
    Main adapter for Archon services integration.

    Provides unified interface to:
    - Archon Server (RAG, knowledge, projects, tasks)
    - Archon MCP (tool invocation)
    - Archon Agents (PydanticAI execution)
    - Docker MCP Organs (fallback and extended capabilities)
    """

    def __init__(self, config: Optional[ArchonConfig] = None):
        self.config = config or ArchonConfig()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )

        # Initialize components
        self.health_checker = HealthChecker(self.client, self.config)
        self.version_compat = VersionCompatibility()
        self.fallback_manager = OrganFallbackManager(self)
        self.cache_manager = CacheManager()
        # self.rate_limiter = OrganRateLimiter()  # Not implemented yet
        self.rate_limiter = None
        self.billing_manager = DockerMCPBilling(self.config.supabase_client)

        # Service endpoints
        self.endpoints = {
            'server': self.config.archon_server_url,
            'mcp': self.config.archon_mcp_url,
            'agents': self.config.archon_agents_url
        }

        # Circuit breaker state
        self.circuit_breaker = {
            'server': {'failures': 0, 'last_failure': None, 'open': False},
            'mcp': {'failures': 0, 'last_failure': None, 'open': False},
            'agents': {'failures': 0, 'last_failure': None, 'open': False}
        }

    async def initialize(self) -> bool:
        """
        Initialize adapter and verify service connectivity.

        Returns:
            True if all services are accessible
        """
        try:
            # Check service health
            health = await self.check_health()
            if not health['overall']:
                logger.warning("Some Archon services unavailable during initialization")
                return False

            # Initialize cache
            await self.cache_manager.initialize()
            # Rate limiter not implemented yet

            logger.info("Archon adapter initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Archon adapter: {e}")
            return False

    async def check_health(self) -> Dict[str, Any]:
        """
        Check health of all Archon services.

        Returns:
            {
                'overall': bool,
                'server': bool,
                'mcp': bool,
                'agents': bool,
                'details': {...}
            }
        """
        return await self.health_checker.check_all_services()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=lambda exc: isinstance(exc, (httpx.TimeoutException, httpx.HTTPError))
    )
    async def perform_rag_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Perform RAG query via Archon server.

        Args:
            query: Search query
            context: Additional context for query
            use_cache: Whether to use cached results

        Returns:
            RAG results with sources and relevance scores
        """
        # Check circuit breaker
        if self._is_circuit_open('server'):
            raise ServiceUnavailableError("Archon server circuit breaker is open")

        # Check cache first
        if use_cache:
            cache_key = f"rag:{hash(query)}"
            cached = await self.cache_manager.get_cached_result('rag', 'query', {'query': query})
            if cached:
                return cached['result']

        try:
            url = f"{self.endpoints['server']}/api/knowledge/rag"
            payload = {'query': query}
            if context:
                payload.update(context)

            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()

            # Cache successful results
            if use_cache:
                await self.cache_manager.cache_result('rag', 'query', {'query': query}, result, ttl=300)

            # Reset circuit breaker
            self._reset_circuit('server')

            return result

        except Exception as e:
            self._record_circuit_failure('server')
            logger.error(f"RAG query failed: {e}")
            raise ArchonError(f"RAG query failed: {e}")

    async def create_task(
        self,
        title: str,
        description: str,
        project_id: Optional[str] = None,
        assignee: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a task via Archon.

        Args:
            title: Task title
            description: Task description
            project_id: Optional project ID
            assignee: Optional assignee

        Returns:
            Created task details
        """
        if self._is_circuit_open('server'):
            raise ServiceUnavailableError("Archon server circuit breaker is open")

        try:
            url = f"{self.endpoints['server']}/api/tasks"
            payload = {
                'title': title,
                'description': description,
                'project_id': project_id,
                'assignee': assignee
            }

            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            self._reset_circuit('server')

            return result

        except Exception as e:
            self._record_circuit_failure('server')
            logger.error(f"Task creation failed: {e}")
            raise ArchonError(f"Task creation failed: {e}")

    async def list_tasks(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List tasks from Archon.

        Args:
            project_id: Filter by project
            status: Filter by status
            limit: Maximum number of tasks

        Returns:
            List of tasks
        """
        if self._is_circuit_open('server'):
            raise ServiceUnavailableError("Archon server circuit breaker is open")

        try:
            url = f"{self.endpoints['server']}/api/tasks"
            params = {}
            if project_id:
                params['project_id'] = project_id
            if status:
                params['status'] = status
            params['limit'] = limit

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            result = response.json()
            self._reset_circuit('server')

            return result.get('tasks', [])

        except Exception as e:
            self._record_circuit_failure('server')
            logger.error(f"Task listing failed: {e}")
            raise ArchonError(f"Task listing failed: {e}")

    async def call_mcp_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout: float = 30.0
    ) -> Any:
        """
        Call MCP tool via Archon MCP server.

        Args:
            tool_name: Name of the tool to call
            parameters: Tool parameters
            timeout: Request timeout in seconds

        Returns:
            Tool execution result
        """
        if self._is_circuit_open('mcp'):
            raise ServiceUnavailableError("Archon MCP circuit breaker is open")

        try:
            url = f"{self.endpoints['mcp']}/tools/{tool_name}/call"

            response = await self.client.post(
                url,
                json=parameters,
                timeout=timeout
            )
            response.raise_for_status()

            result = response.json()
            self._reset_circuit('mcp')

            return result

        except Exception as e:
            self._record_circuit_failure('mcp')
            logger.error(f"MCP tool call failed: {e}")
            raise ArchonError(f"MCP tool call failed: {e}")

    async def run_agent(
        self,
        agent_type: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        streaming: bool = False
    ) -> Dict[str, Any]:
        """
        Run PydanticAI agent via Archon agents service.

        Args:
            agent_type: Type of agent (e.g., 'rag', 'document')
            prompt: Agent prompt
            context: Additional context
            streaming: Whether to use streaming response

        Returns:
            Agent execution result
        """
        if self._is_circuit_open('agents'):
            raise ServiceUnavailableError("Archon agents circuit breaker is open")

        try:
            if streaming:
                url = f"{self.endpoints['agents']}/agents/{agent_type}/stream"
            else:
                url = f"{self.endpoints['agents']}/agents/run"

            payload = {
                'agent_type': agent_type,
                'prompt': prompt,
                'context': context or {}
            }

            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            self._reset_circuit('agents')

            return result

        except Exception as e:
            self._record_circuit_failure('agents')
            logger.error(f"Agent execution failed: {e}")
            raise ArchonError(f"Agent execution failed: {e}")

    async def call_organ(
        self,
        borg_id: str,
        organ_name: str,
        tool: str,
        params: Dict[str, Any],
        wealth: Optional[float] = None,
        use_fallbacks: bool = True
    ) -> Any:
        """
        Call Docker MCP organ with fallback support.

        Args:
            borg_id: Borg identifier
            organ_name: Docker MCP organ name
            tool: Tool/operation to execute
            params: Tool parameters
            wealth: Current borg wealth for billing
            use_fallbacks: Whether to use fallback strategies

        Returns:
            Tool execution result
        """
        # Check rate limit (disabled for now)
        # allowed, current_usage, limit = await self.rate_limiter.check_limit(
        #     borg_id, organ_name, wealth
        # )
        allowed = True
        current_usage = 0
        limit = 100

        if not allowed:
            raise ArchonError(
                f"Rate limit exceeded for {organ_name}. "
                f"Used {current_usage}/{limit} requests"
            )

        # Execute with fallbacks
        try:
            result, level, description = await self.fallback_manager.execute_with_fallback(
                borg_id, organ_name, tool, params, max_fallbacks=3 if use_fallbacks else 0
            )

            # Track billing
            if wealth is not None:
                cost = await self.billing_manager.track_organ_usage(
                    borg_id=borg_id,
                    organ_name=organ_name,
                    operation=tool,
                    response_size=len(str(result)),
                    execution_time=0.0  # Would be measured
                )

                # Deduct from wealth
                success = await self.billing_manager.deduct_from_borg_wealth(
                    borg_id, cost, f"{organ_name}:{tool}"
                )

                if not success:
                    logger.warning(f"Failed to deduct {cost} DOT from borg {borg_id}")

            return result

        except Exception as e:
            logger.error(f"Organ call failed for {organ_name}:{tool}: {e}")
            raise

    async def call_organ(
        self,
        borg_id: str,
        organ_name: str,
        tool: str,
        params: Dict[str, Any],
        wealth: Optional[float] = None,
        use_fallbacks: bool = True
    ) -> Any:
        """
        Call Docker MCP organ with fallback support.

        Args:
            borg_id: Borg identifier
            organ_name: Docker MCP organ name
            tool: Tool/operation to execute
            params: Tool parameters
            wealth: Current borg wealth for billing
            use_fallbacks: Whether to use fallback strategies

        Returns:
            Tool execution result
        """
        # Check rate limit
        allowed, current_usage, limit = await self.rate_limiter.check_limit(
            borg_id, organ_name, wealth
        )

        if not allowed:
            raise ArchonError(
                f"Rate limit exceeded for {organ_name}. "
                f"Used {current_usage}/{limit} requests"
            )

        # Execute with fallbacks
        try:
            result, level, description = await self.fallback_manager.execute_with_fallback(
                borg_id, organ_name, tool, params, max_fallbacks=3 if use_fallbacks else 0
            )

            # Track billing
            if wealth is not None:
                cost = await self.billing_manager.track_organ_usage(
                    borg_id=borg_id,
                    organ_name=organ_name,
                    operation=tool,
                    response_size=len(str(result)),
                    execution_time=0.0  # Would be measured
                )

                # Deduct from wealth
                success = await self.billing_manager.deduct_from_borg_wealth(
                    borg_id, cost, f"{organ_name}:{tool}"
                )

                if not success:
                    logger.warning(f"Failed to deduct {cost} DOT from borg {borg_id}")

            return result

        except Exception as e:
            logger.error(f"Organ call failed for {organ_name}:{tool}: {e}")
            raise

    async def call_archon_tool(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        Call native Archon MCP tool (used by fallback manager).

        Args:
            tool_name: Archon tool name
            params: Tool parameters

        Returns:
            Tool execution result
        """
        return await self.call_mcp_tool(tool_name, params)

    def _is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open for service."""
        breaker = self.circuit_breaker[service]
        if breaker['open']:
            # Check if we should attempt reset
            if breaker['last_failure']:
                if datetime.utcnow() - breaker['last_failure'] > timedelta(minutes=5):
                    breaker['open'] = False
                    breaker['failures'] = 0
                    return False
            return True
        return False

    def _record_circuit_failure(self, service: str):
        """Record circuit breaker failure."""
        breaker = self.circuit_breaker[service]
        breaker['failures'] += 1
        breaker['last_failure'] = datetime.utcnow()

        # Open circuit after 5 failures
        if breaker['failures'] >= 5:
            breaker['open'] = True
            logger.warning(f"Circuit breaker opened for {service}")

    def _reset_circuit(self, service: str):
        """Reset circuit breaker on success."""
        breaker = self.circuit_breaker[service]
        breaker['failures'] = 0
        breaker['open'] = False

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
        await self.cache_manager.close()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()