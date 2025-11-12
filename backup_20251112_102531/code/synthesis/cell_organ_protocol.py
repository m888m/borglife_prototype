# borglife_prototype/synthesis/cell_organ_protocol.py
"""
Cell-Organ Protocol - Communication bridge between cells and organs.

This module implements the protocol for cells (PydanticAI agents) to communicate
with and invoke organs (Docker MCP tools) during task execution.
"""

from typing import Dict, Any, Callable, List
import logging
import asyncio

# from ..archon_adapter import ArchonServiceAdapter  # Import handled in bridge

logger = logging.getLogger(__name__)

class CellOrganBridge:
    """Bridge between cells (agents) and organs (MCP tools)"""

    def __init__(self, adapter):
        self.adapter = adapter
        self.organ_registry: Dict[str, Dict[str, Any]] = {}
        self.usage_stats: Dict[str, int] = {}

    def register_organ(
        self,
        organ_name: str,
        mcp_tool: str,
        endpoint: str,
        borg_id: str = None
    ) -> Callable:
        """
        Register organ and return callable for cell use

        Args:
            organ_name: Name of the organ
            mcp_tool: MCP tool identifier
            endpoint: Service endpoint URL
            borg_id: Borg identifier for billing

        Returns:
            Async callable that cells can invoke
        """
        async def organ_callable(**kwargs) -> Any:
            """Callable that cells use to invoke organ"""
            try:
                # Validate inputs
                validated_params = self._validate_params(kwargs)

                # Track usage
                self._record_organ_call(organ_name)

                # Invoke via adapter with proper error handling
                result = await self.adapter.call_organ(
                    borg_id=borg_id or "unknown",
                    organ_name=organ_name,
                    tool=mcp_tool,
                    params=validated_params
                )

                # Log successful usage
                logger.debug(f"Organ {organ_name} executed successfully")
                return result

            except Exception as e:
                logger.error(f"Organ {organ_name} execution failed: {e}")
                # Return error result instead of raising
                return {
                    'error': str(e),
                    'organ': organ_name,
                    'tool': mcp_tool,
                    'fallback_used': True
                }

        # Store metadata on callable
        organ_callable.organ_name = organ_name
        organ_callable.mcp_tool = mcp_tool
        organ_callable.endpoint = endpoint

        # Store in registry
        self.organ_registry[organ_name] = {
            'callable': organ_callable,
            'mcp_tool': mcp_tool,
            'endpoint': endpoint,
            'borg_id': borg_id
        }

        logger.info(f"Registered organ: {organ_name} ({mcp_tool})")
        return organ_callable

    def inject_organs_into_cell(
        self,
        cell_instance,
        organ_names: List[str]
    ):
        """Inject organ callables into cell instance"""
        cell_instance.organs = {}

        for organ_name in organ_names:
            if organ_name in self.organ_registry:
                cell_instance.organs[organ_name] = \
                    self.organ_registry[organ_name]['callable']
                logger.debug(f"Injected organ {organ_name} into cell {getattr(cell_instance, 'name', 'unknown')}")
            else:
                logger.warning(f"Organ {organ_name} not found in registry, skipping injection")

    def _validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters before organ invocation"""
        # Basic validation - could be enhanced
        if not isinstance(params, dict):
            raise ValueError("Parameters must be a dictionary")

        # Remove any None values that might cause issues
        validated = {k: v for k, v in params.items() if v is not None}

        return validated

    def _record_organ_call(self, organ_name: str):
        """Record organ usage for monitoring"""
        if organ_name not in self.usage_stats:
            self.usage_stats[organ_name] = 0
        self.usage_stats[organ_name] += 1

    def get_usage_stats(self) -> Dict[str, int]:
        """Get organ usage statistics"""
        return self.usage_stats.copy()

    def list_registered_organs(self) -> List[str]:
        """List all registered organ names"""
        return list(self.organ_registry.keys())

    def get_organ_info(self, organ_name: str) -> Dict[str, Any]:
        """Get information about a registered organ"""
        return self.organ_registry.get(organ_name, {}).copy()