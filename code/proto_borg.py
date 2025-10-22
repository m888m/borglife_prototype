# borglife_prototype/proto_borg.py
"""
Proto-Borg Agent - Phase 1 prototype implementation.

Demonstrates Borglife's core functionality with Archon integration,
wealth tracking, and phenotype execution.
"""

from typing import Dict, Any, Optional, List
import asyncio
import logging
from decimal import Decimal
from datetime import datetime

from archon_adapter import ArchonServiceAdapter
from synthesis import DNAParser, PhenotypeBuilder
from jam_mock import JAMMockInterface
from wealth_tracker import WealthTracker

logger = logging.getLogger(__name__)

class BorgConfig:
    """Configuration for Proto-Borg."""

    def __init__(
        self,
        service_index: str = "proto-borg-001",
        kusama_endpoint: str = "wss://kusama-rpc.polkadot.io",
        initial_wealth: Decimal = Decimal('1.0'),
        max_task_time: int = 300,
        enable_fallbacks: bool = True
    ):
        self.service_index = service_index
        self.kusama_endpoint = kusama_endpoint
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
        self.wealth = WealthTracker(initial_wealth=config.initial_wealth)
        self.jam = JAMMockInterface()

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
            # Initialize Archon adapter
            if not await self.archon.initialize():
                logger.error("Failed to initialize Archon adapter")
                return False

            # Load DNA
            self.dna = self._load_dna()
            if not self.dna:
                logger.error("Failed to load DNA")
                return False

            # Build phenotype
            self.phenotype = await self.phenotype_builder.build(self.dna)
            if not self.phenotype:
                logger.error("Failed to build phenotype")
                return False

            self.is_initialized = True
            logger.info(f"Proto-Borg {self.config.service_index} ready for execution")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def _load_dna(self) -> Optional[Any]:
        """
        Load DNA from file or create default.

        Returns:
            BorgDNA object or None if failed
        """
        try:
            # Try to load from borg_dna.yaml
            import os
            dna_file = os.path.join(os.path.dirname(__file__), 'borg_dna.yaml')

            if os.path.exists(dna_file):
                with open(dna_file, 'r') as f:
                    dna_yaml = f.read()
                return self.dna_parser.from_yaml(dna_yaml)
            else:
                # Create minimal DNA for bootstrapping
                logger.warning("No borg_dna.yaml found, creating minimal DNA")
                return self.dna_parser.create_minimal_dna(
                    service_index=self.config.service_index,
                    manifesto_hash="placeholder_manifesto_hash"
                )

        except Exception as e:
            logger.error(f"Failed to load DNA: {e}")
            return None

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task using the borg's phenotype.

        Args:
            task_description: Description of task to execute

        Returns:
            Task execution result with metadata
        """
        if not self.is_initialized:
            raise RuntimeError("Proto-Borg not initialized")

        start_time = datetime.utcnow()
        task_id = f"task_{int(start_time.timestamp())}"

        try:
            # Estimate cost (simplified)
            estimated_cost = Decimal('0.001')
            if self.wealth.get_balance() < estimated_cost:
                raise ValueError(f"Insufficient funds. Required: {estimated_cost}, Available: {self.wealth.get_balance()}")

            # Execute task via phenotype
            result = await self.phenotype.execute_task(task_description)

            # Calculate actual cost (simplified)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            actual_cost = Decimal(str(execution_time * 0.0001))  # Cost per second

            # Record transaction
            self.wealth.log_transaction(
                transaction_type="cost",
                amount=actual_cost,
                currency="DOT",
                description=f"Task execution: {task_description[:50]}..."
            )

            # Return result with metadata
            return {
                'task_id': task_id,
                'task_description': task_description,
                'result': result,
                'execution_time': execution_time,
                'cost': float(actual_cost),
                'borg_id': self.config.service_index,
                'timestamp': start_time.isoformat(),
                'success': True
            }

        except Exception as e:
            # Log failed transaction
            self.wealth.log_transaction(
                transaction_type="error",
                amount=Decimal('0'),
                currency="DOT",
                description=f"Task failed: {str(e)}"
            )

            logger.error(f"Task execution failed: {e}")
            return {
                'task_id': task_id,
                'task_description': task_description,
                'error': str(e),
                'borg_id': self.config.service_index,
                'timestamp': start_time.isoformat(),
                'success': False
            }

    async def get_status(self) -> Dict[str, Any]:
        """
        Get current borg status.

        Returns:
            Status information
        """
        return {
            'borg_id': self.config.service_index,
            'initialized': self.is_initialized,
            'wealth': float(self.wealth.get_balance()),
            'dna_loaded': self.dna is not None,
            'phenotype_built': self.phenotype is not None,
            'cells_count': len(self.phenotype.cells) if self.phenotype else 0,
            'organs_count': len(self.phenotype.organs) if self.phenotype else 0,
            'transactions_count': len(self.wealth.transactions),
            'last_transaction': self.wealth.transactions[-1] if self.wealth.transactions else None
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

            # Validate
            if not new_dna.validate_integrity():
                raise ValueError("DNA integrity validation failed")

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

            # Mock on-chain storage
            result = await self.jam.store_dna_hash(
                borg_id=self.config.service_index,
                dna_hash=dna_hash,
                metadata={
                    'cells_count': len(self.dna.cells),
                    'organs_count': len(self.dna.organs),
                    'service_index': self.dna.header.service_index
                }
            )

            return {
                'success': True,
                'dna_hash': dna_hash,
                'transaction_hash': result.get('transaction_hash'),
                'block_number': result.get('block_number'),
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"On-chain storage failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def get_wealth_history(self) -> List[Dict[str, Any]]:
        """
        Get wealth transaction history.

        Returns:
            List of transactions
        """
        return [
            {
                'timestamp': tx.timestamp.isoformat(),
                'type': tx.transaction_type,
                'amount': float(tx.amount),
                'currency': tx.currency,
                'description': tx.description,
                'balance_after': float(tx.balance_after)
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