# borglife_prototype/borg_designer_ui.py
"""
Borg Designer UI - Streamlit interface for creating and testing borg phenotypes.

Provides a visual composer for building borgs from Archon cells and Docker MCP organs,
with real-time testing and cost transparency.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from archon_adapter import ArchonServiceAdapter
from archon_adapter.config import ArchonConfig
from synthesis.dna_parser import BorgDNA, DNAParser
from synthesis.phenotype_builder import PhenotypeBuilder


class BorgDesignerUI:
    """Streamlit-based UI for borg design and testing."""

    def __init__(self):
        self.dna_parser = DNAParser()
        self.adapter = None
        self.builder = None
        self.current_phenotype = None

        # Component libraries
        self.archon_cells = {
            "rag_agent": {
                "name": "RAG Agent",
                "description": "Knowledge retrieval and question answering",
                "category": "Knowledge",
                "cost_per_call": 0.001,
                "parameters": {"model": "gpt-4", "max_tokens": 500},
            },
            "document_agent": {
                "name": "Document Agent",
                "description": "Document analysis and processing",
                "category": "Analysis",
                "cost_per_call": 0.001,
                "parameters": {"model": "gpt-4", "max_tokens": 500},
            },
        }

        self.docker_mcp_organs = {
            "gmail": {
                "name": "Gmail Integration",
                "description": "Email operations and management",
                "category": "Communication",
                "cost_per_call": 0.0005,
                "tools": ["send_email", "list_emails", "search_emails"],
                "health_status": "healthy",
            },
            "stripe": {
                "name": "Stripe Payments",
                "description": "Payment processing and subscription management",
                "category": "Finance",
                "cost_per_call": 0.001,
                "tools": ["create_payment", "list_customers", "manage_subscriptions"],
                "health_status": "healthy",
            },
            "mongodb": {
                "name": "MongoDB Connector",
                "description": "Database operations and queries",
                "category": "Data",
                "cost_per_call": 0.0003,
                "tools": ["query", "insert", "update", "delete"],
                "health_status": "healthy",
            },
            "duckduckgo": {
                "name": "Web Search",
                "description": "Privacy-focused web search and information retrieval",
                "category": "Search",
                "cost_per_call": 0.0002,
                "tools": ["search", "news", "images"],
                "health_status": "healthy",
            },
        }

    async def initialize(self):
        """Initialize the adapter and builder."""
        if self.adapter is None:
            config = ArchonConfig()
            self.adapter = ArchonServiceAdapter(config)
            await self.adapter.initialize()
            self.builder = PhenotypeBuilder(self.adapter)

    def render_main_ui(self):
        """Render the main Streamlit UI."""
        st.set_page_config(
            page_title="BorgLife Designer", page_icon="🤖", layout="wide"
        )

        st.title("🤖 BorgLife Designer")
        st.markdown(
            "Create and test autonomous borg phenotypes using Archon cells and Docker MCP organs"
        )

        # Initialize async components
        asyncio.run(self.initialize())

        # Create tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📦 Component Library",
                "🔧 Phenotype Composer",
                "🧪 Test Harness",
                "💰 Cost Analysis",
                "📊 Performance",
            ]
        )

        with tab1:
            self.render_component_library()

        with tab2:
            self.render_phenotype_composer()

        with tab3:
            self.render_test_harness()

        with tab4:
            self.render_cost_analysis()

        with tab5:
            self.render_performance_dashboard()

    def render_component_library(self):
        """Render the component library browser."""
        st.header("📚 Component Library")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🧬 Archon Cells")
            for cell_id, cell_info in self.archon_cells.items():
                with st.expander(f"{cell_info['name']} ({cell_id})"):
                    st.write(f"**Category:** {cell_info['category']}")
                    st.write(f"**Description:** {cell_info['description']}")
                    st.write(f"**Cost per call:** {cell_info['cost_per_call']} DOT")
                    st.write(f"**Parameters:** {cell_info['parameters']}")
                    if st.button(f"Add {cell_id}", key=f"add_cell_{cell_id}"):
                        self.add_component_to_phenotype("cell", cell_id, cell_info)

        with col2:
            st.subheader("🫀 Docker MCP Organs")
            for organ_id, organ_info in self.docker_mcp_organs.items():
                with st.expander(f"{organ_info['name']} ({organ_id})"):
                    st.write(f"**Category:** {organ_info['category']}")
                    st.write(f"**Description:** {organ_info['description']}")
                    st.write(f"**Cost per call:** {organ_info['cost_per_call']} DOT")
                    st.write(f"**Tools:** {', '.join(organ_info['tools'])}")
                    health_color = (
                        "🟢" if organ_info["health_status"] == "healthy" else "🔴"
                    )
                    st.write(
                        f"**Health:** {health_color} {organ_info['health_status']}"
                    )
                    if st.button(f"Add {organ_id}", key=f"add_organ_{organ_id}"):
                        self.add_component_to_phenotype("organ", organ_id, organ_info)

    def render_phenotype_composer(self):
        """Render the phenotype composition interface."""
        st.header("🔧 Phenotype Composer")

        if "phenotype_config" not in st.session_state:
            st.session_state.phenotype_config = {
                "cells": {},
                "organs": {},
                "metadata": {
                    "name": "",
                    "description": "",
                    "service_index": f"borg-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                },
            }

        config = st.session_state.phenotype_config

        # Basic metadata
        col1, col2 = st.columns(2)
        with col1:
            config["metadata"]["name"] = st.text_input(
                "Borg Name",
                value=config["metadata"]["name"],
                placeholder="My Awesome Borg",
            )
        with col2:
            config["metadata"]["description"] = st.text_area(
                "Description",
                value=config["metadata"]["description"],
                placeholder="What does this borg do?",
                height=100,
            )

        # Display current composition
        st.subheader("Current Composition")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Cells:**")
            if config["cells"]:
                for cell_id, cell_info in config["cells"].items():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"• {cell_info['name']} ({cell_id})")
                    with col_b:
                        if st.button("❌", key=f"remove_cell_{cell_id}"):
                            del config["cells"][cell_id]
                            st.rerun()
            else:
                st.write("*No cells added yet*")

        with col2:
            st.write("**Organs:**")
            if config["organs"]:
                for organ_id, organ_info in config["organs"].items():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"• {organ_info['name']} ({organ_id})")
                    with col_b:
                        if st.button("❌", key=f"remove_organ_{organ_id}"):
                            del config["organs"][organ_id]
                            st.rerun()
            else:
                st.write("*No organs added yet*")

        # Build phenotype button
        if st.button("🔨 Build Phenotype", type="primary"):
            asyncio.run(self.build_phenotype_from_config())

    def render_test_harness(self):
        """Render the testing interface."""
        st.header("🧪 Test Harness")

        if self.current_phenotype is None:
            st.warning("Please build a phenotype first in the Composer tab.")
            return

        st.success("✅ Phenotype loaded and ready for testing")

        # Test input
        test_task = st.text_area(
            "Test Task",
            placeholder="Describe what you want the borg to do...",
            help="Enter a task for the borg to execute using its cells and organs",
        )

        # Mock wealth for testing
        test_wealth = st.number_input(
            "Test Wealth (DOT)",
            value=1.0,
            min_value=0.0,
            step=0.1,
            help="Simulated wealth for cost calculations",
        )

        if st.button("🚀 Execute Task", type="primary") and test_task:
            with st.spinner("Executing task..."):
                result = asyncio.run(self.execute_test_task(test_task, test_wealth))

            # Display results
            self.display_test_results(result)

    def render_cost_analysis(self):
        """Render cost analysis and transparency."""
        st.header("💰 Cost Analysis")

        if self.current_phenotype is None:
            st.warning("Please build a phenotype first.")
            return

        # Cost breakdown
        st.subheader("Estimated Costs")

        total_cell_cost = sum(
            cell["cost_per_call"] for cell in self.current_phenotype.cells.values()
        )
        total_organ_cost = sum(
            organ["cost_per_call"] for organ in self.current_phenotype.organs.values()
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Cell Costs", f"{total_cell_cost:.6f} DOT/call")

        with col2:
            st.metric("Organ Costs", f"{total_organ_cost:.6f} DOT/call")

        with col3:
            st.metric(
                "Total Estimated", f"{total_cell_cost + total_organ_cost:.6f} DOT/call"
            )

        # Cost visualization
        if total_cell_cost > 0 or total_organ_cost > 0:
            fig = go.Figure(
                data=[
                    go.Bar(
                        name="Cells",
                        x=["Cells", "Organs"],
                        y=[total_cell_cost, total_organ_cost],
                    )
                ]
            )
            fig.update_layout(title="Cost Breakdown", yaxis_title="DOT per call")
            st.plotly_chart(fig)

    def render_performance_dashboard(self):
        """Render performance metrics and analytics."""
        st.header("📊 Performance Dashboard")

        if "test_history" not in st.session_state:
            st.session_state.test_history = []

        history = st.session_state.test_history

        if not history:
            st.info("No test results yet. Run some tests in the Test Harness tab.")
            return

        # Performance metrics
        execution_times = [r["execution_time"] for r in history]
        costs = [float(r["cost_info"]["total_cost"]) for r in history]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Avg Execution Time",
                f"{sum(execution_times)/len(execution_times):.2f}s",
            )

        with col2:
            st.metric("Avg Cost", f"{sum(costs)/len(costs):.6f} DOT")

        with col3:
            st.metric("Total Tests", len(history))

        # Performance chart
        fig = px.scatter(
            x=execution_times,
            y=costs,
            title="Execution Time vs Cost",
            labels={"x": "Execution Time (s)", "y": "Cost (DOT)"},
        )
        st.plotly_chart(fig)

    def add_component_to_phenotype(
        self, component_type: str, component_id: str, component_info: Dict[str, Any]
    ):
        """Add a component to the current phenotype configuration."""
        if "phenotype_config" not in st.session_state:
            st.session_state.phenotype_config = {
                "cells": {},
                "organs": {},
                "metadata": {},
            }

        config = st.session_state.phenotype_config

        if component_type == "cell":
            config["cells"][component_id] = component_info
        elif component_type == "organ":
            config["organs"][component_id] = component_info

        st.success(f"Added {component_info['name']} to phenotype!")

    async def build_phenotype_from_config(self):
        """Build phenotype from current configuration."""
        config = st.session_state.phenotype_config

        if not config["cells"] and not config["organs"]:
            st.error("Please add at least one cell or organ to your phenotype.")
            return

        try:
            with st.spinner("Building phenotype..."):
                # Create DNA from config
                dna = self.create_dna_from_config(config)

                # Build phenotype
                phenotype = await self.builder.build(dna)

                self.current_phenotype = phenotype

            st.success("✅ Phenotype built successfully!")
            st.write(
                f"Built phenotype with {len(phenotype.cells)} cells and {len(phenotype.organs)} organs"
            )

        except Exception as e:
            st.error(f"Failed to build phenotype: {e}")

    def create_dna_from_config(self, config: Dict[str, Any]) -> BorgDNA:
        """Create BorgDNA from UI configuration."""
        from synthesis.dna_parser import Cell, DNAHeader, Organ

        # Create header
        header = DNAHeader(
            code_length=1024,
            gas_limit=1000000,
            service_index=config["metadata"]["service_index"],
        )

        # Create cells
        cells = []
        for cell_id, cell_info in config["cells"].items():
            cell = Cell(
                name=cell_id,
                logic_type=cell_id,
                parameters=cell_info.get("parameters", {}),
                cost_estimate=cell_info.get("cost_per_call", 0.001),
            )
            cells.append(cell)

        # Create organs
        organs = []
        for organ_id, organ_info in config["organs"].items():
            organ = Organ(
                name=organ_id,
                mcp_tool=(
                    organ_info["tools"][0]
                    if organ_info.get("tools")
                    else f"{organ_id}:tool"
                ),
                url=f"http://mcp-{organ_id}:8080",
                abi_version="1.0",
                price_cap=organ_info.get("cost_per_call", 0.001),
            )
            organs.append(organ)

        return BorgDNA(
            header=header,
            cells=cells,
            organs=organs,
            manifesto_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    async def execute_test_task(self, task: str, wealth: float) -> Dict[str, Any]:
        """Execute a test task with the current phenotype."""
        return await self.current_phenotype.execute_task(task, wealth)

    def display_test_results(self, result: Dict[str, Any]):
        """Display test execution results."""
        st.subheader("Test Results")

        # Basic result info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Execution Time", f"{result['execution_time']:.2f}s")
        with col2:
            st.metric("Total Cost", f"{result['cost_info']['total_cost']} DOT")
        with col3:
            wealth_ok = "✅" if result["cost_info"]["wealth_sufficient"] else "❌"
            st.metric("Wealth Sufficient", wealth_ok)

        # Task result
        st.subheader("Task Output")
        if "result" in result and "cell_type" in result["result"]:
            cell_result = result["result"]
            st.write(f"**Cell Type:** {cell_result['cell_type']}")
            if "decision" in cell_result:
                st.write(f"**Decision:** {cell_result['decision']}")
            elif "processed_data" in cell_result:
                st.write(f"**Processed Data:** {cell_result['processed_data']}")
        else:
            st.json(result.get("result", {}))

        # Cost breakdown
        st.subheader("Cost Breakdown")
        cost_info = result["cost_info"]
        st.write(f"**Execution Cost:** {cost_info['execution_cost']} DOT")
        if cost_info["organ_costs"]:
            st.write("**Organ Costs:**")
            for organ, cost in cost_info["organ_costs"].items():
                st.write(f"  - {organ}: {cost} DOT")

        # Add to history
        if "test_history" not in st.session_state:
            st.session_state.test_history = []
        st.session_state.test_history.append(result)


def main():
    """Main entry point for the Streamlit app."""
    ui = BorgDesignerUI()
    ui.render_main_ui()


if __name__ == "__main__":
    main()
