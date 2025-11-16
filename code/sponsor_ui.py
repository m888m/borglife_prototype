#!/usr/bin/env python3
"""
BorgLife Sponsor UI

Streamlit-based interface for sponsors to:
- Fund borgs with DOT
- Create borgs from DNA
- Submit tasks for execution
- Monitor progress and view results
"""

import streamlit as st
import asyncio
import json
from decimal import Decimal
from typing import Optional, Dict, Any
import time

# Import BorgLife components
from jam_mock import JAMInterface, LocalJAMMock, WestendAdapter
from synthesis import DNAParser, PhenotypeBuilder, BorgDNA
from archon_adapter import ArchonServiceAdapter, ArchonConfig


class SponsorUI:
    """
    Streamlit-based sponsor interface for BorgLife Phase 1.

    Provides complete demo flow: funding → borg creation → task execution → results.
    """

    def __init__(self):
        """Initialize UI components."""
        self.jam: Optional[JAMInterface] = None
        self.archon_adapter: Optional[ArchonServiceAdapter] = None
        self.phenotype_builder: Optional[PhenotypeBuilder] = None
        self.current_borg: Optional[Dict[str, Any]] = None
        self.execution_history: list = []

    def setup_page(self):
        """Configure Streamlit page."""
        st.set_page_config(
            page_title="BorgLife Phase 1 Demo",
            page_icon="🤖",
            layout="wide"
        )

        st.title("🤖 BorgLife Phase 1 Demo")
        st.markdown("*End-to-end demo: funding → execution → encoding → storage → decoding*")

        # Sidebar for configuration
        self.setup_sidebar()

    def setup_sidebar(self):
        """Setup sidebar with configuration and status."""
        st.sidebar.header("⚙️ Configuration")

        # JAM Mode selection
        jam_mode = st.sidebar.selectbox(
            "JAM Mode",
            ["local", "westend", "hybrid"],
            help="Local for development, Westend for production validation"
        )

        # Initialize components based on mode
        if st.sidebar.button("Initialize Services"):
            self.initialize_services(jam_mode)
            st.sidebar.success("Services initialized!")

        # Service status
        if self.jam and self.archon_adapter:
            st.sidebar.header("📊 Service Status")
            self.display_service_status()

    def initialize_services(self, jam_mode: str):
        """Initialize JAM and Archon services."""
        try:
            # Initialize JAM
            if jam_mode == "local":
                self.jam = LocalJAMMock()
            elif jam_mode == "westend":
                # Note: In real implementation, would need keypair from wallet
                westend_adapter = WestendAdapter(rpc_url="wss://westend-rpc.polkadot.io")
                self.jam = westend_adapter
            else:  # hybrid
                self.jam = LocalJAMMock()  # Primary local, could add Westend validation

            # Initialize Archon adapter
            config = ArchonConfig()
            self.archon_adapter = ArchonServiceAdapter(config)
            asyncio.run(self.archon_adapter.initialize())

            # Initialize phenotype builder
            self.phenotype_builder = PhenotypeBuilder(self.archon_adapter)

        except Exception as e:
            st.sidebar.error(f"Initialization failed: {e}")

    def display_service_status(self):
        """Display current service status."""
        # JAM status
        jam_health = asyncio.run(self.jam.health_check())
        st.sidebar.metric("JAM Status", jam_health.get('status', 'unknown'))

        # Archon status
        archon_health = asyncio.run(self.archon_adapter.check_health())
        st.sidebar.metric("Archon Status", archon_health.get('status', 'unknown'))

        # Current borg
        if self.current_borg:
            st.sidebar.metric("Active Borg", self.current_borg['id'])
            wealth = asyncio.run(self.jam.get_wealth_balance(self.current_borg['id']))
            st.sidebar.metric("Wealth Balance", f"{wealth:.4f} DOT")

    def main_interface(self):
        """Main UI interface with tabs."""
        if not (self.jam and self.archon_adapter):
            st.warning("⚠️ Please initialize services in the sidebar first.")
            return

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏦 Fund Borg", "🧬 Create Borg", "🎯 Execute Task", "💰 Fund Management", "📊 Results & History"
        ])

        with tab1:
            self.fund_borg_tab()

        with tab2:
            self.create_borg_tab()

        with tab3:
            self.execute_task_tab()

        with tab4:
            self.fund_management_tab()

        with tab5:
            self.results_history_tab()

    def fund_borg_tab(self):
        """Tab for funding borgs with DOT."""
        st.header("🏦 Fund a Borg")

        st.markdown("""
        **Step 1:** Fund a borg with DOT tokens. This provides the economic incentive
        for autonomous execution and evolution.
        """)

        col1, col2 = st.columns(2)

        with col1:
            borg_id = st.text_input(
                "Borg ID",
                value=f"borg_{int(time.time())}",
                help="Unique identifier for the borg"
            )

            funding_amount = st.number_input(
                "Funding Amount (DOT)",
                min_value=0.1,
                max_value=10.0,
                value=0.1,
                step=0.1,
                help="Amount of DOT to fund the borg"
            )

        with col2:
            st.markdown("### Wallet Connection")
            if st.button("🔗 Connect Polkadot.js Wallet"):
                st.info("Wallet connection would be implemented here")
                # In Phase 1, we'll simulate funding
                st.session_state.wallet_connected = True

            if st.session_state.get('wallet_connected'):
                st.success("✅ Wallet connected (simulated)")

        if st.button("💰 Fund Borg", type="primary"):
            if not st.session_state.get('wallet_connected'):
                st.error("Please connect your wallet first")
                return

            try:
                # Simulate funding by updating wealth
                asyncio.run(self.jam.update_wealth(
                    borg_id=borg_id,
                    amount=Decimal(str(funding_amount)),
                    operation="revenue",
                    description=f"Initial funding from sponsor"
                ))

                st.success(f"✅ Successfully funded borg {borg_id} with {funding_amount} DOT")

                # Store current borg
                self.current_borg = {'id': borg_id, 'funded': True}

            except Exception as e:
                st.error(f"Funding failed: {e}")

    def create_borg_tab(self):
        """Tab for creating borgs from DNA."""
        st.header("🧬 Create Borg from DNA")

        st.markdown("""
        **Step 2:** Upload DNA configuration and create an executable borg phenotype.
        The DNA defines the borg's cells (logic) and organs (tools).
        """)

        # DNA upload/input
        dna_input_method = st.radio(
            "DNA Input Method",
            ["Upload YAML File", "Use Example DNA", "Paste YAML"]
        )

        dna: Optional[BorgDNA] = None

        if dna_input_method == "Upload YAML File":
            uploaded_file = st.file_uploader("Upload DNA YAML file", type=['yaml', 'yml'])
            if uploaded_file:
                dna_yaml = uploaded_file.read().decode('utf-8')
                dna = DNAParser.from_yaml(dna_yaml)

        elif dna_input_method == "Use Example DNA":
            if st.button("Generate Example DNA"):
                dna = DNAParser.create_example_dna()
                dna_yaml = DNAParser.to_yaml(dna)
                st.code(dna_yaml, language='yaml')

        else:  # Paste YAML
            dna_yaml = st.text_area("Paste DNA YAML", height=300)
            if dna_yaml and st.button("Parse DNA"):
                try:
                    dna = DNAParser.from_yaml(dna_yaml)
                    st.success("✅ DNA parsed successfully")
                except Exception as e:
                    st.error(f"DNA parsing failed: {e}")

        # DNA validation
        if dna:
            st.markdown("### DNA Validation")
            issues = DNAParser.validate_dna(dna)
            if issues:
                st.error("❌ DNA validation failed:")
                for issue in issues:
                    st.error(f"  • {issue}")
            else:
                st.success("✅ DNA validation passed")

                # Display DNA summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Cells", len(dna.cells))
                with col2:
                    st.metric("Organs", len(dna.organs))
                with col3:
                    st.metric("Gas Limit", dna.header.gas_limit)

        # Borg creation
        if dna and st.button("🚀 Create Borg", type="primary"):
            if not self.current_borg:
                st.error("Please fund a borg first")
                return

            try:
                with st.spinner("Building phenotype..."):
                    phenotype = asyncio.run(self.phenotype_builder.build(dna))

                st.success("✅ Borg created successfully!")

                # Store borg data
                self.current_borg.update({
                    'dna': dna,
                    'phenotype': phenotype,
                    'created_at': time.time()
                })

                # Display phenotype info
                st.markdown("### Phenotype Summary")
                st.json({
                    'borg_id': self.current_borg['id'],
                    'cells': list(phenotype.cells.keys()),
                    'organs': list(phenotype.organs.keys()),
                    'cost_estimate': phenotype._estimate_execution_cost()
                })

            except Exception as e:
                st.error(f"Borg creation failed: {e}")

    def execute_task_tab(self):
        """Tab for executing tasks with the borg."""
        st.header("🎯 Execute Task")

        st.markdown("""
        **Step 3:** Submit a task for the borg to execute using its phenotype.
        The borg will use its cells and organs to complete the task.
        """)

        if not self.current_borg or 'phenotype' not in self.current_borg:
            st.warning("⚠️ Please create a borg first.")
            return

        # Task input
        task_description = st.text_area(
            "Task Description",
            height=100,
            placeholder="Describe the task for the borg to execute...",
            help="Be specific about what you want the borg to accomplish"
        )

        # Task examples
        st.markdown("### Example Tasks")
        example_tasks = [
            "Summarize the key evolution mechanisms in BorgLife whitepaper sections 4-7",
            "Analyze code examples for DNA parsing patterns",
            "Create a task for GP evolution research planning",
            "Research the latest developments in autonomous AI agents"
        ]

        selected_example = st.selectbox("Or choose an example:", [""] + example_tasks)
        if selected_example:
            task_description = selected_example

        # Execution
        if st.button("▶️ Execute Task", type="primary"):
            if not task_description.strip():
                st.error("Please enter a task description")
                return

            try:
                with st.spinner("Executing task..."):
                    phenotype = self.current_borg['phenotype']
                    result = asyncio.run(phenotype.execute_task(task_description))

                # Record execution
                execution_record = {
                    'timestamp': time.time(),
                    'task': task_description,
                    'result': result,
                    'borg_id': self.current_borg['id']
                }
                self.execution_history.append(execution_record)

                # Display result
                st.success("✅ Task executed successfully!")

                st.markdown("### Execution Result")
                if 'error' in result:
                    st.error(f"Execution Error: {result['error']}")
                else:
                    st.info(f"**Cell Used:** {result.get('cell_used', 'unknown')}")
                    st.info(f"**Cost:** {result.get('cost', 0):.6f} DOT")
                    st.info(f"**Result:** {result.get('result', 'No result')}")

                    # Update wealth
                    asyncio.run(self.jam.update_wealth(
                        borg_id=self.current_borg['id'],
                        amount=Decimal(str(result.get('cost', 0))),
                        operation="cost",
                        description=f"Task execution: {task_description[:50]}..."
                    ))

            except Exception as e:
                st.error(f"Task execution failed: {e}")

    def fund_management_tab(self):
        """Tab for fund management and USDB transfers."""
        st.header("💰 Fund Management & USDB Transfers")

        st.markdown("""
        **Phase 2A:** Manage dual-currency balances and execute secure USDB transfers between borgs.
        USDB enables economic wealth storage separate from WND operational costs.
        """)

        if not self.current_borg:
            st.warning("⚠️ Please fund and create a borg first.")
            return

        # Initialize fund management components if needed
        if not hasattr(self, 'fund_manager'):
            self._init_fund_management()

        col1, col2 = st.columns(2)

        with col1:
            self._display_balance_summary()

        with col2:
            self._display_transfer_interface()

        # Transfer history
        self._display_transfer_history()

    def _init_fund_management(self):
        """Initialize fund management components."""
        try:
            from jam_mock.borg_address_manager import BorgAddressManager
            from jam_mock.inter_borg_transfer import InterBorgTransfer
            from jam_mock.economic_validator import EconomicValidator
            from jam_mock.ethical_compliance_monitor import EthicalComplianceMonitor
            from jam_mock.demo_cost_controller import DemoCostController
            from jam_mock.transaction_manager import TransactionManager

            # Mock Supabase client for demo
            supabase_client = None

            self.address_manager = BorgAddressManager(
                supabase_client=supabase_client,
                audit_logger=DemoAuditLogger()
            )

            self.cost_controller = DemoCostController()
            self.compliance_monitor = EthicalComplianceMonitor()
            self.economic_validator = EconomicValidator(
                cost_controller=self.cost_controller,
                compliance_monitor=self.compliance_monitor,
                supabase_client=supabase_client
            )

            self.transaction_manager = TransactionManager(
                kusama_adapter=self.jam,
                keypair_manager=None  # Would need proper keypair manager
            )

            self.transfer_protocol = InterBorgTransfer(
                westend_adapter=self.jam,
                address_manager=self.address_manager,
                economic_validator=self.economic_validator,
                transaction_manager=self.transaction_manager
            )

            self.fund_manager = True

        except ImportError as e:
            st.error(f"Phase 2A components not available: {e}")
            st.info("Run Phase 2A implementation to enable fund management features.")

    def _display_balance_summary(self):
        """Display dual-currency balance summary."""
        st.markdown("### Balance Summary")

        try:
            # Get balance summary
            balance_summary = asyncio.run(
                self.transfer_protocol.get_borg_balance_summary(self.current_borg['id'])
            )

            if 'error' in balance_summary:
                st.error(f"Failed to load balances: {balance_summary['error']}")
                return

            # Display balances
            col1, col2 = st.columns(2)

            with col1:
                wnd_balance = balance_summary['balances']['WND']['database']
                st.metric("WND Balance", f"{wnd_balance} WND")
                st.caption("Blockchain operations & gas fees")

            with col2:
                usdb_balance = balance_summary['balances']['USDB']['database']
                st.metric("USDB Balance", f"{usdb_balance} USDB")
                st.caption("Economic wealth & transfers")

            # Quick actions
            st.markdown("### Quick Actions")

            if st.button("🚰 Request USDB Funds"):
                # Simulate faucet request
                st.info("USDB faucet would distribute funds here")
                st.success("✅ 50 USDB distributed (simulated)")

            if st.button("🔄 Sync Balances"):
                st.info("Balance synchronization would occur here")
                st.success("✅ Balances synchronized")

        except Exception as e:
            st.error(f"Balance display error: {e}")

    def _display_transfer_interface(self):
        """Display USDB transfer interface."""
        st.markdown("### Transfer USDB")

        # Transfer form
        with st.form("usdb_transfer"):
            to_borg_id = st.text_input(
                "Recipient Borg ID",
                help="ID of the borg to receive USDB"
            )

            amount = st.number_input(
                "Amount (USDB)",
                min_value=0.01,
                max_value=1000.0,
                value=10.0,
                step=0.1,
                help="Amount of USDB to transfer"
            )

            description = st.text_area(
                "Description (Optional)",
                height=60,
                help="Purpose of the transfer"
            )

            submitted = st.form_submit_button("💸 Transfer USDB", type="primary")

            if submitted:
                if not to_borg_id.strip():
                    st.error("Please enter recipient borg ID")
                    return

                try:
                    with st.spinner("Processing transfer..."):
                        # Execute transfer
                        result = asyncio.run(self.transfer_protocol.transfer_usdb(
                            from_borg_id=self.current_borg['id'],
                            to_borg_id=to_borg_id,
                            amount=Decimal(str(amount)),
                            description=description or "Manual transfer"
                        ))

                    if result['success']:
                        st.success("✅ Transfer completed successfully!")
                        st.info(f"Transaction ID: {result['transfer_id']}")
                        st.info(f"Blockchain TX: {result['transaction_hash']}")

                        # Refresh balances
                        st.rerun()
                    else:
                        st.error("❌ Transfer failed:")
                        for error in result.get('errors', []):
                            st.error(f"  • {error}")

                except Exception as e:
                    st.error(f"Transfer error: {e}")

    def _display_transfer_history(self):
        """Display transfer history."""
        st.markdown("### Transfer History")

        try:
            # Get transfer history
            history = asyncio.run(
                self.transfer_protocol.get_transfer_history(self.current_borg['id'], limit=10)
            )

            if not history:
                st.info("No transfers yet.")
                return

            # Display as table
            import pandas as pd

            df_data = []
            for transfer in history:
                df_data.append({
                    'Direction': transfer['direction'].title(),
                    'Amount': f"{transfer['amount']} USDB",
                    'Counterparty': transfer['to_borg_id'] if transfer['direction'] == 'sent' else transfer['from_borg_id'],
                    'Status': transfer['status'].title(),
                    'Date': time.strftime('%Y-%m-%d %H:%M', time.localtime(float(transfer['created_at'])))
                })

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"History display error: {e}")

    def results_history_tab(self):
        """Tab for viewing results and execution history."""
        st.header("📊 Results & History")

        if not self.execution_history:
            st.info("No executions yet. Execute some tasks to see results here.")
            return

        # Summary metrics
        total_executions = len(self.execution_history)
        successful_executions = len([e for e in self.execution_history if 'error' not in e.get('result', {})])
        total_cost = sum(float(e.get('result', {}).get('cost', 0)) for e in self.execution_history)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Executions", total_executions)
        with col2:
            st.metric("Successful", successful_executions)
        with col3:
            st.metric("Success Rate", f"{successful_executions/total_executions*100:.1f}%" if total_executions > 0 else "0%")
        with col4:
            st.metric("Total Cost", f"{total_cost:.6f} DOT")

        # Execution history
        st.markdown("### Execution History")

        for i, execution in enumerate(reversed(self.execution_history)):
            with st.expander(f"Execution {len(self.execution_history)-i}: {execution['task'][:50]}..."):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(execution['timestamp']))}")
                    st.write(f"**Borg ID:** {execution['borg_id']}")

                with col2:
                    result = execution.get('result', {})
                    if 'error' in result:
                        st.error(f"**Error:** {result['error']}")
                    else:
                        st.write(f"**Cell Used:** {result.get('cell_used', 'unknown')}")
                        st.write(f"**Cost:** {result.get('cost', 0):.6f} DOT")

                if 'result' in execution and 'result' in execution['result']:
                    st.markdown("**Result:**")
                    st.code(execution['result']['result'], language='text')

        # Wealth tracking
        if self.current_borg:
            st.markdown("### Wealth Tracking")
            try:
                balance = asyncio.run(self.jam.get_wealth_balance(self.current_borg['id']))
                transactions = asyncio.run(self.jam.get_transaction_history(self.current_borg['id'], limit=10))

                st.metric("Current Balance", f"{balance:.6f} DOT")

                if transactions:
                    st.markdown("**Recent Transactions:**")
                    for tx in reversed(transactions[-5:]):  # Show last 5
                        st.write(f"• {tx['operation'].title()}: {tx['amount']:.6f} DOT - {tx['description']}")

            except Exception as e:
                st.error(f"Failed to load wealth data: {e}")


def main():
    """Main Streamlit app."""
    ui = SponsorUI()
    ui.setup_page()
    ui.main_interface()


if __name__ == "__main__":
    main()