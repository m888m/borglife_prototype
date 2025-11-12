from typing import Any, Optional, Dict
import json
import hashlib
from datetime import datetime, timedelta
import redis.asyncio as redis

class CacheManager:
    """Manage cached results for fallback scenarios and performance optimization"""

    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 3600):
        """
        Initialize cache manager

        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        self.redis = redis.from_url(redis_url)
        self.default_ttl = default_ttl
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0
        }

    def _generate_cache_key(
        self,
        organ_name: str,
        tool: str,
        params: Dict[str, Any]
    ) -> str:
        """
        Generate deterministic cache key

        Args:
            organ_name: Docker MCP organ name
            tool: Tool/operation name
            params: Operation parameters

        Returns:
            Cache key string
        """
        # Extract key parameters (ignore timestamps, random values)
        key_params = {
            k: v for k, v in params.items()
            if k not in ['timestamp', 'nonce', 'request_id']
        }

        # Create deterministic hash
        param_str = json.dumps(key_params, sort_keys=True)
        param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]

        return f"cache:{organ_name}:{tool}:{param_hash}"

    async def cache_result(
        self,
        organ_name: str,
        tool: str,
        params: Dict[str, Any],
        result: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache operation result

        Args:
            organ_name: Docker MCP organ name
            tool: Tool/operation name
            params: Operation parameters
            result: Result to cache
            ttl: Time-to-live in seconds (optional)

        Returns:
            True if cached successfully
        """
        cache_key = self._generate_cache_key(organ_name, tool, params)
        ttl = ttl or self.default_ttl

        try:
            # Serialize result with metadata
            cache_data = {
                'result': result,
                'cached_at': datetime.utcnow().isoformat(),
                'organ': organ_name,
                'tool': tool,
                'ttl': ttl
            }

            serialized = json.dumps(cache_data)
            await self.redis.setex(cache_key, ttl, serialized)

            self.cache_stats['sets'] += 1
            return True

        except Exception as e:
            self.cache_stats['errors'] += 1
            print(f"Cache set error: {e}")
            return False

    async def get_cached_result(
        self,
        organ_name: str,
        tool: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result

        Returns:
            {
                'result': Any,
                'cached_at': str,
                'age_seconds': int,
                'is_stale': bool
            } or None if not found
        """
        cache_key = self._generate_cache_key(organ_name, tool, params)

        try:
            cached = await self.redis.get(cache_key)

            if cached:
                cache_data = json.loads(cached)
                cached_at = datetime.fromisoformat(cache_data['cached_at'])
                age_seconds = (datetime.utcnow() - cached_at).total_seconds()

                self.cache_stats['hits'] += 1

                return {
                    'result': cache_data['result'],
                    'cached_at': cache_data['cached_at'],
                    'age_seconds': int(age_seconds),
                    'is_stale': age_seconds > cache_data['ttl'] * 0.8  # 80% of TTL
                }
            else:
                self.cache_stats['misses'] += 1
                return None

        except Exception as e:
            self.cache_stats['errors'] += 1
            print(f"Cache get error: {e}")
            return None

    async def invalidate_cache(
        self,
        organ_name: str,
        tool: Optional[str] = None
    ) -> int:
        """
        Invalidate cached results

        Args:
            organ_name: Docker MCP organ name
            tool: Specific tool (optional, invalidates all if None)

        Returns:
            Number of keys invalidated
        """
        if tool:
            # Invalidate specific tool
            pattern = f"cache:{organ_name}:{tool}:*"
        else:
            # Invalidate all for organ
            pattern = f"cache:{organ_name}:*"

        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)
                return deleted
            return 0

        except Exception as e:
            print(f"Cache invalidation error: {e}")
            return 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache_stats.copy()