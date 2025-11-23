"""
Alert Manager for BorgLife Demo
Manage alerts for demo operations with configurable thresholds and notifications.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class DemoAlertManager:
    """Manage alerts for demo operations"""

    DEFAULT_THRESHOLDS = {
        "low_balance": {"threshold": 0.1, "severity": "high"},  # KSM
        "success_rate": {"threshold": 95.0, "severity": "high"},  # percentage
        "execution_time": {"threshold": 10.0, "severity": "medium"},  # seconds
        "error_rate": {"threshold": 20.0, "severity": "high"},  # percentage
        "network_timeout": {"threshold": 30.0, "severity": "medium"},  # seconds
        "memory_usage": {"threshold": 90.0, "severity": "medium"},  # percentage
        "disk_usage": {"threshold": 95.0, "severity": "high"},  # percentage
    }

    def __init__(
        self,
        alert_file: str = "code/jam_mock/alerts/demo_alerts.jsonl",
        thresholds: Dict[str, Dict] = None,
    ):
        self.alert_file = Path(alert_file)
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()
        self.active_alerts = []
        self.alert_callbacks = []

    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)

    async def check_alerts(
        self, metrics: Dict[str, Any] = None, system_status: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Check for alert conditions and return active alerts"""
        alerts = []

        # Check balance alerts
        if system_status and "balance" in system_status:
            balance_alert = self._check_balance_alert(system_status["balance"])
            if balance_alert:
                alerts.append(balance_alert)

        # Check success rate alerts
        if metrics and "demo_success_rate" in metrics:
            success_alert = self._check_success_rate_alert(metrics["demo_success_rate"])
            if success_alert:
                alerts.append(success_alert)

        # Check performance alerts
        if metrics and "average_execution_time" in metrics:
            perf_alert = self._check_performance_alert(
                metrics["average_execution_time"]
            )
            if perf_alert:
                alerts.append(perf_alert)

        # Check error rate alerts
        if metrics and "error_rate_by_type" in metrics:
            error_alert = self._check_error_rate_alert(metrics)
            if error_alert:
                alerts.append(error_alert)

        # Check system resource alerts
        if system_status:
            resource_alerts = self._check_resource_alerts(system_status)
            alerts.extend(resource_alerts)

        # Update active alerts
        self._update_active_alerts(alerts)

        # Trigger callbacks for new alerts
        for alert in alerts:
            if alert not in self.active_alerts:
                self._trigger_alert_callbacks(alert)

        return alerts

    def _check_balance_alert(self, balance: float) -> Optional[Dict[str, Any]]:
        """Check for low balance alerts"""
        threshold = self.thresholds["low_balance"]["threshold"]
        if balance < threshold:
            return {
                "type": "low_balance",
                "severity": self.thresholds["low_balance"]["severity"],
                "message": f"Testnet balance {balance} KSM below threshold {threshold} KSM",
                "current_value": balance,
                "threshold": threshold,
                "recommendation": "Get more testnet KSM from faucet or reduce demo frequency",
                "timestamp": datetime.utcnow().isoformat(),
            }
        return None

    def _check_success_rate_alert(
        self, success_rate: float
    ) -> Optional[Dict[str, Any]]:
        """Check for success rate alerts"""
        threshold = self.thresholds["success_rate"]["threshold"]
        if success_rate < threshold:
            severity = "high" if success_rate < 80 else "medium"
            return {
                "type": "success_rate",
                "severity": severity,
                "message": f"Demo success rate {success_rate:.1f}% below threshold {threshold}%",
                "current_value": success_rate,
                "threshold": threshold,
                "recommendation": "Check error logs and fix underlying issues",
                "timestamp": datetime.utcnow().isoformat(),
            }
        return None

    def _check_performance_alert(self, avg_time: float) -> Optional[Dict[str, Any]]:
        """Check for performance degradation alerts"""
        threshold = self.thresholds["execution_time"]["threshold"]
        if avg_time > threshold:
            return {
                "type": "performance",
                "severity": self.thresholds["execution_time"]["severity"],
                "message": f"Average execution time {avg_time:.1f}s exceeds threshold {threshold}s",
                "current_value": avg_time,
                "threshold": threshold,
                "recommendation": "Optimize demo performance or check network conditions",
                "timestamp": datetime.utcnow().isoformat(),
            }
        return None

    def _check_error_rate_alert(
        self, metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for high error rate alerts"""
        error_counts = metrics.get("error_rate_by_type", {})
        total_runs = metrics.get("demo_runs_total", 0)

        if total_runs == 0:
            return None

        total_errors = sum(error_counts.values())
        error_rate = (total_errors / total_runs) * 100
        threshold = self.thresholds["error_rate"]["threshold"]

        if error_rate > threshold:
            # Get most common error types
            common_errors = sorted(
                error_counts.items(), key=lambda x: x[1], reverse=True
            )[:3]

            return {
                "type": "error_rate",
                "severity": self.thresholds["error_rate"]["severity"],
                "message": f"Error rate {error_rate:.1f}% exceeds threshold {threshold}%",
                "current_value": error_rate,
                "threshold": threshold,
                "common_errors": common_errors,
                "recommendation": "Review error logs and address most frequent error types",
                "timestamp": datetime.utcnow().isoformat(),
            }
        return None

    def _check_resource_alerts(
        self, system_status: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check for system resource alerts"""
        alerts = []

        # Memory usage alert
        if "memory_percent" in system_status:
            mem_threshold = self.thresholds["memory_usage"]["threshold"]
            mem_usage = system_status["memory_percent"]
            if mem_usage > mem_threshold:
                alerts.append(
                    {
                        "type": "memory_usage",
                        "severity": self.thresholds["memory_usage"]["severity"],
                        "message": f"Memory usage {mem_usage:.1f}% exceeds threshold {mem_threshold}%",
                        "current_value": mem_usage,
                        "threshold": mem_threshold,
                        "recommendation": "Close other applications or increase system memory",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

        # Disk usage alert
        if "disk_percent" in system_status:
            disk_threshold = self.thresholds["disk_usage"]["threshold"]
            disk_usage = system_status["disk_percent"]
            if disk_usage > disk_threshold:
                alerts.append(
                    {
                        "type": "disk_usage",
                        "severity": self.thresholds["disk_usage"]["severity"],
                        "message": f"Disk usage {disk_usage:.1f}% exceeds threshold {disk_threshold}%",
                        "current_value": disk_usage,
                        "threshold": disk_threshold,
                        "recommendation": "Free up disk space or add storage",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

        return alerts

    def _update_active_alerts(self, new_alerts: List[Dict[str, Any]]):
        """Update the list of active alerts"""
        # Remove resolved alerts (simple approach - could be enhanced)
        current_alert_types = {alert["type"] for alert in new_alerts}
        self.active_alerts = [
            alert
            for alert in self.active_alerts
            if alert["type"] in current_alert_types
        ]

        # Add new alerts
        for alert in new_alerts:
            if alert not in self.active_alerts:
                self.active_alerts.append(alert)
                self._log_alert(alert)

    def _trigger_alert_callbacks(self, alert: Dict[str, Any]):
        """Trigger registered alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Alert callback error: {e}")

    def _log_alert(self, alert: Dict[str, Any]):
        """Log alert to file"""
        try:
            with open(self.alert_file, "a") as f:
                f.write(json.dumps(alert) + "\n")
        except Exception as e:
            print(f"Failed to log alert: {e}")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        return self.active_alerts.copy()

    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for the last N hours"""
        try:
            if not self.alert_file.exists():
                return []

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            alerts = []

            with open(self.alert_file, "r") as f:
                for line in f:
                    alert = json.loads(line)
                    alert_time = datetime.fromisoformat(alert["timestamp"])
                    if alert_time >= cutoff_time:
                        alerts.append(alert)

            return alerts
        except Exception as e:
            print(f"Failed to read alert history: {e}")
            return []

    def acknowledge_alert(self, alert_type: str) -> bool:
        """Acknowledge an alert (remove from active alerts)"""
        try:
            self.active_alerts = [
                alert for alert in self.active_alerts if alert["type"] != alert_type
            ]
            return True
        except Exception:
            return False

    def update_threshold(
        self, alert_type: str, new_threshold: float, new_severity: str = None
    ) -> bool:
        """Update alert threshold and severity"""
        if alert_type not in self.thresholds:
            return False

        self.thresholds[alert_type]["threshold"] = new_threshold
        if new_severity:
            self.thresholds[alert_type]["severity"] = new_severity

        return True

    def generate_alert_report(self) -> Dict[str, Any]:
        """Generate comprehensive alert report"""
        history = self.get_alert_history(168)  # Last 7 days

        # Count alerts by type and severity
        alert_counts = {}
        severity_counts = {"low": 0, "medium": 0, "high": 0}

        for alert in history:
            alert_type = alert["type"]
            severity = alert["severity"]

            if alert_type not in alert_counts:
                alert_counts[alert_type] = 0
            alert_counts[alert_type] += 1

            severity_counts[severity] += 1

        return {
            "active_alerts": len(self.active_alerts),
            "alerts_last_7_days": len(history),
            "alerts_by_type": alert_counts,
            "alerts_by_severity": severity_counts,
            "most_common_alert": (
                max(alert_counts.items(), key=lambda x: x[1]) if alert_counts else None
            ),
            "generated_at": datetime.utcnow().isoformat(),
        }


# Default alert callback for console output
def console_alert_callback(alert: Dict[str, Any]):
    """Default callback that prints alerts to console"""
    severity_icon = {"low": "ℹ️", "medium": "⚠️", "high": "🚨"}.get(
        alert["severity"], "❓"
    )

    print(f"{severity_icon} ALERT [{alert['type'].upper()}]: {alert['message']}")
    if "recommendation" in alert:
        print(f"   💡 {alert['recommendation']}")
