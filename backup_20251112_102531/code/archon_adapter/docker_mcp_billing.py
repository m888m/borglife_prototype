# borglife_prototype/archon_adapter/docker_mcp_billing.py
"""
Docker MCP Organ Billing - Track and bill for Docker MCP organ usage.

Implements micro-cost calculations and wealth tracking for organ usage,
integrating with Borglife's economic model (Δ(W) = R - C).
"""

from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class DockerMCPBilling:
    """Track and bill for Docker MCP organ usage with micro-costs."""

    # Base cost per API call in DOT (calibrated for Kusama testnet)
    BASE_COSTS = {
        'gmail': Decimal('0.0005'),      # Email operations
        'stripe': Decimal('0.001'),      # Payment processing
        'bitcoin': Decimal('0.0008'),    # Blockchain queries
        'mongodb': Decimal('0.0003'),    # Database operations
        'duckduckgo': Decimal('0.0002'), # Web search
        'grafana': Decimal('0.0004'),    # Metrics queries
        'wikipedia': Decimal('0.0001'),  # Knowledge queries
        'arxiv': Decimal('0.0002'),      # Academic search
    }

    # Cost multipliers based on operation complexity
    COMPLEXITY_MULTIPLIERS = {
        'simple': Decimal('1.0'),     # Basic queries
        'medium': Decimal('1.5'),     # Data processing
        'complex': Decimal('2.0'),    # Advanced operations
    }

    def __init__(self, supabase_client=None):
        """
        Initialize billing manager.

        Args:
            supabase_client: Supabase client for persistence (optional)
        """
        self.supabase = supabase_client
        self.usage_cache = {}  # borg_id -> {organ: usage_count}

    async def estimate_cost(
        self,
        organ_name: str,
        tool: str,
        params: Dict[str, Any]
    ) -> Decimal:
        """
        Estimate cost for an organ operation before execution.

        Args:
            organ_name: Docker MCP organ name
            tool: Tool/operation name
            params: Operation parameters

        Returns:
            Estimated cost in DOT
        """
        base_cost = self.BASE_COSTS.get(organ_name, Decimal('0.001'))

        # Determine complexity based on parameters
        complexity = self._assess_complexity(params)
        multiplier = self.COMPLEXITY_MULTIPLIERS[complexity]

        # Size multiplier for large responses
        size_multiplier = self._calculate_size_multiplier(params)

        estimated_cost = base_cost * multiplier * size_multiplier

        logger.debug(f"Estimated cost for {organ_name}:{tool}: {estimated_cost} DOT")
        return estimated_cost

    async def track_organ_usage(
        self,
        borg_id: str,
        organ_name: str,
        operation: str,
        response_size: int = 0,
        execution_time: float = 0.0,
        actual_cost: Optional[Decimal] = None
    ) -> Decimal:
        """
        Track organ usage and calculate actual cost.

        Args:
            borg_id: Borg identifier
            organ_name: Docker MCP organ name
            operation: Specific operation performed
            response_size: Size of response in bytes
            execution_time: Time taken in seconds
            actual_cost: Pre-calculated cost (optional)

        Returns:
            Actual cost in DOT for this operation
        """
        if actual_cost is None:
            # Estimate cost if not provided
            actual_cost = await self.estimate_cost(organ_name, operation, {})

        # Apply execution time multiplier
        time_multiplier = self._calculate_time_multiplier(execution_time)
        final_cost = actual_cost * time_multiplier

        # Store usage record
        usage_record = {
            'borg_id': borg_id,
            'organ_name': organ_name,
            'operation': operation,
            'cost': str(final_cost),
            'response_size': response_size,
            'execution_time': execution_time,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Persist to Supabase if available
        if self.supabase:
            try:
                await self.supabase.table('organ_usage').insert(usage_record)
            except Exception as e:
                logger.warning(f"Failed to persist usage record: {e}")

        # Update cache for rate limiting
        if borg_id not in self.usage_cache:
            self.usage_cache[borg_id] = {}
        if organ_name not in self.usage_cache[borg_id]:
            self.usage_cache[borg_id][organ_name] = 0
        self.usage_cache[borg_id][organ_name] += 1

        logger.info(f"Tracked usage: {borg_id} used {organ_name}:{operation} for {final_cost} DOT")
        return final_cost

    async def deduct_from_borg_wealth(
        self,
        borg_id: str,
        cost: Decimal,
        operation: str
    ) -> bool:
        """
        Deduct cost from borg's wealth tracking (Δ(W) = R - C).

        Args:
            borg_id: Borg identifier
            cost: Cost to deduct
            operation: Description of operation

        Returns:
            True if deduction successful, False if insufficient funds
        """
        if not self.supabase:
            logger.warning("No Supabase client - wealth deduction skipped")
            return True  # Allow operation in development

        try:
            # Get current wealth
            wealth_record = await self.supabase.table('borg_wealth').select('*').eq('borg_id', borg_id).single()

            if not wealth_record:
                logger.error(f"No wealth record found for borg {borg_id}")
                return False

            current_wealth = Decimal(str(wealth_record['total_wealth']))

            if current_wealth < cost:
                logger.warning(f"Insufficient funds for borg {borg_id}: {current_wealth} < {cost}")
                return False

            # Deduct cost
            new_wealth = current_wealth - cost

            # Update wealth record
            await self.supabase.table('borg_wealth').update({
                'total_wealth': str(new_wealth),
                'last_updated': datetime.utcnow().isoformat()
            }).eq('borg_id', borg_id)

            # Log transaction
            await self.supabase.table('borg_transactions').insert({
                'borg_id': borg_id,
                'transaction_type': 'cost',
                'amount': str(cost),
                'currency': 'DOT',
                'description': f"Docker MCP organ usage: {operation}",
                'timestamp': datetime.utcnow().isoformat()
            })

            logger.info(f"Deducted {cost} DOT from borg {borg_id} wealth: {current_wealth} → {new_wealth}")
            return True

        except Exception as e:
            logger.error(f"Failed to deduct wealth for borg {borg_id}: {e}")
            return False

    async def get_borg_usage_summary(
        self,
        borg_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get usage summary for a borg.

        Args:
            borg_id: Borg identifier
            days: Number of days to look back

        Returns:
            Usage summary with costs and statistics
        """
        if not self.supabase:
            return {
                'total_cost': Decimal('0'),
                'organ_breakdown': {},
                'usage_count': 0
            }

        try:
            # Query usage records
            cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

            usage_records = await self.supabase.table('organ_usage').select('*').eq('borg_id', borg_id).gte('timestamp', cutoff_date.isoformat())

            total_cost = Decimal('0')
            organ_breakdown = {}

            for record in usage_records:
                cost = Decimal(record['cost'])
                organ = record['organ_name']

                total_cost += cost
                organ_breakdown[organ] = organ_breakdown.get(organ, Decimal('0')) + cost

            return {
                'total_cost': total_cost,
                'organ_breakdown': organ_breakdown,
                'usage_count': len(usage_records)
            }

        except Exception as e:
            logger.error(f"Failed to get usage summary for borg {borg_id}: {e}")
            return {
                'total_cost': Decimal('0'),
                'organ_breakdown': {},
                'usage_count': 0
            }

    def _assess_complexity(self, params: Dict[str, Any]) -> str:
        """Assess operation complexity based on parameters."""
        param_count = len(params)
        total_size = sum(len(str(v)) for v in params.values())

        if param_count <= 2 and total_size < 100:
            return 'simple'
        elif param_count <= 5 and total_size < 500:
            return 'medium'
        else:
            return 'complex'

    def _calculate_size_multiplier(self, params: Dict[str, Any]) -> Decimal:
        """Calculate multiplier based on expected response size."""
        # Simple heuristic based on operation type
        if any(keyword in str(params).lower() for keyword in ['list', 'search', 'query']):
            return Decimal('1.2')  # List operations often return more data
        elif any(keyword in str(params).lower() for keyword in ['create', 'update']):
            return Decimal('1.1')  # Write operations
        else:
            return Decimal('1.0')  # Default

    def _calculate_time_multiplier(self, execution_time: float) -> Decimal:
        """Calculate multiplier based on execution time."""
        if execution_time <= 1.0:
            return Decimal('1.0')  # Fast operations
        elif execution_time <= 3.0:
            return Decimal('1.1')  # Moderate time
        elif execution_time <= 10.0:
            return Decimal('1.3')  # Slow operations
        else:
            return Decimal('1.5')  # Very slow operations