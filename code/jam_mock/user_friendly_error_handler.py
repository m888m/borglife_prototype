"""
User-Friendly Error Handler for BorgLife Demo
Converts technical errors to user-friendly messages with actionable guidance.
"""

from datetime import datetime
from typing import Any, Dict, Optional


class UserFriendlyErrorHandler:
    """Convert technical errors to user-friendly messages"""

    ERROR_MESSAGES = {
        # Keypair errors
        "keypair_not_found": {
            "message": "Demo keypair not configured. Please set up testnet account.",
            "action": "Run setup script: python setup_kusama_testnet.py",
            "severity": "high",
        },
        "keypair_load_failed": {
            "message": "Failed to load demo keypair. Security issue detected.",
            "action": "Contact administrator or re-run setup",
            "severity": "high",
        },
        "keypair_encryption_failed": {
            "message": "Keypair encryption error. Cannot securely store keys.",
            "action": "Check encryption configuration and try again",
            "severity": "high",
        },
        # Network errors
        "network_timeout": {
            "message": "Network connection slow. Retrying automatically...",
            "action": "Check internet connection. Will retry up to 3 times.",
            "severity": "medium",
        },
        "network_unreachable": {
            "message": "Cannot connect to blockchain network.",
            "action": "Check network connection and try again in a few minutes.",
            "severity": "medium",
        },
        "rpc_endpoint_down": {
            "message": "Blockchain RPC service temporarily unavailable.",
            "action": "Switching to backup endpoint automatically.",
            "severity": "low",
        },
        # Transaction errors
        "insufficient_funds": {
            "message": "Testnet account low on funds. Need more KSM for transactions.",
            "action": "Get testnet KSM from https://faucet.parity.io/",
            "severity": "high",
        },
        "transaction_failed": {
            "message": "Transaction failed. This is normal - retrying with adjusted fees.",
            "action": "Automatic retry in progress. No action needed.",
            "severity": "low",
        },
        "transaction_rejected": {
            "message": "Transaction rejected by network. Fee too low or network congestion.",
            "action": "Retrying with higher fee automatically.",
            "severity": "medium",
        },
        # DNA/Validation errors
        "dna_parse_error": {
            "message": "DNA configuration file has formatting issues.",
            "action": "Check YAML syntax in borg_dna.yaml file.",
            "severity": "medium",
        },
        "dna_validation_failed": {
            "message": "DNA structure validation failed.",
            "action": "Review DNA configuration for required fields.",
            "severity": "medium",
        },
        "dna_integrity_check_failed": {
            "message": "DNA integrity verification failed after storage.",
            "action": "Check blockchain connection and retry demo.",
            "severity": "high",
        },
        # Task execution errors
        "task_execution_timeout": {
            "message": "Task took too long to execute.",
            "action": "Task will be retried. Check task complexity.",
            "severity": "medium",
        },
        "task_invalid": {
            "message": "Task description contains invalid or harmful content.",
            "action": "Review task description and try again.",
            "severity": "high",
        },
        # System errors
        "memory_error": {
            "message": "System running low on memory.",
            "action": "Close other applications and try again.",
            "severity": "medium",
        },
        "disk_space_low": {
            "message": "Low disk space available.",
            "action": "Free up disk space and try again.",
            "severity": "high",
        },
        # Security/compliance errors
        "security_violation": {
            "message": "Security policy violation detected.",
            "action": "Operation blocked for security reasons.",
            "severity": "high",
        },
        "budget_exceeded": {
            "message": "Demo budget limit exceeded.",
            "action": "Reset budget or reduce operation frequency.",
            "severity": "high",
        },
        "ethical_violation": {
            "message": "Operation violates ethical guidelines.",
            "action": "Review Universal Principles and modify operation.",
            "severity": "high",
        },
    }

    def __init__(self):
        self.error_history = []

    def get_user_message(
        self,
        error_code: str,
        technical_details: str = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Get user-friendly error message for error code"""
        result = {
            "error_code": error_code,
            "user_message": "",
            "action_required": "",
            "severity": "medium",
            "technical_details": technical_details,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
            "suggestions": [],
        }

        # Get base message
        if error_code in self.ERROR_MESSAGES:
            error_info = self.ERROR_MESSAGES[error_code]
            result["user_message"] = error_info["message"]
            result["action_required"] = error_info["action"]
            result["severity"] = error_info["severity"]
        else:
            # Generic message for unknown errors
            result["user_message"] = "An unexpected error occurred."
            result["action_required"] = "Check logs for details and try again."
            result["severity"] = "medium"

        # Add contextual suggestions
        result["suggestions"] = self._get_contextual_suggestions(error_code, context)

        # Log error for analysis
        self.error_history.append(
            {
                "timestamp": result["timestamp"],
                "error_code": error_code,
                "severity": result["severity"],
                "user_message": result["user_message"],
            }
        )

        return result

    def _get_contextual_suggestions(
        self, error_code: str, context: Dict[str, Any]
    ) -> list:
        """Get contextual suggestions based on error and context"""
        suggestions = []

        if error_code == "insufficient_funds":
            suggestions.extend(
                [
                    "Visit https://faucet.parity.io/ for free testnet KSM",
                    "Check current balance on https://westend.subscan.io/",
                    "Reduce demo frequency to conserve funds",
                ]
            )

        elif error_code == "network_timeout":
            suggestions.extend(
                [
                    "Check internet connection stability",
                    "Try running demo during off-peak hours",
                    "Consider using a different network connection",
                ]
            )

        elif error_code == "dna_parse_error":
            suggestions.extend(
                [
                    "Validate YAML syntax with online YAML validator",
                    "Check for special characters in DNA file",
                    "Ensure proper indentation in YAML structure",
                ]
            )

        elif error_code == "transaction_failed":
            suggestions.extend(
                [
                    "Transaction will retry automatically with higher fee",
                    "Monitor network congestion on blockchain explorer",
                    "Consider waiting for network congestion to decrease",
                ]
            )

        elif error_code == "budget_exceeded":
            suggestions.extend(
                [
                    "Check current spending with budget status command",
                    "Reset budget for new testing period",
                    "Reduce operation frequency or complexity",
                ]
            )

        # Add general suggestions for high severity errors
        if self.ERROR_MESSAGES.get(error_code, {}).get("severity") == "high":
            suggestions.append("Contact support if issue persists")
            suggestions.append("Check demo logs for additional details")

        return suggestions

    def format_error_display(self, error_result: Dict[str, Any]) -> str:
        """Format error for user display"""
        severity_icon = {"low": "ℹ️", "medium": "⚠️", "high": "🚨"}.get(
            error_result["severity"], "❓"
        )

        display = f"""
{severity_icon} **{error_result['user_message']}**

**Recommended Action:** {error_result['action_required']}
"""

        if error_result["suggestions"]:
            display += "\n**Suggestions:**\n"
            for suggestion in error_result["suggestions"]:
                display += f"• {suggestion}\n"

        if error_result["technical_details"]:
            display += f"\n**Technical Details:** {error_result['technical_details']}"

        return display.strip()

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for monitoring"""
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)

        recent_errors = [
            error
            for error in self.error_history
            if datetime.fromisoformat(error["timestamp"]).timestamp() > cutoff_time
        ]

        # Count by severity
        severity_counts = {"low": 0, "medium": 0, "high": 0}
        error_codes = {}

        for error in recent_errors:
            severity_counts[error["severity"]] = (
                severity_counts.get(error["severity"], 0) + 1
            )
            error_codes[error["error_code"]] = (
                error_codes.get(error["error_code"], 0) + 1
            )

        return {
            "total_errors": len(recent_errors),
            "severity_breakdown": severity_counts,
            "common_errors": sorted(
                error_codes.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "time_period_hours": hours,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def clear_error_history(self, days_to_keep: int = 7):
        """Clear old error history"""
        cutoff_time = datetime.utcnow().timestamp() - (days_to_keep * 24 * 3600)

        self.error_history = [
            error
            for error in self.error_history
            if datetime.fromisoformat(error["timestamp"]).timestamp() > cutoff_time
        ]
