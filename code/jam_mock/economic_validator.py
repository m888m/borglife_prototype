"""
Economic Validator for Phase 2A

Validates economic operations and transfers with dual-currency support.
Integrates with EthicalComplianceMonitor and DemoCostController.
"""

import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .demo_audit_logger import DemoAuditLogger
from .demo_cost_controller import DemoCostController
from .ethical_compliance_monitor import EthicalComplianceMonitor


class EconomicValidator:
    """
    Validates economic operations for borg fund holding and transfers.

    Integrates ethical compliance monitoring, cost controls, and balance validation
    for secure dual-currency economic activities.
    """

    def __init__(
        self,
        cost_controller: DemoCostController,
        compliance_monitor: EthicalComplianceMonitor,
        supabase_client=None,
        audit_logger: Optional[DemoAuditLogger] = None,
    ):
        """
        Initialize EconomicValidator.

        Args:
            cost_controller: Cost controller for budget management
            compliance_monitor: Ethical compliance monitor
            supabase_client: Supabase client for database queries
            audit_logger: Audit logger for compliance tracking
        """
        self.cost_controller = cost_controller
        self.compliance_monitor = compliance_monitor
        self.supabase = supabase_client
        self.audit_logger = audit_logger or DemoAuditLogger()

        # Economic thresholds
        self.min_balance_threshold = Decimal(
            "0.001"
        )  # Minimum balance to prevent starvation
        self.max_transfer_limit = Decimal("1000")  # Maximum single transfer
        self.daily_transfer_limit = Decimal("5000")  # Daily transfer limit per borg

    async def validate_transfer(
        self,
        from_borg_id: str,
        to_borg_id: str,
        currency: str,
        amount: Decimal,
        asset_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive transfer validation.

        Args:
            from_borg_id: Sending borg ID
            to_borg_id: Receiving borg ID
            currency: 'WND' or 'USDB'
            amount: Transfer amount
            asset_id: Asset ID for USDB transfers

        Returns:
            Validation result with success status and details
        """
        validation_result = {
            "valid": True,
            "checks": {},
            "warnings": [],
            "errors": [],
            "recommendations": [],
        }

        # Basic validation
        basic_check = self._validate_basic_transfer_params(
            from_borg_id, to_borg_id, currency, amount
        )
        validation_result["checks"]["basic"] = basic_check

        if not basic_check["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(basic_check["errors"])
            return validation_result

        # Balance validation
        balance_check = await self._validate_sufficient_balance(
            from_borg_id, currency, amount, asset_id
        )
        validation_result["checks"]["balance"] = balance_check

        if not balance_check["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(balance_check["errors"])

        # Ethical compliance check
        ethical_check = await self._validate_ethical_compliance(
            from_borg_id, to_borg_id, currency, amount
        )
        validation_result["checks"]["ethical"] = ethical_check

        if not ethical_check["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(ethical_check["errors"])

        # Cost control validation
        cost_check = await self._validate_cost_controls(from_borg_id, currency, amount)
        validation_result["checks"]["cost"] = cost_check

        if not cost_check["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(cost_check["errors"])

        # Rate limiting check
        rate_check = await self._validate_transfer_limits(from_borg_id, amount)
        validation_result["checks"]["rate_limit"] = rate_check

        if not rate_check["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(rate_check["errors"])

        # Add recommendations
        if validation_result["valid"]:
            validation_result["recommendations"].append(
                "Transfer approved and ready for execution"
            )
        else:
            validation_result["recommendations"].append(
                "Address validation errors before proceeding"
            )

        # Log validation result
        self.audit_logger.log_event(
            "transfer_validation",
            f"Transfer validation {'passed' if validation_result['valid'] else 'failed'} for {from_borg_id} -> {to_borg_id}",
            {
                "from_borg_id": from_borg_id,
                "to_borg_id": to_borg_id,
                "currency": currency,
                "amount": str(amount),
                "valid": validation_result["valid"],
                "error_count": len(validation_result["errors"]),
            },
        )

        return validation_result

    def _validate_basic_transfer_params(
        self, from_borg_id: str, to_borg_id: str, currency: str, amount: Decimal
    ) -> Dict[str, Any]:
        """Validate basic transfer parameters."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Borg ID validation
        if not from_borg_id or not to_borg_id:
            result["valid"] = False
            result["errors"].append("Missing borg IDs")

        if from_borg_id == to_borg_id:
            result["valid"] = False
            result["errors"].append("Cannot transfer to self")

        # Currency validation
        if currency not in ["WND", "USDB"]:
            result["valid"] = False
            result["errors"].append(f"Invalid currency: {currency}")

        # Amount validation
        if amount <= 0:
            result["valid"] = False
            result["errors"].append("Transfer amount must be positive")

        if amount > self.max_transfer_limit:
            result["valid"] = False
            result["errors"].append(
                f"Transfer amount exceeds maximum limit: {self.max_transfer_limit}"
            )

        return result

    async def _validate_sufficient_balance(
        self, borg_id: str, currency: str, amount: Decimal, asset_id: Optional[int]
    ) -> Dict[str, Any]:
        """Validate that borg has sufficient balance for transfer."""
        result = {"valid": True, "errors": [], "warnings": []}

        if not self.supabase:
            result["warnings"].append(
                "No database connection - balance validation skipped"
            )
            return result

        try:
            # Query current balance
            balance_result = (
                self.supabase.table("borg_balances")
                .select("balance_wei")
                .eq("borg_id", borg_id)
                .eq("currency", currency)
                .execute()
            )

            if not balance_result.data:
                result["valid"] = False
                result["errors"].append("No balance record found")
                return result

            current_balance_wei = balance_result.data[0]["balance_wei"]
            current_balance = Decimal(str(current_balance_wei)) / Decimal(
                "1000000000000"
            )  # Convert from planck to token units

            if current_balance < amount:
                result["valid"] = False
                result["errors"].append(
                    f"Insufficient balance: {current_balance} {currency} available, {amount} {currency} required"
                )

            # Check minimum balance threshold
            remaining_balance = current_balance - amount
            if remaining_balance < self.min_balance_threshold:
                result["warnings"].append(
                    f"Transfer would leave borg with low balance: {remaining_balance} {currency}"
                )

        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Balance validation error: {str(e)}")

        return result

    async def _validate_ethical_compliance(
        self, from_borg_id: str, to_borg_id: str, currency: str, amount: Decimal
    ) -> Dict[str, Any]:
        """Validate transfer against ethical compliance rules."""
        result = {"valid": True, "errors": [], "warnings": []}

        try:
            # Check for harmful transfers (would cause borg "starvation")
            if self.supabase:
                # Get recipient balance
                recipient_balance_result = (
                    self.supabase.table("borg_balances")
                    .select("balance_wei")
                    .eq("borg_id", to_borg_id)
                    .eq("currency", currency)
                    .execute()
                )

                if recipient_balance_result.data:
                    recipient_balance_wei = recipient_balance_result.data[0][
                        "balance_wei"
                    ]
                    recipient_balance = Decimal(str(recipient_balance_wei)) / Decimal(
                        "1000000000000"
                    )

                    # If recipient already has high balance, this might be concentration of wealth
                    if recipient_balance > Decimal("1000"):
                        result["warnings"].append(
                            "Recipient already has high balance - consider wealth distribution"
                        )

            # Use ethical compliance monitor for additional checks
            compliance_result = await self.compliance_monitor.validate_transfer_ethics(
                from_borg_id, to_borg_id, float(amount), currency
            )

            if not compliance_result.get("approved", True):
                result["valid"] = False
                result["errors"].append("Transfer violates ethical compliance rules")

        except Exception as e:
            result["warnings"].append(f"Ethical compliance check error: {str(e)}")

        return result

    async def _validate_cost_controls(
        self, borg_id: str, currency: str, amount: Decimal
    ) -> Dict[str, Any]:
        """Validate transfer against cost control budgets."""
        result = {"valid": True, "errors": [], "warnings": []}

        try:
            # Check if borg has sufficient budget for this transfer
            budget_check = self.cost_controller.check_transfer_budget(
                borg_id, currency, float(amount)
            )

            if not budget_check.get("approved", True):
                result["valid"] = False
                result["errors"].append("Transfer exceeds budget limits")

            # Check for unusual transfer patterns
            pattern_check = self.cost_controller.detect_unusual_patterns(
                borg_id, "transfer", float(amount)
            )

            if pattern_check.get("flagged", False):
                result["warnings"].append("Unusual transfer pattern detected")

        except Exception as e:
            result["warnings"].append(f"Cost control validation error: {str(e)}")

        return result

    async def _validate_transfer_limits(
        self, borg_id: str, amount: Decimal
    ) -> Dict[str, Any]:
        """Validate transfer against rate limits."""
        result = {"valid": True, "errors": [], "warnings": []}

        if not self.supabase:
            result["warnings"].append(
                "No database connection - rate limit validation skipped"
            )
            return result

        try:
            # Check daily transfer limit
            # This is a simplified implementation - in production you'd track daily totals
            daily_total = await self._get_daily_transfer_total(borg_id)

            if daily_total + amount > self.daily_transfer_limit:
                result["valid"] = False
                result["errors"].append(
                    f"Daily transfer limit exceeded: {daily_total + amount} > {self.daily_transfer_limit}"
                )

        except Exception as e:
            result["warnings"].append(f"Rate limit validation error: {str(e)}")

        return result

    async def _get_daily_transfer_total(self, borg_id: str) -> Decimal:
        """Get total transfers for today (simplified implementation)."""
        # In a real implementation, this would query recent transfers
        # For now, return 0 (no limits enforced)
        return Decimal("0")

    async def validate_balance_distribution(
        self, borg_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Validate overall balance distribution across borgs.

        Args:
            borg_ids: List of borg IDs to check

        Returns:
            Distribution analysis and recommendations
        """
        result = {
            "total_borgs": len(borg_ids),
            "balances": {},
            "distribution_analysis": {},
            "recommendations": [],
        }

        if not self.supabase:
            result["error"] = "No database connection"
            return result

        try:
            # Get all balances
            for borg_id in borg_ids:
                balance_result = (
                    self.supabase.table("borg_balances")
                    .select("*")
                    .eq("borg_id", borg_id)
                    .execute()
                )

                if balance_result.data:
                    result["balances"][borg_id] = {
                        record["currency"]: Decimal(str(record["balance_wei"]))
                        / Decimal("1000000000000")
                        for record in balance_result.data
                    }

            # Analyze distribution
            wnd_balances = [
                balances.get("WND", Decimal("0"))
                for balances in result["balances"].values()
            ]
            usdb_balances = [
                balances.get("USDB", Decimal("0"))
                for balances in result["balances"].values()
            ]

            result["distribution_analysis"] = {
                "wnd_total": sum(wnd_balances),
                "usdb_total": sum(usdb_balances),
                "wnd_avg": (
                    sum(wnd_balances) / len(wnd_balances)
                    if wnd_balances
                    else Decimal("0")
                ),
                "usdb_avg": (
                    sum(usdb_balances) / len(usdb_balances)
                    if usdb_balances
                    else Decimal("0")
                ),
                "gini_coefficient": self._calculate_gini(
                    usdb_balances
                ),  # Focus on wealth distribution
            }

            # Generate recommendations
            gini = result["distribution_analysis"]["gini_coefficient"]
            if gini > 0.7:
                result["recommendations"].append(
                    "High wealth concentration detected - consider redistribution mechanisms"
                )
            elif gini < 0.3:
                result["recommendations"].append("Good wealth distribution maintained")

        except Exception as e:
            result["error"] = str(e)

        return result

    def _calculate_gini(self, values: List[Decimal]) -> float:
        """Calculate Gini coefficient for wealth distribution."""
        if not values:
            return 0.0

        # Sort values
        sorted_values = sorted(values)
        n = len(values)
        cumsum = sum((i + 1) * val for i, val in enumerate(sorted_values))
        total = sum(sorted_values)

        if total == 0:
            return 0.0

        return float((2 * cumsum) / (n * total) - (n + 1) / n)
