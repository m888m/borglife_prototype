"""
Main Archon Service Adapter

Provides unified interface to Archon services with resilience and monitoring.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .config import ArchonConfig
from .exceptions import (
    ArchonError, ArchonConnectionError, ArchonTimeoutError,
    ArchonServiceUnavailableError, ArchonVersionError
)


class ArchonServiceAdapter:
    """
    Unified adapter for Archon services.

    Provides resilient access to:
    - Archon Server (RAG, knowledge, projects, tasks)
    - Archon MCP (tool invocation)
    - Archon Agents (PydanticAI execution)

    Features:
    - Circuit breaker pattern
    - Retry logic with exponential backoff
    - Health monitoring
    - Version compatibility checks
    """

    def __init__(self, config: Optional[ArchonConfig] = None):
        """
        Initialize adapter with configuration.

        Args:
            config: ArchonConfig instance, uses defaults if None
        """
        self.config = config or ArchonConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.circuit_breaker_failures = 0
        self.circuit_breaker_open = False
        self.last_failure_time = 0
        self.health_status = {
            'archon_server': False,
            'archon_mcp': False,
            'archon_agents': False
        }

    async def initialize(self) -> None:
        """Initialize HTTP session and perform health checks."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)

        # Perform initial health checks
        await self.check_health()

    async def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def check_health(self) -> Dict[str, Any]:
        """
        Check health of all Archon services.

        Returns:
            Dict with health status for each service
        """
        if self.circuit_breaker_open:
            # Check if recovery timeout has passed
            if asyncio.get_event_loop().time() - self.last_failure_time > self.config.circuit_breaker_recovery_timeout:
                self.circuit_breaker_open = False
                self.circuit_breaker_failures = 0
            else:
                return {
                    'circuit_breaker': 'open',
                    'status': 'degraded'
                }

        health_results = {}

        # Check each service
        services = {
            'archon_server': f"{self.config.archon_server_url}/health",
            'archon_mcp': f"{self.config.archon_mcp_url}/health",
            'archon_agents': f"{self.config.archon_agents_url}/health"
        }

        for service_name, health_url in services.items():
            try:
                async with self.session.get(health_url, timeout=self.config.health_check_timeout) as response:
                    health_results[service_name] = response.status == 200
            except Exception:
                health_results[service_name] = False

        # Update circuit breaker
        all_healthy = all(health_results.values())
        if not all_healthy:
            self.circuit_breaker_failures += 1
            self.last_failure_time = asyncio.get_event_loop().time()

            if self.circuit_breaker_failures >= self.config.circuit_breaker_failure_threshold:
                self.circuit_breaker_open = True

        self.health_status.update(health_results)
        health_results.update({
            'circuit_breaker': 'open' if self.circuit_breaker_open else 'closed',
            'status': 'healthy' if all_healthy else 'degraded'
        })

        return health_results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ArchonConnectionError, ArchonTimeoutError))
    )
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response data as dict

        Raises:
            ArchonConnectionError: Connection failed
            ArchonTimeoutError: Request timed out
            ArchonServiceUnavailableError: Service unavailable
        """
        if self.circuit_breaker_open:
            raise ArchonServiceUnavailableError("Circuit breaker is open")

        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status >= 500:
                    raise ArchonServiceUnavailableError(f"Server error: {response.status}")
                elif response.status == 429:
                    raise ArchonServiceUnavailableError("Rate limited")
                else:
                    error_text = await response.text()
                    raise ArchonError(f"Request failed: {response.status} - {error_text}")

        except asyncio.TimeoutError:
            raise ArchonTimeoutError(f"Request to {url} timed out")
        except aiohttp.ClientError as e:
            raise ArchonConnectionError(f"Connection failed: {e}")

    async def perform_rag_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform RAG query using Archon server.

        Args:
            query: Search query
            **kwargs: Additional parameters

        Returns:
            RAG results
        """
        if not self.config.enable_rag:
            raise ArchonError("RAG queries are disabled")

        url = f"{self.config.archon_server_url}/api/knowledge/rag"
        data = {'query': query, **kwargs}

        return await self._make_request('POST', url, json=data)

    async def call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Call MCP tool through Archon MCP server.

        Args:
            tool_name: Name of the tool to call
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        url = f"{self.config.archon_mcp_url}/tools/{tool_name}"
        data = {'parameters': parameters}

        result = await self._make_request('POST', url, json=data)
        return result.get('result')

    async def run_agent(self, agent_type: str, prompt: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run PydanticAI agent through Archon agents service.

        Args:
            agent_type: Type of agent (RagAgent, DocumentAgent, etc.)
            prompt: Agent prompt
            parameters: Additional parameters

        Returns:
            Agent execution result
        """
        url = f"{self.config.archon_agents_url}/agents/run"
        data = {
            'agent_type': agent_type,
            'prompt': prompt,
            'parameters': parameters or {}
        }

        return await self._make_request('POST', url, json=data)

    async def create_task(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        """
        Create task using Archon server.

        Args:
            title: Task title
            description: Task description
            **kwargs: Additional task parameters

        Returns:
            Task creation result
        """
        if not self.config.enable_tasks:
            raise ArchonError("Task management is disabled")

        url = f"{self.config.archon_server_url}/api/tasks"
        data = {
            'title': title,
            'description': description,
            **kwargs
        }

        return await self._make_request('POST', url, json=data)

    async def list_tasks(self, **kwargs) -> List[Dict[str, Any]]:
        """
        List tasks from Archon server.

        Args:
            **kwargs: Query parameters

        Returns:
            List of tasks
        """
        if not self.config.enable_tasks:
            raise ArchonError("Task management is disabled")

        url = f"{self.config.archon_server_url}/api/tasks"
        result = await self._make_request('GET', url, params=kwargs)
        return result.get('tasks', [])

    async def create_project(self, name: str, description: str, **kwargs) -> Dict[str, Any]:
        """
        Create project using Archon server.

        Args:
            name: Project name
            description: Project description
            **kwargs: Additional project parameters

        Returns:
            Project creation result
        """
        url = f"{self.config.archon_server_url}/api/projects"
        data = {
            'name': name,
            'description': description,
            **kwargs
        }

        return await self._make_request('POST', url, json=data)

    async def search_code_examples(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search code examples using Archon MCP.

        Args:
            query: Search query
            **kwargs: Additional parameters

        Returns:
            Code search results
        """
        return await self.call_mcp_tool('archon:search_code_examples', {'query': query, **kwargs})

    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about connected Archon services.

        Returns:
            Service information and capabilities
        """
        health = await self.check_health()

        return {
            'services': self.config.get_service_urls(),
            'health': health,
            'config': {
                'timeout': self.config.request_timeout,
                'max_retries': self.config.max_retries,
                'features': {
                    'rag': self.config.enable_rag,
                    'tasks': self.config.enable_tasks,
                    'crawling': self.config.enable_crawling
                }
            },
            'circuit_breaker': {
                'open': self.circuit_breaker_open,
                'failures': self.circuit_breaker_failures,
                'last_failure': self.last_failure_time
            }
        }

    # Context manager support
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()