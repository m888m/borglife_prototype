import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from .docker_mcp_billing import DockerMCPBilling
from .exceptions import (AllFallbacksFailedError, InsufficientFundsError,
                         RateLimitExceededError)
from .fallback_manager import FallbackLevel, OrganFallbackManager
from .rate_limiter import OrganRateLimiter


class MCPClient:
    """Enhanced MCP client with rate limiting and billing"""

    def __init__(
        self,
        archon_adapter,
        fallback_manager: OrganFallbackManager,
        rate_limiter: OrganRateLimiter,
        billing_manager: DockerMCPBilling,
    ):
        self.archon_adapter = archon_adapter
        self.fallback_manager = fallback_manager
        self.rate_limiter = rate_limiter
        self.billing_manager = billing_manager

    async def call_organ_with_fallback(
        self,
        borg_id: str,
        organ_name: str,
        tool: str,
        params: Dict[str, Any],
        use_fallbacks: bool = True,
    ) -> Dict[str, Any]:
        """
        Call organ with automatic fallback support

        Returns:
            {
                'result': Any,
                'fallback_used': bool,
                'fallback_level': str,
                'fallback_description': str
            }
        """
        if use_fallbacks:
            try:
                result, level, description = (
                    await self.fallback_manager.execute_with_fallback(
                        borg_id, organ_name, tool, params
                    )
                )

                return {
                    "result": result,
                    "fallback_used": level != FallbackLevel.PRIMARY,
                    "fallback_level": level.name,
                    "fallback_description": description,
                }
            except AllFallbacksFailedError as e:
                # All fallbacks failed - return error info
                return {
                    "result": None,
                    "error": str(e),
                    "fallback_used": True,
                    "fallback_level": "FAILED",
                    "fallback_description": "All fallbacks exhausted",
                }
        else:
            # No fallbacks - direct call
            result = await self.archon_adapter.call_organ(
                borg_id, organ_name, tool, params
            )
            return {
                "result": result,
                "fallback_used": False,
                "fallback_level": "PRIMARY",
                "fallback_description": f"Direct call to {organ_name}",
            }

    async def call_organ(
        self,
        borg_id: str,
        organ_name: str,
        tool: str,
        params: Dict[str, Any],
        wealth: Optional[float] = None,
    ) -> Any:
        """
        Call Docker MCP organ with rate limiting and billing

        Raises:
            RateLimitExceededError: If rate limit exceeded
            InsufficientFundsError: If borg cannot afford operation
        """
        # Check rate limit
        allowed, current_usage, limit = await self.rate_limiter.check_limit(
            borg_id, organ_name, wealth
        )

        if not allowed:
            reset_time = await self.rate_limiter.get_reset_time(borg_id, organ_name)
            raise RateLimitExceededError(
                f"Rate limit exceeded for {organ_name}. "
                f"Used {current_usage}/{limit} requests. "
                f"Resets at {reset_time.isoformat()}"
            )

        # Estimate cost before execution (placeholder - would need implementation)
        estimated_cost = 0.001  # Default estimate

        # Check if borg can afford
        if wealth is not None and wealth < estimated_cost:
            raise InsufficientFundsError(
                f"Insufficient funds. Required: {estimated_cost} DOT, "
                f"Available: {wealth} DOT"
            )

        # Execute the call
        start_time = datetime.utcnow()
        try:
            result = await self._execute_call(organ_name, tool, params)
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Track usage and cost (simplified for now)
            actual_cost = estimated_cost  # Simplified

            # Deduct from wealth (placeholder - would need Supabase integration)
            if wealth is not None:
                # This would deduct from actual wealth tracking
                pass

            return result

        except Exception as e:
            # Still track failed attempts for rate limiting
            await self.rate_limiter._record_request(borg_id, organ_name)
            raise

    async def _execute_call(
        self, organ_name: str, tool: str, params: Dict[str, Any]
    ) -> Any:
        """
        Execute the actual organ call (placeholder implementation).

        In production, this would make HTTP calls to Docker MCP containers.
        """
        # Placeholder implementation - returns mock result
        # In real implementation, would call Docker MCP organ via HTTP
        return {
            "organ": organ_name,
            "tool": tool,
            "params": params,
            "result": f"Mock result from {organ_name}:{tool}",
            "timestamp": datetime.utcnow().isoformat(),
        }
