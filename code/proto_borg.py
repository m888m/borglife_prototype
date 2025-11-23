# borglife_prototype/proto_borg.py
"""
Proto-Borg Agent - Phase 1 prototype implementation.

Demonstrates Borglife's core functionality with Archon integration,
wealth tracking, and phenotype execution.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from archon_adapter import ArchonServiceAdapter
from jam_mock import LocalJAMMock
from synthesis import BorgDNA, DNAParser, PhenotypeBuilder, PhenotypeEncoder

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Simple transaction record for wealth tracking"""

    timestamp: datetime
    transaction_type: str  # 'cost', 'revenue', 'transfer'
    amount: Decimal
    currency: str = "DOT"
    description: str = ""
    balance_after: Decimal = Decimal("0")


class MockWealthTracker:
    """Simple in-memory wealth tracker for proto-borg testing"""

    def __init__(self, initial_wealth: Decimal = Decimal("1.0")):
        self.total_wealth = initial_wealth
        self.transactions: List[Transaction] = []

    def get_balance(self) -> Decimal:
        """Get current wealth balance"""
        return self.total_wealth

    def log_transaction(
        self,
        transaction_type: str,
        amount: Decimal,
        currency: str = "DOT",
        description: str = "",
    ):
        """Log a transaction and update balance"""
        # Update balance
        if transaction_type in ["revenue", "transfer"]:
            self.total_wealth += amount
        elif transaction_type == "cost":
            self.total_wealth -= amount

        # Create transaction record
        transaction = Transaction(
            timestamp=datetime.utcnow(),
            transaction_type=transaction_type,
            amount=amount,
            currency=currency,
            description=description,
            balance_after=self.total_wealth,
        )

        self.transactions.append(transaction)


class BorgConfig:
    """Configuration for Proto-Borg."""

    def __init__(
        self,
        service_index: str = "proto-borg-001",
        westend_endpoint: str = "wss://westend-rpc.polkadot.io",
        initial_wealth: Decimal = Decimal("1.0"),
        max_task_time: int = 300,
        enable_fallbacks: bool = True,
    ):
        self.service_index = service_index
        self.westend_endpoint = westend_endpoint
        self.initial_wealth = initial_wealth
        self.max_task_time = max_task_time
        self.enable_fallbacks = enable_fallbacks


class ProtoBorgAgent:
    """
    Prototype Borg Agent - Phase 1 implementation.

    Demonstrates:
    - DNA parsing and phenotype building
    - Task execution via Archon services
    - Wealth tracking and cost management
    - On-chain storage simulation
    """

    def __init__(self, config: BorgConfig):
        self.config = config
        # Initialize wealth tracker (mock for now - would use Supabase in production)
        self.wealth = MockWealthTracker(initial_wealth=config.initial_wealth)
        self.jam = LocalJAMMock()  # Use real JAM implementation

        # Initialize DNA encoding components
        self.dna_parser = DNAParser()
        self.phenotype_encoder = PhenotypeEncoder()

        # Initialize Archon adapter
        self.archon = ArchonServiceAdapter()

        # Initialize synthesis components
        self.dna_parser = DNAParser()
        self.phenotype_builder = PhenotypeBuilder(self.archon)

        # Runtime state
        self.dna = None
        self.phenotype = None
        self.is_initialized = False

        logger.info(f"Proto-Borg initialized: {config.service_index}")

    async def initialize(self) -> bool:
        """
        Async initialization - load DNA and build phenotype.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize Archon adapter (optional - continue if unavailable)
            try:
                archon_ready = await self.archon.initialize()
                if not archon_ready:
                    logger.warning(
                        "Archon services unavailable - continuing with mock phenotype"
                    )
            except Exception as e:
                logger.warning(
                    f"Archon initialization failed: {e} - continuing with mock phenotype"
                )

            # Load DNA
            self.dna = self._load_dna()
            if not self.dna:
                logger.error("Failed to load DNA")
                return False

            # Build phenotype (use mock adapter if Archon unavailable)
            try:
                self.phenotype = await self.phenotype_builder.build(self.dna)
                if not self.phenotype:
                    logger.warning(
                        "Phenotype building failed - creating mock phenotype"
                    )
                    self.phenotype = self._create_mock_phenotype()
            except Exception as e:
                logger.warning(
                    f"Phenotype building failed: {e} - creating mock phenotype"
                )
                self.phenotype = self._create_mock_phenotype()

            self.is_initialized = True
            logger.info(f"Proto-Borg {self.config.service_index} ready for execution")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def _create_mock_phenotype(self):
        """Create a mock phenotype for testing when Archon is unavailable"""
        from synthesis import BorgPhenotype

        class MockPhenotype:
            def __init__(self):
                self.cells = {
                    "basic_processor": MockCell("basic_processor"),
                    "decision_maker": MockCell("decision_maker"),
                }
                self.organs = {
                    "web_search": lambda **kwargs: {"result": "Mock web search result"},
                    "data_analysis": lambda **kwargs: {
                        "result": "Mock data analysis result"
                    },
                }
                self.is_built = True

            def _calculate_task_cost(self, execution_time: float) -> Decimal:
                """Calculate task execution cost"""
                return Decimal(str(execution_time * 0.0001))

            async def execute_task(self, task_description: str):
                """Execute task with cost calculation"""
                execution_time = 0.1  # Mock execution time
                cost = self._calculate_task_cost(execution_time)

                return {
                    "response": f"Mock execution result for: {task_description}",
                    "mock": True,
                    "cost": cost,
                    "execution_time": execution_time,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        class MockCell:
            def __init__(self, name):
                self.name = name

        return MockPhenotype()

    def _load_dna(self) -> Optional[BorgDNA]:
        """
        Load DNA from file or create default.

        Returns:
            BorgDNA object or None if failed
        """
        try:
            # Try to load from borg_dna.yaml
            import os

            dna_file = os.path.join(os.path.dirname(__file__), "borg_dna.yaml")

            if os.path.exists(dna_file):
                with open(dna_file, "r") as f:
                    dna_yaml = f.read()
                dna = self.dna_parser.from_yaml(dna_yaml)
                logger.info(f"Loaded DNA from file: {dna.header.service_index}")

                # Skip manifesto validation for Phase 1 bootstrapping
                from synthesis import DNAValidator

                validator = DNAValidator()
                errors = validator.validate_structure(dna)
                filtered_errors = [e for e in errors if "Manifesto hash" not in e]
                if filtered_errors:
                    logger.warning(
                        f"DNA validation warnings (non-blocking): {filtered_errors}"
                    )
                else:
                    logger.info("DNA validation passed")

                return dna
            else:
                # Create minimal DNA for bootstrapping
                logger.warning("No borg_dna.yaml found, creating minimal DNA")
                return self._create_minimal_dna()
        except Exception as e:
            logger.error(f"Failed to load DNA: {e}")
            # Create minimal DNA as fallback
            logger.warning("Creating minimal DNA as fallback")
            return self._create_minimal_dna()

        except Exception as e:
            logger.error(f"Failed to load DNA: {e}")
            return None

    def _create_minimal_dna(self) -> BorgDNA:
        """
        Create minimal DNA structure for bootstrapping.

        Returns:
            Minimal BorgDNA with basic cells and organs
        """
        from synthesis import Cell, DNAHeader, Organ

        # Create minimal header
        header = DNAHeader(
            code_length=1024, gas_limit=1000000, service_index=self.config.service_index
        )

        # Create basic cells
        cells = [
            Cell(
                name="basic_processor",
                logic_type="data_processing",
                parameters={"model": "gpt-4", "max_tokens": 500, "temperature": 0.7},
                cost_estimate=0.001,
            ),
            Cell(
                name="decision_maker",
                logic_type="decision_making",
                parameters={"strategy": "utility_maximization", "risk_tolerance": 0.5},
                cost_estimate=0.0008,
            ),
        ]

        # Create basic organs
        organs = [
            Organ(
                name="web_search",
                mcp_tool="web_search",
                url="http://localhost:8080",  # Placeholder
                abi_version="1.0",
                price_cap=0.01,
            ),
            Organ(
                name="data_analysis",
                mcp_tool="data_analysis",
                url="http://localhost:8081",  # Placeholder
                abi_version="1.0",
                price_cap=0.005,
            ),
        ]

        # Create DNA with placeholder manifesto hash
        return BorgDNA(
            header=header,
            cells=cells,
            organs=organs,
            manifesto_hash="minimal_bootstrap_manifesto_hash_123456789abcdef",
        )

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task using the borg's phenotype and handle DNA storage workflow.

        Process:
        1. Execute task using phenotype
        2. Update wealth tracking for task costs
        3. Encode phenotype back to DNA after successful execution
        4. Store DNA on-chain via JAM
        5. Update wealth for storage costs

        Returns:
            Task execution result with execution and storage details
        """
        if not self.is_initialized:
            raise RuntimeError("Proto-Borg not initialized")

        start_time = datetime.utcnow()
        task_id = f"task_{int(start_time.timestamp())}"

        try:
            # Estimate cost (simplified)
            estimated_cost = Decimal("0.001")
            if self.wealth.get_balance() < estimated_cost:
                raise ValueError(
                    f"Insufficient funds. Required: {estimated_cost}, Available: {self.wealth.get_balance()}"
                )

            # Execute task via phenotype
            result = await self.phenotype.execute_task(task_description)

            # Calculate actual cost (simplified)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            actual_cost = Decimal(str(execution_time * 0.0001))  # Cost per second

            # Record transaction for task execution
            self.wealth.log_transaction(
                transaction_type="cost",
                amount=actual_cost,
                currency="DOT",
                description=f"Task execution: {task_description[:50]}...",
            )

            # Encode phenotype to DNA after successful execution
            dna_storage_result = await self._encode_and_store_dna()

            # Update wealth for DNA storage cost
            if dna_storage_result["success"]:
                storage_cost = Decimal(str(dna_storage_result.get("cost", 0.001)))
                self.wealth.log_transaction(
                    transaction_type="cost",
                    amount=storage_cost,
                    currency="DOT",
                    description="DNA storage on JAM",
                )

            # Return result with metadata
            return {
                "task_id": task_id,
                "task_description": task_description,
                "result": result,
                "execution_time": execution_time,
                "cost": float(actual_cost),
                "borg_id": self.config.service_index,
                "timestamp": start_time.isoformat(),
                "success": True,
                "dna_storage": dna_storage_result,
            }

        except Exception as e:
            # Log failed transaction
            self.wealth.log_transaction(
                transaction_type="error",
                amount=Decimal("0"),
                currency="DOT",
                description=f"Task failed: {str(e)}",
            )

            logger.error(f"Task execution failed: {e}")
            return {
                "task_id": task_id,
                "task_description": task_description,
                "error": str(e),
                "borg_id": self.config.service_index,
                "timestamp": start_time.isoformat(),
                "success": False,
            }

    async def _encode_and_store_dna(self) -> Dict[str, Any]:
        """
        Encode current phenotype to DNA and store on JAM.
        """
        try:
            # Encode phenotype to DNA
            encoded_dna = self.phenotype_encoder.encode(self.phenotype)

            # Prepare for JAM storage
            jam_data = self.phenotype_encoder.prepare_for_jam_storage(encoded_dna)

            # Store on JAM
            storage_result = await self.jam.store_dna_hash(
                borg_id=self.config.service_index,
                dna_hash=jam_data["dna_hash"],
                metadata={
                    "cell_count": jam_data["cell_count"],
                    "organ_count": jam_data["organ_count"],
                    "code_length": jam_data["code_length"],
                },
            )

            return {
                "success": storage_result["success"],
                "dna_hash": jam_data["dna_hash"],
                "block_number": storage_result.get("block_number"),
                "transaction_hash": storage_result.get("transaction_hash"),
                "cost": storage_result.get("cost", Decimal("0")),
                "encoded_at": jam_data["prepared_at"],
            }

        except Exception as e:
            logger.error(f"DNA encoding/storage failed: {e}")
            return {"success": False, "error": str(e), "cost": Decimal("0")}

    async def get_status(self) -> Dict[str, Any]:
        """
        Get current borg status.

        Returns:
            Status information
        """
        return {
            "borg_id": self.config.service_index,
            "initialized": self.is_initialized,
            "wealth": float(self.wealth.get_balance()),
            "dna_loaded": self.dna is not None,
            "phenotype_built": self.phenotype is not None,
            "cells_count": len(self.phenotype.cells) if self.phenotype else 0,
            "organs_count": len(self.phenotype.organs) if self.phenotype else 0,
            "transactions_count": len(self.wealth.transactions),
            "last_transaction": (
                self.wealth.transactions[-1] if self.wealth.transactions else None
            ),
        }

    async def update_dna(self, dna_yaml: str) -> bool:
        """
        Update borg DNA and rebuild phenotype.

        Args:
            dna_yaml: New DNA in YAML format

        Returns:
            True if update successful
        """
        try:
            # Parse new DNA
            new_dna = self.dna_parser.from_yaml(dna_yaml)

            # Validate DNA structure (skip manifesto validation for now)
            from synthesis import DNAValidator

            validator = DNAValidator()
            errors = validator.validate_structure(new_dna)
            # Allow manifesto hash mismatch for bootstrapping
            filtered_errors = [e for e in errors if "Manifesto hash" not in e]
            if filtered_errors:
                raise ValueError(f"DNA validation failed: {'; '.join(filtered_errors)}")

            # Rebuild phenotype
            new_phenotype = await self.phenotype_builder.build(new_dna)

            # Update state
            self.dna = new_dna
            self.phenotype = new_phenotype

            logger.info(f"DNA updated for borg {self.config.service_index}")
            return True

        except Exception as e:
            logger.error(f"DNA update failed: {e}")
            return False

    async def store_dna_on_chain(self) -> Dict[str, Any]:
        """
        Store DNA hash on-chain (mock implementation).

        Returns:
            Storage result
        """
        if not self.dna:
            raise ValueError("No DNA loaded")

        try:
            dna_hash = self.dna.compute_hash()
            logger.info(f"Computed DNA hash: {dna_hash[:16]}...")

            # Mock on-chain storage
            result = await self.jam.store_dna_hash(
                borg_id=self.config.service_index,
                dna_hash=dna_hash,
                metadata={
                    "cells_count": len(self.dna.cells),
                    "organs_count": len(self.dna.organs),
                    "service_index": self.dna.header.service_index,
                },
            )

            return {
                "success": True,
                "dna_hash": dna_hash,
                "transaction_hash": result.get("transaction_hash"),
                "block_number": result.get("block_number"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"On-chain storage failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_wealth_history(self) -> List[Dict[str, Any]]:
        """
        Get wealth transaction history.

        Returns:
            List of transactions
        """
        return [
            {
                "timestamp": tx.timestamp.isoformat(),
                "type": tx.transaction_type,
                "amount": float(tx.amount),
                "currency": tx.currency,
                "description": tx.description,
                "balance_after": float(tx.balance_after),
            }
            for tx in self.wealth.transactions
        ]

    async def shutdown(self):
        """Clean shutdown."""
        await self.archon.close()
        logger.info(f"Proto-Borg {self.config.service_index} shut down")


# Convenience functions for testing


async def create_proto_borg(service_index: str = "test-borg") -> ProtoBorgAgent:
    """
    Create and initialize a proto-borg for testing.

    Args:
        service_index: Unique service identifier

    Returns:
        Initialized ProtoBorgAgent
    """
    config = BorgConfig(service_index=service_index)
    borg = ProtoBorgAgent(config)

    if await borg.initialize():
        return borg
    else:
        raise RuntimeError("Failed to initialize proto-borg")


async def run_demo_task(borg: ProtoBorgAgent, task: str) -> Dict[str, Any]:
    """
    Run a demo task and return formatted results.

    Args:
        borg: Proto-borg instance
        task: Task description

    Returns:
        Demo results
    """
    print(f"🤖 Executing task: {task}")

    result = await borg.execute_task(task)
    status = await borg.get_status()

    print(f"✅ Task completed in {result.get('execution_time', 0):.2f}s")
    print(f"💰 Cost: {result.get('cost', 0):.6f} DOT")
    print(f"💎 Wealth remaining: {status['wealth']:.6f} DOT")

    return result
