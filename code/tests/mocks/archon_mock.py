# borglife_prototype/tests/mocks/archon_mock.py
"""
Mock implementation of ArchonServiceAdapter for testing.

Provides deterministic responses for all Archon service calls without
requiring actual network connections or running services.
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from ...archon_adapter.config import ArchonConfig


class ArchonServiceMock:
    """
    Mock Archon service adapter for testing.

    Provides predictable responses for all service calls with configurable
    behavior for testing different scenarios.
    """

    def __init__(self, config: Optional[ArchonConfig] = None):
        self.config = config or ArchonConfig()
        self.call_history: List[Dict[str, Any]] = []
        self.should_fail = False
        self.fail_on_next_calls = 0

    async def initialize(self) -> bool:
        """Mock initialization - always succeeds."""
        return True

    async def check_health(self) -> Dict[str, Any]:
        """Mock health check with configurable responses."""
        if self.should_fail:
            return {
                "overall": False,
                "server": False,
                "mcp": False,
                "agents": False,
                "details": {"error": "Mock failure configured"},
            }

        return {
            "overall": True,
            "server": True,
            "mcp": True,
            "agents": True,
            "details": {
                "server": {"status": "healthy", "version": "1.0.0"},
                "mcp": {"status": "healthy", "tools": 15},
                "agents": {"status": "healthy", "models": ["gpt-4", "claude-3"]},
            },
        }

    async def perform_rag_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Mock RAG query with sample response."""
        self._record_call("perform_rag_query", query=query, **kwargs)

        if self._should_fail():
            raise Exception("Mock RAG query failure")

        return {
            "query": query,
            "results": [
                {
                    "content": f"Mock RAG response for: {query}",
                    "source": "mock_source",
                    "relevance": 0.95,
                    "metadata": {"type": "mock"},
                }
            ],
            "total_results": 1,
            "processing_time": 0.1,
        }

    async def create_task(
        self, title: str, description: str, **kwargs
    ) -> Dict[str, Any]:
        """Mock task creation."""
        self._record_call("create_task", title=title, description=description, **kwargs)

        if self._should_fail():
            raise Exception("Mock task creation failure")

        return {
            "id": f"mock_task_{len(self.call_history)}",
            "title": title,
            "description": description,
            "status": "todo",
            "assignee": kwargs.get("assignee", "User"),
            "created_at": "2025-10-30T12:00:00Z",
        }

    async def list_tasks(self, **kwargs) -> List[Dict[str, Any]]:
        """Mock task listing."""
        self._record_call("list_tasks", **kwargs)

        if self._should_fail():
            raise Exception("Mock task listing failure")

        return [
            {
                "id": "mock_task_1",
                "title": "Mock Task 1",
                "description": "Mock task for testing",
                "status": "todo",
                "assignee": "User",
            }
        ]

    async def call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Mock MCP tool call."""
        self._record_call("call_mcp_tool", tool_name=tool_name, parameters=parameters)

        if self._should_fail():
            raise Exception(f"Mock MCP tool failure: {tool_name}")

        # Return mock responses based on tool name
        mock_responses = {
            "web_search": {"results": ["Mock web result"], "total": 1},
            "data_analysis": {"analysis": "Mock data analysis", "insights": []},
            "document_search": {"documents": [], "total": 0},
        }

        return mock_responses.get(tool_name, {"result": f"Mock {tool_name} response"})

    async def run_agent(self, agent_type: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Mock agent execution."""
        self._record_call("run_agent", agent_type=agent_type, prompt=prompt, **kwargs)

        if self._should_fail():
            raise Exception(f"Mock agent failure: {agent_type}")

        return {
            "agent_type": agent_type,
            "prompt": prompt,
            "response": f"Mock {agent_type} response to: {prompt[:50]}...",
            "model_used": kwargs.get("model", "gpt-4"),
            "processing_time": 0.5,
        }

    async def call_organ(
        self, borg_id: str, organ_name: str, tool: str, params: Dict[str, Any], **kwargs
    ) -> Any:
        """Mock organ call."""
        self._record_call(
            "call_organ",
            borg_id=borg_id,
            organ_name=organ_name,
            tool=tool,
            params=params,
            **kwargs,
        )

        if self._should_fail():
            raise Exception(f"Mock organ failure: {organ_name}")

        return {
            "organ": organ_name,
            "tool": tool,
            "result": f"Mock {organ_name} result for {tool}",
            "params": params,
        }

    def _record_call(self, method: str, **kwargs):
        """Record method call for testing verification."""
        self.call_history.append(
            {
                "method": method,
                "args": kwargs,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

    def _should_fail(self) -> bool:
        """Determine if current call should fail."""
        if self.fail_on_next_calls > 0:
            self.fail_on_next_calls -= 1
            return True
        return self.should_fail

    def configure_failure(self, should_fail: bool = True, fail_next_n: int = 0):
        """Configure mock to fail on subsequent calls."""
        self.should_fail = should_fail
        self.fail_on_next_calls = fail_next_n

    def reset_call_history(self):
        """Reset call history for testing."""
        self.call_history.clear()

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get recorded call history."""
        return self.call_history.copy()

    # Context manager support
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
