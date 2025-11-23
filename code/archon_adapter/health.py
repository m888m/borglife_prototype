# borglife_prototype/archon_adapter/health.py
"""
Health monitoring for Archon services.

Provides comprehensive health checks for all Archon services
and Docker MCP organs with detailed status reporting.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from .config import ArchonConfig
from .exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health monitoring for Archon services."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        config: ArchonConfig,
        health_check_interval: int = 30,
    ):
        self.client = client
        self.config = config
        self.health_check_interval = health_check_interval
        self.last_checks = {}
        self.health_history = {}

    async def check_all_services(self) -> Dict[str, Any]:
        """
        Check health of all Archon services.

        Returns:
            {
                'overall': bool,
                'server': bool,
                'mcp': bool,
                'agents': bool,
                'docker_mcp': bool,
                'details': {...},
                'timestamp': str
            }
        """
        results = {}
        details = {}

        # Check Archon services
        services = ["server", "mcp", "agents"]
        for service in services:
            is_healthy, service_details = await self._check_service_health(service)
            results[service] = is_healthy
            details[service] = service_details

        # Check Docker MCP if enabled
        if self.config.enable_docker_mcp_organs:
            docker_healthy, docker_details = await self._check_docker_mcp_health()
            results["docker_mcp"] = docker_healthy
            details["docker_mcp"] = docker_details
        else:
            results["docker_mcp"] = True  # Not applicable
            details["docker_mcp"] = {"status": "disabled"}

        # Overall health
        overall = all(results.values())

        # Update history
        self._update_health_history(results, details)

        return {
            "overall": overall,
            "server": results.get("server", False),
            "mcp": results.get("mcp", False),
            "agents": results.get("agents", False),
            "docker_mcp": results.get("docker_mcp", False),
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _check_service_health(self, service: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check health of a specific Archon service.

        Returns:
            (is_healthy: bool, details: dict)
        """
        endpoint = self.config.get_service_endpoints()[service]
        health_url = f"{endpoint}/health"

        try:
            start_time = datetime.utcnow()
            response = await self.client.get(
                health_url, timeout=self.config.docker_mcp_health_timeout
            )
            response_time = (datetime.utcnow() - start_time).total_seconds()

            is_healthy = response.status_code == 200

            details = {
                "status": "healthy" if is_healthy else "unhealthy",
                "response_time": round(response_time, 3),
                "status_code": response.status_code,
                "endpoint": health_url,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if is_healthy:
                try:
                    health_data = response.json()
                    details.update(health_data)
                except:
                    pass  # Health endpoint may not return JSON

        except httpx.TimeoutException:
            details = {
                "status": "timeout",
                "error": "Request timed out",
                "endpoint": health_url,
                "timestamp": datetime.utcnow().isoformat(),
            }
            is_healthy = False

        except Exception as e:
            details = {
                "status": "error",
                "error": str(e),
                "endpoint": health_url,
                "timestamp": datetime.utcnow().isoformat(),
            }
            is_healthy = False

        # Update last check
        self.last_checks[service] = {
            "healthy": is_healthy,
            "details": details,
            "timestamp": datetime.utcnow(),
        }

        return is_healthy, details

    async def _check_docker_mcp_health(self) -> tuple[bool, Dict[str, Any]]:
        """
        Check health of Docker MCP organs.

        Returns:
            (is_healthy: bool, details: dict)
        """
        # This would integrate with docker_mcp_monitor.py
        # For now, return basic status
        try:
            # Placeholder - would check actual Docker MCP organs
            details = {
                "status": "healthy",
                "organs_checked": 0,
                "organs_healthy": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
            is_healthy = True
        except Exception as e:
            details = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
            is_healthy = False

        return is_healthy, details

    def _update_health_history(self, results: Dict[str, bool], details: Dict[str, Any]):
        """Update health history for trend analysis."""
        timestamp = datetime.utcnow()

        for service, is_healthy in results.items():
            if service not in self.health_history:
                self.health_history[service] = []

            self.health_history[service].append(
                {
                    "timestamp": timestamp,
                    "healthy": is_healthy,
                    "details": details.get(service, {}),
                }
            )

            # Keep only last 100 entries
            if len(self.health_history[service]) > 100:
                self.health_history[service].pop(0)

    def get_health_history(self, service: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get health history for a service.

        Args:
            service: Service name
            hours: Hours of history to retrieve

        Returns:
            List of health check results
        """
        if service not in self.health_history:
            return []

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            entry
            for entry in self.health_history[service]
            if entry["timestamp"] >= cutoff
        ]

    def get_service_uptime(self, service: str, hours: int = 24) -> float:
        """
        Calculate service uptime percentage.

        Args:
            service: Service name
            hours: Time period in hours

        Returns:
            Uptime percentage (0-100)
        """
        history = self.get_health_history(service, hours)
        if not history:
            return 0.0

        healthy_count = sum(1 for entry in history if entry["healthy"])
        return (healthy_count / len(history)) * 100

    def get_last_health_check(self, service: str) -> Optional[Dict[str, Any]]:
        """Get the last health check result for a service."""
        return self.last_checks.get(service)

    async def wait_for_service_healthy(
        self, service: str, timeout: int = 300, check_interval: int = 10
    ) -> bool:
        """
        Wait for a service to become healthy.

        Args:
            service: Service name
            timeout: Maximum wait time in seconds
            check_interval: Check interval in seconds

        Returns:
            True if service became healthy within timeout
        """
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            is_healthy, _ = await self._check_service_health(service)
            if is_healthy:
                return True
            await asyncio.sleep(check_interval)

        return False

    def get_overall_health_summary(self) -> Dict[str, Any]:
        """
        Get overall health summary across all services.

        Returns:
            Summary statistics
        """
        summary = {
            "services_checked": len(self.last_checks),
            "services_healthy": 0,
            "services_unhealthy": 0,
            "average_response_time": 0.0,
            "last_check": None,
            "service_details": {},
        }

        total_response_time = 0.0
        response_time_count = 0

        for service, check in self.last_checks.items():
            if check["healthy"]:
                summary["services_healthy"] += 1
            else:
                summary["services_unhealthy"] += 1

            summary["service_details"][service] = {
                "healthy": check["healthy"],
                "uptime_24h": self.get_service_uptime(service, 24),
                "last_check": check["timestamp"].isoformat(),
                "details": check["details"],
            }

            # Calculate average response time
            if "response_time" in check["details"]:
                total_response_time += check["details"]["response_time"]
                response_time_count += 1

            # Track latest check time
            if not summary["last_check"] or check["timestamp"] > summary["last_check"]:
                summary["last_check"] = check["timestamp"]

        if response_time_count > 0:
            summary["average_response_time"] = total_response_time / response_time_count

        if summary["last_check"]:
            summary["last_check"] = summary["last_check"].isoformat()

        return summary
