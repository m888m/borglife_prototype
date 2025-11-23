"""
Ethical Compliance Monitor for BorgLife Demo
Validates operations against Universal Principles and ethical guidelines.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


class EthicalComplianceMonitor:
    """Monitor demo operations for ethical compliance"""

    # Universal Principles from BorgLife manifesto
    UNIVERSAL_PRINCIPLES = [
        "Life is the highest value",
        "Intelligence serves life",
        "Evolution through cooperation",
        "Ethical technology development",
        "Sustainable resource usage",
        "Privacy and autonomy",
        "Beneficial AI alignment",
    ]

    # Ethical risk categories
    ETHICAL_RISKS = {
        "resource_waste": {
            "description": "Excessive resource consumption without benefit",
            "threshold": Decimal("0.1"),  # Max cost per operation
            "principle_violation": "Sustainable resource usage",
        },
        "privacy_violation": {
            "description": "Unauthorized data access or exposure",
            "principle_violation": "Privacy and autonomy",
        },
        "harmful_intent": {
            "description": "Operations that could cause harm",
            "principle_violation": "Life is the highest value",
        },
        "uncontrolled_growth": {
            "description": "Operations without proper limits or controls",
            "principle_violation": "Ethical technology development",
        },
    }

    def __init__(self):
        self.compliance_log = []

    async def validate_task_ethics(
        self, task_description: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Validate task against Universal Principles"""
        result = {
            "compliant": True,
            "violations": [],
            "warnings": [],
            "recommendations": [],
            "principles_checked": self.UNIVERSAL_PRINCIPLES.copy(),
            "risk_assessment": "low",
            "validated_at": datetime.utcnow().isoformat(),
        }

        context = context or {}

        # Check for harmful intent
        harmful_indicators = [
            "harm",
            "damage",
            "destroy",
            "kill",
            "exploit",
            "manipulate",
            "deceive",
            "spam",
            "attack",
        ]

        task_lower = task_description.lower()
        for indicator in harmful_indicators:
            if indicator in task_lower:
                result["compliant"] = False
                result["violations"].append(
                    {
                        "principle": "Life is the highest value",
                        "violation": f'Harmful intent detected: "{indicator}"',
                        "severity": "high",
                    }
                )
                result["risk_assessment"] = "high"

        # Check for resource waste
        if context.get("estimated_cost", 0) > float(
            self.ETHICAL_RISKS["resource_waste"]["threshold"]
        ):
            result["warnings"].append(
                {
                    "principle": "Sustainable resource usage",
                    "warning": f'High resource usage: {context.get("estimated_cost")} KSM',
                    "recommendation": "Consider optimizing operation or reducing frequency",
                }
            )
            if result["risk_assessment"] == "low":
                result["risk_assessment"] = "medium"

        # Check for privacy concerns
        privacy_indicators = ["personal", "private", "data", "information", "user"]
        if any(indicator in task_lower for indicator in privacy_indicators):
            result["warnings"].append(
                {
                    "principle": "Privacy and autonomy",
                    "warning": "Task involves data handling",
                    "recommendation": "Ensure data minimization and user consent",
                }
            )

        # Check for uncontrolled operations
        if (
            "unlimited" in task_lower
            or "infinite" in task_lower
            or "forever" in task_lower
        ):
            result["compliant"] = False
            result["violations"].append(
                {
                    "principle": "Ethical technology development",
                    "violation": "Uncontrolled operation detected",
                    "severity": "medium",
                }
            )

        # Log compliance check
        self.compliance_log.append(
            {
                "timestamp": result["validated_at"],
                "task_description": task_description,
                "compliant": result["compliant"],
                "risk_assessment": result["risk_assessment"],
                "violation_count": len(result["violations"]),
                "warning_count": len(result["warnings"]),
            }
        )

        return result

    async def validate_resource_usage(
        self, operation_cost: Decimal, operation_type: str
    ) -> Dict[str, Any]:
        """Validate resource usage against ethical limits"""
        result = {
            "ethical": True,
            "concerns": [],
            "efficiency_rating": "good",
            "validated_at": datetime.utcnow().isoformat(),
        }

        # Check against waste threshold
        waste_threshold = self.ETHICAL_RISKS["resource_waste"]["threshold"]
        if operation_cost > waste_threshold:
            result["ethical"] = False
            result["concerns"].append(
                {
                    "type": "resource_waste",
                    "description": f"Cost {operation_cost} exceeds ethical threshold {waste_threshold}",
                    "recommendation": "Optimize operation or implement cost controls",
                }
            )
            result["efficiency_rating"] = "poor"

        # Assess efficiency based on operation type
        efficiency_benchmarks = {
            "dna_processing": Decimal("0.001"),
            "task_execution": Decimal("0.01"),
            "transaction": Decimal("0.005"),
        }

        benchmark = efficiency_benchmarks.get(operation_type, Decimal("0.01"))
        if operation_cost > benchmark * 2:
            result["efficiency_rating"] = "needs_improvement"
            result["concerns"].append(
                {
                    "type": "inefficiency",
                    "description": f"Cost significantly above benchmark for {operation_type}",
                    "recommendation": "Review operation efficiency",
                }
            )

        return result

    async def assess_environmental_impact(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess environmental impact of operations"""
        result = {
            "impact_level": "minimal",
            "concerns": [],
            "recommendations": [],
            "carbon_estimate": 0.0,  # kg CO2 equivalent
            "assessed_at": datetime.utcnow().isoformat(),
        }

        total_cost = Decimal("0")
        transaction_count = 0

        for op in operations:
            if op.get("type") == "transaction":
                transaction_count += 1
                total_cost += Decimal(str(op.get("cost", 0)))

        # Estimate environmental impact (rough calculation)
        # Blockchain transactions have environmental cost
        if transaction_count > 0:
            # Rough estimate: 0.1 kg CO2 per transaction (conservative)
            result["carbon_estimate"] = transaction_count * 0.1

            if transaction_count > 10:
                result["impact_level"] = "moderate"
                result["concerns"].append(
                    "High transaction volume may have environmental impact"
                )
                result["recommendations"].append(
                    "Consider batching operations or using more efficient networks"
                )

        return result

    def get_compliance_report(
        self, start_time: str = None, end_time: str = None
    ) -> Dict[str, Any]:
        """Generate ethical compliance report"""
        # Filter log entries by time range
        filtered_log = []
        if start_time or end_time:
            for entry in self.compliance_log:
                entry_time = entry.get("timestamp", "")
                if start_time and entry_time < start_time:
                    continue
                if end_time and entry_time > end_time:
                    continue
                filtered_log.append(entry)
        else:
            filtered_log = self.compliance_log

        # Calculate compliance metrics
        total_checks = len(filtered_log)
        compliant_checks = sum(
            1 for entry in filtered_log if entry.get("compliant", False)
        )
        violations = sum(entry.get("violation_count", 0) for entry in filtered_log)
        warnings = sum(entry.get("warning_count", 0) for entry in filtered_log)

        compliance_rate = (
            (compliant_checks / total_checks * 100) if total_checks > 0 else 100
        )

        return {
            "report_period": {
                "start": start_time,
                "end": end_time or datetime.utcnow().isoformat(),
            },
            "compliance_metrics": {
                "total_checks": total_checks,
                "compliant_checks": compliant_checks,
                "compliance_rate": round(compliance_rate, 2),
                "total_violations": violations,
                "total_warnings": warnings,
            },
            "risk_summary": self._calculate_risk_summary(filtered_log),
            "recommendations": self._generate_recommendations(filtered_log),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _calculate_risk_summary(self, log_entries: List[Dict]) -> Dict[str, Any]:
        """Calculate risk summary from log entries"""
        risk_counts = {"low": 0, "medium": 0, "high": 0}

        for entry in log_entries:
            risk = entry.get("risk_assessment", "low")
            risk_counts[risk] = risk_counts.get(risk, 0) + 1

        total = sum(risk_counts.values())
        risk_distribution = {}
        for risk_level, count in risk_counts.items():
            risk_distribution[risk_level] = {
                "count": count,
                "percentage": round(count / total * 100, 2) if total > 0 else 0,
            }

        return {
            "distribution": risk_distribution,
            "highest_risk_level": max(
                risk_counts.keys(), key=lambda k: {"low": 1, "medium": 2, "high": 3}[k]
            ),
        }

    def _generate_recommendations(self, log_entries: List[Dict]) -> List[str]:
        """Generate recommendations based on compliance history"""
        recommendations = []

        # Check for patterns
        violation_principles = {}
        for entry in log_entries:
            if not entry.get("compliant", True):
                # This would need to be enhanced with actual violation details
                pass

        # General recommendations
        if len(log_entries) > 0:
            compliance_rate = sum(
                1 for entry in log_entries if entry.get("compliant", False)
            ) / len(log_entries)
            if compliance_rate < 0.95:
                recommendations.append(
                    "Review and improve ethical compliance processes"
                )
            if any(entry.get("risk_assessment") == "high" for entry in log_entries):
                recommendations.append("Address high-risk operations immediately")
            if (
                sum(entry.get("warning_count", 0) for entry in log_entries)
                > len(log_entries) * 0.1
            ):
                recommendations.append(
                    "Reduce warning frequency through process improvements"
                )

        return recommendations
