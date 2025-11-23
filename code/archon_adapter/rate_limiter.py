"""
Rate limiter for Docker MCP organ usage.

Implements borg-based rate limiting to prevent abuse and ensure fair resource allocation.
Tracks usage per borg per organ with configurable limits and reset periods.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OrganRateLimiter:
    """
    Rate limiter for Docker MCP organ usage with borg-based tracking.

    Implements sliding window rate limiting with configurable limits per organ.
    Tracks usage and provides reset time calculations for proper client behavior.
    """

    # Default rate limits per organ (requests per hour)
    DEFAULT_RATE_LIMITS = {
        "gmail": 100,  # Email operations - moderate limit
        "stripe": 50,  # Payment processing - conservative limit
        "bitcoin": 200,  # Blockchain queries - higher limit
        "mongodb": 500,  # Database operations - high limit
        "duckduckgo": 300,  # Web search - moderate-high limit
        "grafana": 1000,  # Metrics queries - very high limit
        "wikipedia": 500,  # Knowledge queries - high limit
        "arxiv": 200,  # Academic search - moderate limit
    }

    # Reset period in seconds (1 hour = 3600 seconds)
    RESET_PERIOD_SECONDS = 3600

    def __init__(
        self, supabase_client=None, custom_limits: Optional[Dict[str, int]] = None
    ):
        """
        Initialize rate limiter.

        Args:
            supabase_client: Supabase client for persistent storage (optional)
            custom_limits: Custom rate limits per organ (optional)
        """
        self.supabase = supabase_client
        self.rate_limits = self.DEFAULT_RATE_LIMITS.copy()
        if custom_limits:
            self.rate_limits.update(custom_limits)

        # In-memory cache for rate limiting (borg_id -> organ -> usage_data)
        self.usage_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def check_limit(
        self, borg_id: str, organ_name: str, wealth: Optional[float] = None
    ) -> Tuple[bool, int, int]:
        """
        Check if borg can make a request to the specified organ.

        Args:
            borg_id: Borg identifier
            organ_name: Docker MCP organ name
            wealth: Current borg wealth (for premium rate limits)

        Returns:
            (allowed: bool, current_usage: int, limit: int)
        """
        async with self._lock:
            # Get or create usage data for this borg/organ
            usage_data = await self._get_usage_data(borg_id, organ_name)

            # Check if we need to reset the window
            await self._check_reset_window(usage_data)

            # Get rate limit (may be adjusted based on wealth)
            limit = self._get_effective_limit(organ_name, wealth)

            # Check if under limit
            current_usage = usage_data["request_count"]
            allowed = current_usage < limit

            if allowed:
                # Record the request (will be incremented)
                await self._record_request(borg_id, organ_name)

            logger.debug(
                f"Rate limit check for {borg_id}:{organ_name} - {current_usage}/{limit}, allowed: {allowed}"
            )
            return allowed, current_usage, limit

    async def get_reset_time(self, borg_id: str, organ_name: str) -> datetime:
        """
        Get the time when the rate limit will reset for this borg/organ.

        Args:
            borg_id: Borg identifier
            organ_name: Docker MCP organ name

        Returns:
            Reset time as datetime object
        """
        usage_data = await self._get_usage_data(borg_id, organ_name)
        return usage_data["window_start"] + timedelta(seconds=self.RESET_PERIOD_SECONDS)

    async def _record_request(self, borg_id: str, organ_name: str) -> None:
        """
        Record a request for rate limiting purposes.

        Args:
            borg_id: Borg identifier
            organ_name: Docker MCP organ name
        """
        async with self._lock:
            usage_data = await self._get_usage_data(borg_id, organ_name)

            # Increment request count
            usage_data["request_count"] += 1
            usage_data["last_request"] = datetime.utcnow()

            # Persist to Supabase if available
            if self.supabase:
                try:
                    await self.supabase.table("borg_rate_limits").upsert(
                        {
                            "borg_id": borg_id,
                            "organ_name": organ_name,
                            "request_count": usage_data["request_count"],
                            "window_start": usage_data["window_start"].isoformat(),
                            "last_request": usage_data["last_request"].isoformat(),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist rate limit data: {e}")

    async def _get_usage_data(self, borg_id: str, organ_name: str) -> Dict[str, Any]:
        """
        Get usage data for a borg/organ combination.

        Args:
            borg_id: Borg identifier
            organ_name: Docker MCP organ name

        Returns:
            Usage data dictionary
        """
        # Initialize borg data if needed
        if borg_id not in self.usage_cache:
            self.usage_cache[borg_id] = {}

        # Get or create organ data
        if organ_name not in self.usage_cache[borg_id]:
            # Try to load from Supabase first
            usage_data = await self._load_usage_data(borg_id, organ_name)
            if usage_data is None:
                # Create new usage data
                usage_data = {
                    "request_count": 0,
                    "window_start": datetime.utcnow(),
                    "last_request": None,
                }
            self.usage_cache[borg_id][organ_name] = usage_data

        return self.usage_cache[borg_id][organ_name]

    async def _load_usage_data(
        self, borg_id: str, organ_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load usage data from Supabase.

        Args:
            borg_id: Borg identifier
            organ_name: Docker MCP organ name

        Returns:
            Usage data or None if not found
        """
        if not self.supabase:
            return None

        try:
            result = (
                await self.supabase.table("borg_rate_limits")
                .select("*")
                .eq("borg_id", borg_id)
                .eq("organ_name", organ_name)
                .single()
            )

            if result:
                return {
                    "request_count": result["request_count"],
                    "window_start": datetime.fromisoformat(result["window_start"]),
                    "last_request": (
                        datetime.fromisoformat(result["last_request"])
                        if result.get("last_request")
                        else None
                    ),
                }
        except Exception as e:
            logger.debug(f"Failed to load rate limit data from Supabase: {e}")

        return None

    async def _check_reset_window(self, usage_data: Dict[str, Any]) -> None:
        """
        Check if the rate limit window needs to be reset.

        Args:
            usage_data: Usage data dictionary to check/modify
        """
        now = datetime.utcnow()
        window_end = usage_data["window_start"] + timedelta(
            seconds=self.RESET_PERIOD_SECONDS
        )

        if now >= window_end:
            # Reset the window
            usage_data["request_count"] = 0
            usage_data["window_start"] = now
            logger.debug("Reset rate limit window")

    def _get_effective_limit(self, organ_name: str, wealth: Optional[float]) -> int:
        """
        Get the effective rate limit for an organ, potentially adjusted by wealth.

        Args:
            organ_name: Docker MCP organ name
            wealth: Current borg wealth

        Returns:
            Effective rate limit
        """
        base_limit = self.rate_limits.get(organ_name, 100)

        # Premium rate limits for wealthy borgs (simple heuristic)
        if wealth is not None and wealth > 10.0:  # More than 10 DOT
            return int(base_limit * 1.5)  # 50% bonus

        return base_limit

    async def get_usage_stats(self, borg_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a borg across all organs.

        Args:
            borg_id: Borg identifier

        Returns:
            Usage statistics dictionary
        """
        stats = {}
        total_requests = 0

        if borg_id in self.usage_cache:
            for organ_name, usage_data in self.usage_cache[borg_id].items():
                limit = self.rate_limits.get(organ_name, 100)
                usage_percent = (
                    (usage_data["request_count"] / limit) * 100 if limit > 0 else 0
                )

                stats[organ_name] = {
                    "request_count": usage_data["request_count"],
                    "limit": limit,
                    "usage_percent": round(usage_percent, 1),
                    "reset_time": usage_data["window_start"]
                    + timedelta(seconds=self.RESET_PERIOD_SECONDS),
                }
                total_requests += usage_data["request_count"]

        return {
            "borg_id": borg_id,
            "total_requests": total_requests,
            "organ_stats": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
