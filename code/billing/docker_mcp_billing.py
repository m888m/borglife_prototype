import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional


class DockerMCPBilling:
    """Track and bill for Docker MCP organ usage"""

    # Cost per API call (in DOT, calibrated for Kusama testnet)
    ORGAN_COSTS = {
        "gmail": Decimal("0.0005"),  # Email operations
        "stripe": Decimal("0.001"),  # Payment processing
        "bitcoin": Decimal("0.0008"),  # Blockchain queries
        "mongodb": Decimal("0.0003"),  # Database operations
        "duckduckgo": Decimal("0.0002"),  # Web search
        "grafana": Decimal("0.0004"),  # Metrics queries
    }

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.usage_cache = {}  # borg_id -> {organ: usage_count}

    async def track_organ_usage(
        self,
        borg_id: str,
        organ_name: str,
        operation: str,
        response_size: int = 0,
        execution_time: float = 0.0,
    ) -> Decimal:
        """
        Track organ usage and calculate cost

        Args:
            borg_id: Unique borg identifier
            organ_name: Docker MCP organ name
            operation: Specific operation performed
            response_size: Size of response in bytes
            execution_time: Time taken in seconds

        Returns:
            Cost in DOT for this operation
        """
        # Base cost per operation
        base_cost = self.ORGAN_COSTS.get(organ_name, Decimal("0.001"))

        # Size multiplier (larger responses cost more)
        size_multiplier = Decimal("1.0")
        if response_size > 1000:  # >1KB
            size_multiplier = Decimal("1.2")
        elif response_size > 10000:  # >10KB
            size_multiplier = Decimal("1.5")

        # Time multiplier (slower operations cost more)
        time_multiplier = Decimal("1.0")
        if execution_time > 2.0:  # >2 seconds
            time_multiplier = Decimal("1.1")
        elif execution_time > 5.0:  # >5 seconds
            time_multiplier = Decimal("1.3")

        # Calculate final cost
        total_cost = base_cost * size_multiplier * time_multiplier

        # Store usage record
        usage_record = {
            "borg_id": borg_id,
            "organ_name": organ_name,
            "operation": operation,
            "cost": str(total_cost),
            "response_size": response_size,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Insert into Supabase (async)
        asyncio.create_task(self._store_usage_record(usage_record))

        # Update cache for rate limiting
        if borg_id not in self.usage_cache:
            self.usage_cache[borg_id] = {}
        if organ_name not in self.usage_cache[borg_id]:
            self.usage_cache[borg_id][organ_name] = 0
        self.usage_cache[borg_id][organ_name] += 1

        return total_cost

    async def deduct_from_borg_wealth(
        self, borg_id: str, cost: Decimal, operation: str
    ) -> bool:
        """
        Deduct cost from borg's wealth tracking

        Returns:
            True if deduction successful, False if insufficient funds
        """
        # Get current wealth
        wealth_record = (
            await self.supabase.table("borg_wealth")
            .select("*")
            .eq("borg_id", borg_id)
            .single()
        )

        if not wealth_record:
            return False

        current_wealth = Decimal(str(wealth_record["total_wealth"]))

        if current_wealth < cost:
            # Insufficient funds - operation should be rejected
            return False

        # Deduct cost
        new_wealth = current_wealth - cost

        # Update wealth record
        await self.supabase.table("borg_wealth").update(
            {
                "total_wealth": str(new_wealth),
                "last_updated": datetime.utcnow().isoformat(),
            }
        ).eq("borg_id", borg_id)

        # Log transaction
        await self.supabase.table("borg_transactions").insert(
            {
                "borg_id": borg_id,
                "transaction_type": "cost",
                "amount": str(cost),
                "currency": "DOT",
                "description": f"Docker MCP organ usage: {operation}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return True

    async def get_borg_usage_summary(
        self, borg_id: str, days: int = 7
    ) -> Dict[str, Any]:
        """
        Get usage summary for borg

        Returns:
            {
                'total_cost': Decimal,
                'organ_breakdown': {organ: cost},
                'usage_count': int
            }
        """
        # Query Supabase for usage data
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        usage_records = (
            await self.supabase.table("organ_usage")
            .select("*")
            .eq("borg_id", borg_id)
            .gte("timestamp", cutoff_date.isoformat())
        )

        total_cost = Decimal("0")
        organ_breakdown = {}

        for record in usage_records:
            cost = Decimal(record["cost"])
            organ = record["organ_name"]

            total_cost += cost
            organ_breakdown[organ] = organ_breakdown.get(organ, Decimal("0")) + cost

        return {
            "total_cost": total_cost,
            "organ_breakdown": organ_breakdown,
            "usage_count": len(usage_records),
        }

    async def _store_usage_record(self, record: Dict[str, Any]):
        """Store usage record in Supabase"""
        try:
            await self.supabase.table("organ_usage").insert(record)
        except Exception as e:
            # Log error but don't fail operation
            print(f"Failed to store usage record: {e}")
