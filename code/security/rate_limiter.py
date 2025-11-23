import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis


class OrganRateLimiter:
    """Rate limit organ usage per borg to prevent abuse"""

    # Default limits per organ per hour
    DEFAULT_LIMITS = {
        "gmail": 100,  # Email operations - moderate limit
        "stripe": 50,  # Payment processing - strict limit
        "bitcoin": 200,  # Blockchain queries - generous limit
        "mongodb": 500,  # Database operations - high limit
        "duckduckgo": 300,  # Web search - generous limit
        "grafana": 1000,  # Metrics queries - very generous
        "wikipedia": 500,  # Knowledge queries - high limit
        "arxiv": 200,  # Academic search - moderate limit
    }

    # Premium limits for borgs with high wealth
    PREMIUM_THRESHOLDS = {
        "wealth_threshold": 1.0,  # 1 DOT minimum for premium
        "multiplier": 2.0,  # 2x limits for premium borgs
    }

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.local_cache = defaultdict(
            lambda: defaultdict(list)
        )  # borg_id -> organ -> timestamps

    async def check_limit(
        self, borg_id: str, organ_name: str, wealth: Optional[float] = None
    ) -> Tuple[bool, int, int]:
        """
        Check if borg is within rate limit for organ

        Args:
            borg_id: Unique borg identifier
            organ_name: Docker MCP organ name
            wealth: Current borg wealth (optional, for premium limits)

        Returns:
            (allowed: bool, current_usage: int, limit: int)
        """
        # Determine limit based on wealth
        base_limit = self.DEFAULT_LIMITS.get(organ_name, 100)
        if wealth and wealth >= self.PREMIUM_THRESHOLDS["wealth_threshold"]:
            limit = int(base_limit * self.PREMIUM_THRESHOLDS["multiplier"])
        else:
            limit = base_limit

        # Get current usage in sliding window (last hour)
        window_start = datetime.utcnow() - timedelta(hours=1)
        current_usage = await self._get_usage_count(borg_id, organ_name, window_start)

        allowed = current_usage < limit

        if allowed:
            # Record this request
            await self._record_request(borg_id, organ_name)

        return allowed, current_usage, limit

    async def _get_usage_count(
        self, borg_id: str, organ_name: str, window_start: datetime
    ) -> int:
        """Get usage count in sliding window"""
        key = f"rate_limit:{borg_id}:{organ_name}"

        # Get all timestamps in window
        timestamps = await self.redis.zrangebyscore(
            key,
            window_start.timestamp(),
            datetime.utcnow().timestamp(),
            withscores=False,
        )

        return len(timestamps)

    async def _record_request(self, borg_id: str, organ_name: str):
        """Record a request timestamp"""
        key = f"rate_limit:{borg_id}:{organ_name}"
        timestamp = datetime.utcnow().timestamp()

        # Add timestamp to sorted set
        await self.redis.zadd(key, {str(timestamp): timestamp})

        # Clean up old entries (older than 2 hours to be safe)
        cutoff = (datetime.utcnow() - timedelta(hours=2)).timestamp()
        await self.redis.zremrangebyscore(key, 0, cutoff)

    async def get_remaining_requests(
        self, borg_id: str, organ_name: str, wealth: Optional[float] = None
    ) -> int:
        """Get remaining requests in current window"""
        allowed, current_usage, limit = await self.check_limit(
            borg_id, organ_name, wealth
        )
        return max(0, limit - current_usage)

    async def get_reset_time(self, borg_id: str, organ_name: str) -> datetime:
        """Get when the rate limit resets (next hour boundary)"""
        now = datetime.utcnow()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return next_hour

    async def bulk_check_limits(
        self, borg_id: str, organ_names: List[str], wealth: Optional[float] = None
    ) -> Dict[str, Tuple[bool, int, int]]:
        """
        Check rate limits for multiple organs efficiently

        Returns:
            {organ_name: (allowed, current_usage, limit)}
        """
        results = {}
        for organ_name in organ_names:
            allowed, usage, limit = await self.check_limit(borg_id, organ_name, wealth)
            results[organ_name] = (allowed, usage, limit)

        return results

    async def get_borg_limits_summary(
        self, borg_id: str, wealth: Optional[float] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive rate limit status for all organs

        Returns:
            {
                organ_name: {
                    'limit': int,
                    'current_usage': int,
                    'remaining': int,
                    'reset_time': datetime,
                    'is_premium': bool
                }
            }
        """
        summary = {}
        is_premium = wealth and wealth >= self.PREMIUM_THRESHOLDS["wealth_threshold"]

        for organ_name in self.DEFAULT_LIMITS.keys():
            allowed, current_usage, limit = await self.check_limit(
                borg_id, organ_name, wealth
            )
            remaining = max(0, limit - current_usage)
            reset_time = await self.get_reset_time(borg_id, organ_name)

            summary[organ_name] = {
                "limit": limit,
                "current_usage": current_usage,
                "remaining": remaining,
                "reset_time": reset_time.isoformat(),
                "is_premium": is_premium,
            }

        return summary
