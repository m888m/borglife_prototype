"""
Production Metrics Collector for BorgLife Demo
Production-grade metrics collection with Prometheus support and alerting.
"""

import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProductionMetricsCollector:
    """Production-grade metrics collection"""

    def __init__(
        self,
        metrics_backend: str = "jsonl",
        metrics_file: str = "code/jam_mock/metrics/demo_metrics.jsonl",
    ):
        self.metrics_backend = metrics_backend
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize metrics
        self.metrics = {
            "demo_runs_total": 0,
            "demo_success_rate": 0.0,
            "average_execution_time": 0.0,
            "total_cost_kusama": Decimal("0"),
            "error_rate_by_type": {},
            "step_execution_times": {},
            "network_performance": {},
            "resource_usage": {},
        }

        # Load existing metrics
        self._load_metrics()

    def _load_metrics(self):
        """Load existing metrics from storage"""
        try:
            if self.metrics_file.exists():
                # For JSONL, read last entry to get current state
                with open(self.metrics_file, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        self.metrics.update(last_entry.get("current_metrics", {}))
        except Exception as e:
            print(f"Failed to load metrics: {e}")

    def _save_metrics(self):
        """Save current metrics to storage"""
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "current_metrics": self.metrics.copy(),
            }

            with open(self.metrics_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Failed to save metrics: {e}")

    async def record_demo_run(
        self,
        success: bool,
        duration: float,
        cost: Decimal,
        steps_data: Dict[str, Any] = None,
    ) -> bool:
        """Record comprehensive demo metrics"""
        try:
            # Update counters
            self.metrics["demo_runs_total"] += 1

            # Update success rate
            total_runs = self.metrics["demo_runs_total"]
            successful_runs = (
                int(total_runs * (self.metrics["demo_success_rate"] / 100))
                if total_runs > 1
                else 0
            )
            if success:
                successful_runs += 1
            self.metrics["demo_success_rate"] = (successful_runs / total_runs) * 100

            # Update average execution time (rolling average)
            current_avg = self.metrics["average_execution_time"]
            self.metrics["average_execution_time"] = (
                (current_avg * (total_runs - 1)) + duration
            ) / total_runs

            # Update total cost
            self.metrics["total_cost_kusama"] += cost

            # Record step data if provided
            if steps_data:
                self._record_step_metrics(steps_data)

            # Save metrics
            self._save_metrics()

            print(
                f"📊 Metrics recorded: Run {total_runs}, Success: {success}, "
                f"Duration: {duration:.1f}s, Cost: {cost}"
            )

            return True
        except Exception as e:
            print(f"Failed to record demo metrics: {e}")
            return False

    def _record_step_metrics(self, steps_data: Dict[str, Any]):
        """Record detailed step execution metrics"""
        for step_name, step_info in steps_data.items():
            if step_name not in self.metrics["step_execution_times"]:
                self.metrics["step_execution_times"][step_name] = []

            duration = step_info.get("duration", 0)
            self.metrics["step_execution_times"][step_name].append(duration)

            # Keep only last 100 measurements to prevent unbounded growth
            if len(self.metrics["step_execution_times"][step_name]) > 100:
                self.metrics["step_execution_times"][step_name] = self.metrics[
                    "step_execution_times"
                ][step_name][-100:]

    def record_error(self, error_type: str, details: str = ""):
        """Record error occurrence"""
        if error_type not in self.metrics["error_rate_by_type"]:
            self.metrics["error_rate_by_type"][error_type] = 0

        self.metrics["error_rate_by_type"][error_type] += 1
        self._save_metrics()

    def record_network_performance(
        self, endpoint: str, response_time: float, success: bool
    ):
        """Record network performance metrics"""
        if endpoint not in self.metrics["network_performance"]:
            self.metrics["network_performance"][endpoint] = {
                "total_requests": 0,
                "successful_requests": 0,
                "average_response_time": 0.0,
                "response_times": [],
            }

        perf = self.metrics["network_performance"][endpoint]
        perf["total_requests"] += 1
        if success:
            perf["successful_requests"] += 1

        # Update rolling average response time
        current_avg = perf["average_response_time"]
        total_requests = perf["total_requests"]
        perf["average_response_time"] = (
            (current_avg * (total_requests - 1)) + response_time
        ) / total_requests

        # Keep response time history
        perf["response_times"].append(response_time)
        if len(perf["response_times"]) > 50:
            perf["response_times"] = perf["response_times"][-50:]

        self._save_metrics()

    def record_resource_usage(
        self,
        cpu_percent: float = None,
        memory_mb: float = None,
        disk_usage: float = None,
    ):
        """Record system resource usage"""
        if "current" not in self.metrics["resource_usage"]:
            self.metrics["resource_usage"]["current"] = {}

        current = self.metrics["resource_usage"]["current"]

        if cpu_percent is not None:
            current["cpu_percent"] = cpu_percent
        if memory_mb is not None:
            current["memory_mb"] = memory_mb
        if disk_usage is not None:
            current["disk_usage"] = disk_usage

        current["timestamp"] = datetime.utcnow().isoformat()
        self._save_metrics()

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        return self.metrics.copy()

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Read recent metrics entries
            recent_entries = []
            if self.metrics_file.exists():
                with open(self.metrics_file, "r") as f:
                    for line in f:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"])
                        if entry_time >= cutoff_time:
                            recent_entries.append(entry)

            if not recent_entries:
                return {"error": "No metrics data available for the specified period"}

            # Calculate summary
            summary = {
                "period_hours": hours,
                "total_runs": len(recent_entries),
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "total_cost": Decimal("0"),
                "generated_at": datetime.utcnow().isoformat(),
            }

            successful_runs = 0
            total_duration = 0
            total_cost = Decimal("0")

            for entry in recent_entries:
                metrics = entry.get("current_metrics", {})

                # Count successful runs (rough approximation)
                success_rate = metrics.get("demo_success_rate", 0)
                if success_rate > 50:  # Assume success if rate > 50%
                    successful_runs += 1

                total_duration += metrics.get("average_execution_time", 0)
                total_cost += Decimal(str(metrics.get("total_cost_kusama", "0")))

            if recent_entries:
                summary["success_rate"] = (successful_runs / len(recent_entries)) * 100
                summary["avg_execution_time"] = total_duration / len(recent_entries)
                summary["total_cost"] = str(total_cost)

            return summary

        except Exception as e:
            return {"error": f"Failed to generate performance summary: {e}"}

    def generate_alerts(self) -> List[Dict[str, Any]]:
        """Generate alerts based on current metrics"""
        alerts = []

        # Success rate alert
        success_rate = self.metrics.get("demo_success_rate", 100)
        if success_rate < 95:
            alerts.append(
                {
                    "type": "success_rate",
                    "severity": "high" if success_rate < 80 else "medium",
                    "message": f"Demo success rate is {success_rate:.1f}%, below 95% threshold",
                    "current_value": success_rate,
                    "threshold": 95.0,
                }
            )

        # Performance degradation alert
        avg_time = self.metrics.get("average_execution_time", 0)
        if avg_time > 10:  # More than 10 seconds
            alerts.append(
                {
                    "type": "performance",
                    "severity": "medium",
                    "message": f"Average execution time {avg_time:.1f}s exceeds 10s threshold",
                    "current_value": avg_time,
                    "threshold": 10.0,
                }
            )

        # High error rate alert
        total_runs = self.metrics.get("demo_runs_total", 0)
        if total_runs > 0:
            error_rate = (
                sum(self.metrics.get("error_rate_by_type", {}).values())
                / total_runs
                * 100
            )
            if error_rate > 20:
                alerts.append(
                    {
                        "type": "error_rate",
                        "severity": "high",
                        "message": f"Error rate is {error_rate:.1f}%, above 20% threshold",
                        "current_value": error_rate,
                        "threshold": 20.0,
                    }
                )

        return alerts

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        if format == "json":
            return json.dumps(self.metrics, indent=2, default=str)
        elif format == "prometheus":
            return self._export_prometheus_format()
        else:
            return json.dumps(self.metrics, default=str)

    def _export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        # Gauge metrics
        lines.append(f"# HELP borglife_demo_runs_total Total number of demo runs")
        lines.append(f"# TYPE borglife_demo_runs_total gauge")
        lines.append(f'borglife_demo_runs_total {self.metrics["demo_runs_total"]}')

        lines.append(f"# HELP borglife_demo_success_rate Demo success rate percentage")
        lines.append(f"# TYPE borglife_demo_success_rate gauge")
        lines.append(f'borglife_demo_success_rate {self.metrics["demo_success_rate"]}')

        lines.append(
            f"# HELP borglife_demo_avg_execution_time Average execution time in seconds"
        )
        lines.append(f"# TYPE borglife_demo_avg_execution_time gauge")
        lines.append(
            f'borglife_demo_avg_execution_time {self.metrics["average_execution_time"]}'
        )

        # Counter metrics
        lines.append(f"# HELP borglife_demo_total_cost Total cost in KSM")
        lines.append(f"# TYPE borglife_demo_total_cost counter")
        lines.append(f'borglife_demo_total_cost {self.metrics["total_cost_kusama"]}')

        return "\n".join(lines)
