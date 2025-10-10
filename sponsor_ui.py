#!/usr/bin/env python3
"""
Sponsor UI and Monitoring Dashboard for Borglife Phase 1 Prototype

Streamlit-based interface for DNA design, bounty posting, sponsorship, and borg monitoring.
"""

import streamlit as st
import json
from pathlib import Path
from dna_system import DNAMapper, BorgPhenotype
from on_chain import KusamaStorage, BorgWealthManager
from proto_borg import ProtoBorgAgent, BorgConfig

# Initialize components
mapper = DNAMapper()
storage = KusamaStorage()

st.set_page_config(page_title="Borglife Prototype", page_icon="🤖", layout="wide")

st.title("🤖 Borglife Phase 1 Prototype")
st.markdown("Decentralized compute platform for autonomous digital life")

# Sidebar for navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["Dashboard", "DNA Designer", "Bounty Manager", "Borg Monitor", "Logs"]
)

if page == "Dashboard":
    st.header("Dashboard")
    st.markdown("Welcome to the Borglife prototype. Create and monitor borgs autonomously.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Borgs", "1")
    with col2:
        st.metric("Total Bounties", "0")
    with col3:
        st.metric("Network Wealth", "0 DOT")

elif page == "DNA Designer":
    st.header("DNA Designer")
    st.markdown("Design borg DNA by configuring cells and organs.")

    with st.form("dna_form"):
        borg_name = st.text_input("Borg Name", "ProtoBorg-001")
        service_index = st.number_input("Service Index", 1, 100, 1)

        st.subheader("Cells (Logic Units)")
        cell_name = st.text_input("Cell Name", "data_processor")
        cell_logic = st.text_area("Cell Logic Description", "Summarize input text")

        st.subheader("Organs (MCP Servers)")
        organ_url = st.text_input("Organ URL", "http://localhost:8051")
        organ_price = st.number_input("Price (DOT)", 0.0, 10.0, 0.01)

        submitted = st.form_submit_button("Create DNA")

        if submitted:
            phenotype = BorgPhenotype(
                name=borg_name,
                config={"service_index": service_index, "gas_limits": {"max_gas": 1000000}},
                cells=[{"name": cell_name, "logic": cell_logic}],
                organs=[{"url": organ_url, "price": organ_price}],
                manifesto_hash=mapper.manifesto_hash
            )

            yaml_dna = mapper.encode_to_yaml(phenotype)
            st.code(yaml_dna, language="yaml")

            # Save DNA
            filename = f"{borg_name.lower().replace(' ', '_')}_dna.yaml"
            mapper.save_dna(phenotype, filename)
            st.success(f"DNA saved to {filename}")

            # Store hash on-chain (mock)
            dna_hash = storage.store_dna_hash(yaml_dna, "mock_address")
            st.info(f"DNA hash stored: {dna_hash}")

elif page == "Bounty Manager":
    st.header("Bounty Manager")
    st.markdown("Post bounties and manage sponsorships.")

    with st.form("bounty_form"):
        bounty_description = st.text_area("Bounty Description", "Process this dataset...")
        reward_amount = st.number_input("Reward (DOT)", 0.1, 100.0, 1.0)
        borg_address = st.text_input("Target Borg Address", "mock_borg_address")

        submitted = st.form_submit_button("Post Bounty")

        if submitted:
            # Mock bounty posting
            bounty = {
                "description": bounty_description,
                "reward": reward_amount,
                "borg_address": borg_address,
                "status": "posted"
            }
            st.json(bounty)
            st.success("Bounty posted successfully!")

elif page == "Borg Monitor":
    st.header("Borg Monitor")
    st.markdown("Monitor borg wealth, tasks, and performance.")

    borg_address = st.text_input("Borg Address", "mock_borg_address")

    if st.button("Refresh Data"):
        # Mock wealth data
        wealth_manager = BorgWealthManager(storage, borg_address)
        wealth_manager.sync_with_chain()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Wealth Status")
            st.json(wealth_manager.local_wealth)

        with col2:
            st.subheader("Recent Transactions")
            # Mock transactions
            transactions = [
                {"type": "task", "amount": -0.001, "description": "Data processing"},
                {"type": "sponsorship", "amount": 1.0, "description": "Bounty reward"}
            ]
            st.json(transactions)

elif page == "Logs":
    st.header("System Logs")
    st.markdown("View borg activity logs.")

    log_file = Path("borg_logs.jsonl")
    if log_file.exists():
        with open(log_file, 'r') as f:
            logs = [json.loads(line) for line in f.readlines()[-10:]]  # Last 10 entries

        for log in logs:
            st.json(log)
    else:
        st.info("No logs available yet.")

# Footer
st.markdown("---")
st.markdown("Built for Borglife Phase 1 Prototype | [Whitepaper](../borglife_whitepaper/borglife-whitepaper.md)")

if __name__ == "__main__":
    # Run with: streamlit run sponsor_ui.py
    pass