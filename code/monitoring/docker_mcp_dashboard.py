import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


@dataclass
class OrganHealthMetrics:
    """Health metrics for a Docker MCP organ"""

    name: str
    status: str  # 'healthy', 'unhealthy', 'unknown'
    uptime_percentage: float
    avg_response_time: float
    error_rate: float
    current_load: int  # concurrent requests
    rate_limit_usage: float  # percentage used
    version: str
    compatible: bool
    update_available: bool
    recommended_version: Optional[str]
    last_checked: datetime


class DockerMCPHealthDashboard:
    """Real-time health dashboard for Docker MCP organs"""

    def __init__(self, monitor, rate_limiter, compatibility_matrix):
        self.monitor = monitor
        self.rate_limiter = rate_limiter
        self.compatibility_matrix = compatibility_matrix
        self.metrics_cache = {}
        self.cache_ttl = timedelta(seconds=30)  # Cache for 30 seconds

    async def get_all_organ_metrics(self) -> Dict[str, OrganHealthMetrics]:
        """Get comprehensive health metrics for all organs"""
        now = datetime.utcnow()

        # Check cache
        if (
            hasattr(self, "_last_cache_update")
            and now - self._last_cache_update < self.cache_ttl
            and self.metrics_cache
        ):
            return self.metrics_cache

        # Get discovered organs
        discovered_organs = await self.monitor.discover_mcp_containers()

        metrics = {}
        for organ_name, organ_info in discovered_organs.items():
            # Health check
            is_healthy = await self.monitor.check_organ_health(
                organ_name, organ_info["endpoint"]
            )

            # Get uptime from history
            uptime = self.monitor.get_organ_uptime(organ_name)

            # Get performance metrics (would come from monitoring system)
            avg_response_time = organ_info.get("avg_response_time", 0.0)
            error_rate = organ_info.get("error_rate", 0.0)
            current_load = organ_info.get("current_load", 0)

            # Rate limit status (simplified - would need borg context)
            rate_limit_usage = 0.0  # Percentage used in current window

            # Compatibility info
            compatible = organ_info.get("compatible", True)
            update_available = organ_info.get("update_available", False)
            recommended_version = organ_info.get("recommended_version")

            metrics[organ_name] = OrganHealthMetrics(
                name=organ_name,
                status="healthy" if is_healthy else "unhealthy",
                uptime_percentage=uptime,
                avg_response_time=avg_response_time,
                error_rate=error_rate,
                current_load=current_load,
                rate_limit_usage=rate_limit_usage,
                version=organ_info.get("version", "unknown"),
                compatible=compatible,
                update_available=update_available,
                recommended_version=recommended_version,
                last_checked=now,
            )

        # Update cache
        self.metrics_cache = metrics
        self._last_cache_update = now

        return metrics

    def render_health_overview(self, metrics: Dict[str, OrganHealthMetrics]):
        """Render overall health overview cards"""
        st.header("🔍 Docker MCP Organ Health Dashboard")

        # Summary metrics
        total_organs = len(metrics)
        healthy_organs = sum(1 for m in metrics.values() if m.status == "healthy")
        unhealthy_organs = total_organs - healthy_organs

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Organs", total_organs)

        with col2:
            st.metric(
                "Healthy",
                healthy_organs,
                delta=(
                    f"{healthy_organs/total_organs*100:.1f}%"
                    if total_organs > 0
                    else "0%"
                ),
            )

        with col3:
            st.metric("Unhealthy", unhealthy_organs)

        with col4:
            avg_uptime = (
                sum(m.uptime_percentage for m in metrics.values()) / total_organs
                if total_organs > 0
                else 0
            )
            st.metric("Avg Uptime", f"{avg_uptime:.1f}%")

    def render_organ_status_table(self, metrics: Dict[str, OrganHealthMetrics]):
        """Render detailed organ status table"""
        st.subheader("Organ Status Details")

        # Prepare data for table
        table_data = []
        for organ in metrics.values():
            status_icon = "✅" if organ.status == "healthy" else "❌"
            compatibility_icon = "✅" if organ.compatible else "❌"
            update_icon = "⬆️" if organ.update_available else "✅"

            table_data.append(
                {
                    "Organ": organ.name,
                    "Status": f"{status_icon} {organ.status.title()}",
                    "Uptime": f"{organ.uptime_percentage:.1f}%",
                    "Avg Response": f"{organ.avg_response_time:.0f}ms",
                    "Error Rate": f"{organ.error_rate:.1f}%",
                    "Load": organ.current_load,
                    "Rate Limit": f"{organ.rate_limit_usage:.1f}%",
                    "Version": organ.version,
                    "Compatible": compatibility_icon,
                    "Updates": update_icon,
                }
            )

        if table_data:
            st.dataframe(table_data, use_container_width=True)
        else:
            st.warning("No organ metrics available")

    def render_performance_charts(self, metrics: Dict[str, OrganHealthMetrics]):
        """Render performance visualization charts"""
        st.subheader("Performance Analytics")

        if not metrics:
            st.warning("No metrics data available")
            return

        # Uptime chart
        uptime_data = {name: m.uptime_percentage for name, m in metrics.items()}
        fig_uptime = px.bar(
            x=list(uptime_data.keys()),
            y=list(uptime_data.values()),
            title="Organ Uptime Percentage",
            labels={"x": "Organ", "y": "Uptime %"},
            color=list(uptime_data.values()),
            color_continuous_scale="RdYlGn",
        )
        st.plotly_chart(fig_uptime, use_container_width=True)

        # Response time chart
        response_data = {name: m.avg_response_time for name, m in metrics.items()}
        fig_response = px.bar(
            x=list(response_data.keys()),
            y=list(response_data.values()),
            title="Average Response Time",
            labels={"x": "Organ", "y": "Response Time (ms)"},
            color=list(response_data.values()),
            color_continuous_scale="RdYlGn_r",  # Reversed for lower=better
        )
        st.plotly_chart(fig_response, use_container_width=True)

    def render_compatibility_status(self, metrics: Dict[str, OrganHealthMetrics]):
        """Render compatibility and update status"""
        st.subheader("Compatibility & Updates")

        # Compatibility summary
        compatible = sum(1 for m in metrics.values() if m.compatible)
        total = len(metrics)

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Compatible Organs", f"{compatible}/{total}")

        with col2:
            updates_available = sum(1 for m in metrics.values() if m.update_available)
            st.metric("Updates Available", updates_available)

        # Update recommendations
        updates_needed = [
            (name, m.recommended_version)
            for name, m in metrics.items()
            if m.update_available and m.recommended_version
        ]

        if updates_needed:
            st.subheader("Recommended Updates")
            for organ_name, recommended_version in updates_needed:
                st.info(f"⬆️ {organ_name}: Update to v{recommended_version}")

        # Compatibility issues
        incompatible_organs = [name for name, m in metrics.items() if not m.compatible]

        if incompatible_organs:
            st.subheader("Compatibility Issues")
            st.error(f"❌ Incompatible organs: {', '.join(incompatible_organs)}")
            st.warning(
                "These organs may not work correctly with current Borglife version"
            )

    async def render_dashboard(self):
        """Render complete health dashboard"""
        # Get metrics
        with st.spinner("Loading organ health metrics..."):
            metrics = await self.get_all_organ_metrics()

        if not metrics:
            st.error("No Docker MCP organs discovered. Please check container status.")
            return

        # Render sections
        self.render_health_overview(metrics)
        st.divider()
        self.render_organ_status_table(metrics)
        st.divider()
        self.render_performance_charts(metrics)
        st.divider()
        self.render_compatibility_status(metrics)

        # Auto-refresh
        st.empty()
        time_to_refresh = 30 - (datetime.utcnow().second % 30)
        st.caption(f"Dashboard auto-refreshes in {time_to_refresh} seconds")

        # Force refresh button
        if st.button("🔄 Refresh Now"):
            st.rerun()
