"""
Cost Control System for BorgLife Demo
Implements spending limits and budget tracking for ethical compliance.
"""

import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional


class DemoCostController:
    """Control and monitor demo costs"""

    def __init__(
        self,
        max_budget: Decimal = Decimal("1.0"),
        alert_threshold: Decimal = Decimal("0.5"),
        budget_file: str = "code/jam_mock/.budget.json",
    ):
        self.max_budget = max_budget
        self.alert_threshold = alert_threshold
        self.budget_file = Path(budget_file)
        self.budget_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_spend = self._load_budget_state()

    def _load_budget_state(self) -> Decimal:
        """Load current budget state from file"""
        try:
            if self.budget_file.exists():
                with open(self.budget_file, "r") as f:
                    data = json.load(f)
                    return Decimal(str(data.get("current_spend", "0")))
            return Decimal("0")
        except Exception:
            return Decimal("0")

    def _save_budget_state(self):
        """Save current budget state to file"""
        try:
            data = {
                "current_spend": str(self.current_spend),
                "max_budget": str(self.max_budget),
                "alert_threshold": str(self.alert_threshold),
                "last_updated": datetime.utcnow().isoformat(),
            }
            with open(self.budget_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save budget state: {e}")

    async def check_cost_limit(
        self, proposed_cost: Decimal, operation_type: str = "general"
    ) -> Dict[str, Any]:
        """Check if operation would exceed cost limits"""
        result = {
            "approved": True,
            "warnings": [],
            "remaining_budget": self.max_budget - self.current_spend,
            "checked_at": datetime.utcnow().isoformat(),
        }

        # Check if this operation would exceed budget
        projected_total = self.current_spend + proposed_cost
        if projected_total > self.max_budget:
            result["approved"] = False
            result["warnings"].append(
                {
                    "type": "budget_exceeded",
                    "message": f"Operation cost {proposed_cost} would exceed budget. "
                    f"Current: {self.current_spend}, Max: {self.max_budget}",
                    "severity": "high",
                }
            )
            return result

        # Check alert threshold
        if projected_total > (self.max_budget * self.alert_threshold):
            result["warnings"].append(
                {
                    "type": "budget_warning",
                    "message": f"Operation would bring spending to {projected_total} "
                    f"({projected_total/self.max_budget*100:.1f}% of budget)",
                    "severity": "medium",
                }
            )

        # Operation-specific limits
        op_limits = {
            "transaction": Decimal("0.01"),  # Max per transaction
            "dna_storage": Decimal("0.005"),  # Max per DNA storage
            "task_execution": Decimal("0.001"),  # Max per task
        }

        if operation_type in op_limits:
            limit = op_limits[operation_type]
            if proposed_cost > limit:
                result["approved"] = False
                result["warnings"].append(
                    {
                        "type": "operation_limit_exceeded",
                        "message": f"{operation_type} cost {proposed_cost} exceeds limit of {limit}",
                        "severity": "high",
                    }
                )

        return result

    async def record_cost(
        self, cost: Decimal, operation_type: str, operation_id: str = None
    ) -> bool:
        """Record a cost against the budget"""
        try:
            # Validate cost
            if cost < 0:
                print(f"Invalid cost: {cost} (cannot be negative)")
                return False

            # Check if this would exceed budget
            check_result = await self.check_cost_limit(cost, operation_type)
            if not check_result["approved"]:
                print(f"Cost recording rejected: {check_result['warnings']}")
                return False

            # Record the cost
            self.current_spend += cost
            self._save_budget_state()

            # Log the transaction
            self._log_budget_transaction(cost, operation_type, operation_id, "recorded")

            print(
                f"✅ Cost recorded: {cost} KSM for {operation_type} "
                f"(Total spend: {self.current_spend}/{self.max_budget})"
            )

            return True
        except Exception as e:
            print(f"Failed to record cost: {e}")
            return False

    async def refund_cost(
        self, cost: Decimal, operation_type: str, operation_id: str = None
    ) -> bool:
        """Refund a cost (for failed operations)"""
        try:
            if cost < 0:
                print(f"Invalid refund amount: {cost}")
                return False

            # Prevent negative spend
            if self.current_spend - cost < 0:
                print(f"Cannot refund {cost}: would result in negative spend")
                return False

            self.current_spend -= cost
            self._save_budget_state()

            self._log_budget_transaction(cost, operation_type, operation_id, "refunded")

            print(
                f"💰 Cost refunded: {cost} KSM for {operation_type} "
                f"(Total spend: {self.current_spend}/{self.max_budget})"
            )

            return True
        except Exception as e:
            print(f"Failed to refund cost: {e}")
            return False

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status"""
        remaining = self.max_budget - self.current_spend
        utilization_percent = (
            (self.current_spend / self.max_budget * 100) if self.max_budget > 0 else 0
        )

        status = "good"
        if utilization_percent > 90:
            status = "critical"
        elif utilization_percent > 75:
            status = "warning"

        return {
            "current_spend": self.current_spend,
            "max_budget": self.max_budget,
            "remaining_budget": remaining,
            "utilization_percent": round(utilization_percent, 2),
            "status": status,
            "alert_threshold": self.alert_threshold,
            "last_updated": datetime.utcnow().isoformat(),
        }

    def reset_budget(self, new_budget: Optional[Decimal] = None) -> bool:
        """Reset budget for new period"""
        try:
            if new_budget is not None:
                self.max_budget = new_budget

            self.current_spend = Decimal("0")
            self._save_budget_state()

            self._log_budget_transaction(Decimal("0"), "budget_reset", None, "reset")

            print(f"🔄 Budget reset to {self.max_budget} KSM")
            return True
        except Exception as e:
            print(f"Failed to reset budget: {e}")
            return False

    def _log_budget_transaction(
        self, amount: Decimal, operation_type: str, operation_id: str, action: str
    ):
        """Log budget transactions for audit trail"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "amount": str(amount),
                "operation_type": operation_type,
                "operation_id": operation_id,
                "running_total": str(self.current_spend),
                "budget_limit": str(self.max_budget),
            }

            log_file = self.budget_file.parent / "budget_transactions.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Failed to log budget transaction: {e}")

    def get_budget_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get budget transaction history"""
        try:
            log_file = self.budget_file.parent / "budget_transactions.jsonl"
            if not log_file.exists():
                return []

            cutoff_date = datetime.utcnow() - timedelta(days=days)
            transactions = []

            with open(log_file, "r") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        entry_date = datetime.fromisoformat(entry["timestamp"])
                        if entry_date >= cutoff_date:
                            transactions.append(entry)

            return transactions
        except Exception as e:
            print(f"Failed to read budget history: {e}")
            return []

    def generate_budget_report(self) -> Dict[str, Any]:
        """Generate comprehensive budget report"""
        history = self.get_budget_history()
        status = self.get_budget_status()

        # Calculate spending patterns
        transaction_count = len([t for t in history if t["action"] == "recorded"])
        refund_count = len([t for t in history if t["action"] == "refunded"])

        total_recorded = sum(
            Decimal(t["amount"]) for t in history if t["action"] == "recorded"
        )
        total_refunded = sum(
            Decimal(t["amount"]) for t in history if t["action"] == "refunded"
        )

        # Operation type breakdown
        op_breakdown = {}
        for transaction in history:
            if transaction["action"] == "recorded":
                op_type = transaction["operation_type"]
                amount = Decimal(transaction["amount"])
                op_breakdown[op_type] = op_breakdown.get(op_type, Decimal("0")) + amount

        return {
            "budget_status": status,
            "spending_summary": {
                "total_recorded": total_recorded,
                "total_refunded": total_refunded,
                "net_spend": total_recorded - total_refunded,
                "transaction_count": transaction_count,
                "refund_count": refund_count,
            },
            "operation_breakdown": {k: str(v) for k, v in op_breakdown.items()},
            "recent_transactions": history[-10:],  # Last 10 transactions
            "generated_at": datetime.utcnow().isoformat(),
        }
