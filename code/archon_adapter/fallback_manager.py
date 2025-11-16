# borglife_prototype/archon_adapter/fallback_manager.py
from typing import Dict, Any, Optional, List, Callable, Tuple
from enum import Enum
import asyncio
from datetime import datetime, timedelta

class FallbackLevel(Enum):
    """Fallback hierarchy levels"""
    PRIMARY = 1      # Docker MCP organ (preferred)
    SECONDARY = 2    # Alternative Docker MCP organ
    ARCHON = 3       # Archon native MCP tool
    CACHED = 4       # Cached/stale results
    ERROR = 5        # No fallback available

class OrganFallbackManager:
    """Manage fallback strategies for Docker MCP organ failures"""

    # Fallback mapping: primary_organ -> [fallback_options]
    FALLBACK_MAPPING = {
        'gmail': [
            {'level': FallbackLevel.ARCHON, 'tool': 'archon:send_email', 'description': 'Archon email service'},
            {'level': FallbackLevel.CACHED, 'description': 'Skip email operations (cached)'}
        ],
        'stripe': [
            {'level': FallbackLevel.ERROR, 'description': 'No payment fallback available'}
        ],
        'bitcoin': [
            {'level': FallbackLevel.ARCHON, 'tool': 'archon:blockchain_query', 'description': 'Archon blockchain service'},
            {'level': FallbackLevel.CACHED, 'description': 'Use cached blockchain data'}
        ],
        'mongodb': [
            {'level': FallbackLevel.SECONDARY, 'organ': 'postgres', 'description': 'PostgreSQL fallback'},
            {'level': FallbackLevel.CACHED, 'description': 'Use cached database results'}
        ],
        'duckduckgo': [
            {'level': FallbackLevel.SECONDARY, 'organ': 'google', 'description': 'Google search fallback'},
            {'level': FallbackLevel.CACHED, 'description': 'Use cached search results'}
        ],
        'grafana': [
            {'level': FallbackLevel.SECONDARY, 'organ': 'prometheus', 'description': 'Prometheus metrics fallback'},
            {'level': FallbackLevel.CACHED, 'description': 'Use cached metrics'}
        ],
        'wikipedia': [
            {'level': FallbackLevel.SECONDARY, 'organ': 'wolfram', 'description': 'Wolfram knowledge fallback'},
            {'level': FallbackLevel.CACHED, 'description': 'Use cached knowledge'}
        ],
        'arxiv': [
            {'level': FallbackLevel.SECONDARY, 'organ': 'semantic_scholar', 'description': 'Semantic Scholar fallback'},
            {'level': FallbackLevel.CACHED, 'description': 'Use cached research data'}
        ]
    }

    def __init__(self, archon_adapter, cache_manager=None):
        self.archon_adapter = archon_adapter
        self.cache_manager = cache_manager or getattr(archon_adapter, "cache_manager", None)
        self.fallback_stats = {}  # Track fallback usage

    async def execute_with_fallback(
        self,
        borg_id: str,
        primary_organ: str,
        tool: str,
        params: Dict[str, Any],
        max_fallbacks: int = 3,
        wealth: Optional[float] = None
    ) -> Tuple[Any, FallbackLevel, str]:
        """
        Execute organ call with automatic fallback

        Returns:
            (result, fallback_level_used, description)

        Raises:
            AllFallbacksFailedError: If all fallbacks exhausted
        """
        fallbacks_tried = []

        # Try primary organ first
        try:
            result = await self.archon_adapter.invoke_primary_organ(
                borg_id=borg_id,
                organ_name=primary_organ,
                tool=tool,
                params=params,
                wealth=wealth
            )
            return result, FallbackLevel.PRIMARY, f"Primary organ: {primary_organ}"
        except Exception as e:
            fallbacks_tried.append(f"Primary {primary_organ}: {str(e)}")

        # Try fallbacks
        fallback_options = self.FALLBACK_MAPPING.get(primary_organ, [])

        for i, fallback in enumerate(fallback_options[:max_fallbacks]):
            if fallback['level'] == FallbackLevel.SECONDARY:
                # Try alternative Docker MCP organ
                alt_organ = fallback.get('organ')
                if alt_organ:
                    try:
                        result = await self.archon_adapter.invoke_primary_organ(
                            borg_id=borg_id,
                            organ_name=alt_organ,
                            tool=tool,
                            params=params,
                            wealth=wealth
                        )
                        self._record_fallback_usage(primary_organ, fallback['level'])
                        return result, fallback['level'], fallback['description']
                    except Exception as e:
                        fallbacks_tried.append(f"Secondary {alt_organ}: {str(e)}")

            elif fallback['level'] == FallbackLevel.ARCHON:
                # Try Archon native tool
                archon_tool = fallback.get('tool')
                if archon_tool:
                    try:
                        # Convert params to Archon format if needed
                        archon_params = self._convert_params_for_archon(params, primary_organ, archon_tool)
                        result = await self.archon_adapter.call_archon_tool(
                            archon_tool, archon_params
                        )
                        self._record_fallback_usage(primary_organ, fallback['level'])
                        return result, fallback['level'], fallback['description']
                    except Exception as e:
                        fallbacks_tried.append(f"Archon {archon_tool}: {str(e)}")

            elif fallback['level'] == FallbackLevel.CACHED:
                # Try cached results
                if self.cache_manager:
                    try:
                        cache_key = self._generate_cache_key(primary_organ, tool, params)
                        result = await self.cache_manager.get_cached_result(cache_key)
                        if result:
                            self._record_fallback_usage(primary_organ, fallback['level'])
                            return result, fallback['level'], f"{fallback['description']} (stale data)"
                    except Exception as e:
                        fallbacks_tried.append(f"Cached: {str(e)}")

        # All fallbacks failed
        error_msg = f"All fallbacks failed for {primary_organ}:{tool}. Tried: {'; '.join(fallbacks_tried)}"
        raise AllFallbacksFailedError(error_msg)

    def _convert_params_for_archon(
        self,
        original_params: Dict[str, Any],
        original_organ: str,
        archon_tool: str
    ) -> Dict[str, Any]:
        """
        Convert Docker MCP organ parameters to Archon tool format

        This handles parameter mapping between different services
        """
        # Gmail to Archon email
        if original_organ == 'gmail' and 'send_email' in archon_tool:
            return {
                'to': original_params.get('to'),
                'subject': original_params.get('subject'),
                'body': original_params.get('body')
            }

        # Bitcoin to Archon blockchain
        elif original_organ == 'bitcoin' and 'blockchain_query' in archon_tool:
            return {
                'query_type': 'transaction',
                'tx_hash': original_params.get('tx_hash')
            }

        # Default: pass through (may not work)
        return original_params

    def _generate_cache_key(
        self,
        organ: str,
        tool: str,
        params: Dict[str, Any]
    ) -> str:
        """Generate cache key for fallback results"""
        # Create deterministic key from organ, tool, and key params
        key_params = {k: v for k, v in params.items() if k in ['query', 'id', 'hash', 'address']}
        return f"fallback:{organ}:{tool}:{hash(str(sorted(key_params.items())))}"

    def _record_fallback_usage(self, primary_organ: str, fallback_level: FallbackLevel):
        """Record fallback usage for monitoring"""
        if primary_organ not in self.fallback_stats:
            self.fallback_stats[primary_organ] = {}

        level_key = fallback_level.name.lower()
        self.fallback_stats[primary_organ][level_key] = \
            self.fallback_stats[primary_organ].get(level_key, 0) + 1

    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get fallback usage statistics"""
        return self.fallback_stats.copy()

    async def is_organ_available(self, organ_name: str) -> bool:
        """Check if organ is currently available (not in fallback)"""
        # This would check health status
        # For now, assume available unless we know otherwise
        return True

    def get_available_fallbacks(self, organ_name: str) -> List[Dict[str, Any]]:
        """Get list of available fallback options for organ"""
        return self.FALLBACK_MAPPING.get(organ_name, [])