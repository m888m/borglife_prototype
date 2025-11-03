# borglife_prototype/synthesis/phenotype_builder.py
"""
Phenotype Builder - Construct executable borg phenotypes from DNA.

Builds BorgPhenotype objects from BorgDNA by creating cells (PydanticAI agents)
and registering organs (MCP tool callables).
"""

from typing import Dict, Any, Optional, Callable, List
import asyncio
import logging

from .dna_parser import BorgDNA, Cell, Organ
try:
    from ..archon_adapter import ArchonServiceAdapter
    from ..archon_adapter.exceptions import PhenotypeBuildError
except ImportError:
    # Mock for testing when archon_adapter is not available
    class ArchonServiceAdapter:
        pass
    class PhenotypeBuildError(Exception):
        pass

logger = logging.getLogger(__name__)

class BorgPhenotype:
    """Executable borg phenotype (body) built from DNA."""

    def __init__(self, dna: BorgDNA, adapter: ArchonServiceAdapter):
        self.dna = dna
        self.adapter = adapter

        # Built components
        self.cells: Dict[str, Any] = {}  # name -> cell instance
        self.organs: Dict[str, Callable] = {}  # name -> organ callable

        # Metadata
        self.build_timestamp = None
        self.is_built = False

    async def execute_task(self, task_description: str, wealth: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute a task using the phenotype's cells and organs with economic tracking.

        Args:
            task_description: Description of the task to execute
            wealth: Current borg wealth for cost tracking

        Returns:
            Task execution result with cost information
        """
        if not self.is_built:
            raise PhenotypeBuildError(
                self.dna.header.service_index,
                "Phenotype not fully built"
            )

        # Route task to appropriate cell based on task type
        # This is a simplified routing - in production would be more sophisticated
        if not self.cells:
            raise PhenotypeBuildError(
                self.dna.header.service_index,
                "No cells available for task execution"
            )

        # Use first available cell for now
        cell_name = next(iter(self.cells.keys()))
        cell = self.cells[cell_name]

        # Track execution start for cost calculation
        start_time = asyncio.get_event_loop().time()

        try:
            # Execute task via cell
            result = await self._execute_via_cell(cell, task_description)

            # Calculate and track costs
            execution_time = asyncio.get_event_loop().time() - start_time
            cost_info = await self._calculate_task_cost(result, execution_time, wealth)

            # Enhance result with cost information
            result.update({
                'execution_time': execution_time,
                'cost_info': cost_info,
                'borg_id': self.dna.header.service_index
            })

            return result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            raise PhenotypeBuildError(
                self.dna.header.service_index,
                f"Task execution failed: {e}"
            )

    async def _execute_via_cell(self, cell, task_description: str) -> Dict[str, Any]:
        """
        Execute task via a specific cell.

        Args:
            cell: Cell instance to use
            task_description: Task description

        Returns:
            Execution result
        """
        try:
            # Execute the task using the cell's execute method
            cell_result = await cell.execute(task_description)

            # Enhance result with phenotype context
            enhanced_result = {
                'task': task_description,
                'result': cell_result,
                'cell_used': getattr(cell, 'name', 'unknown'),
                'organs_used': list(self.organs.keys()),
                'organs_available': len(self.organs),
                'phenotype_built': self.is_built,
                'timestamp': asyncio.get_event_loop().time()
            }

            return enhanced_result

        except Exception as e:
            logger.error(f"Cell execution failed: {e}")
            return {
                'task': task_description,
                'error': str(e),
                'cell_used': getattr(cell, 'name', 'unknown'),
                'organs_used': [],
                'timestamp': asyncio.get_event_loop().time()
            }

    def get_cell(self, name: str) -> Optional[Any]:
        """Get a cell by name."""
        return self.cells.get(name)

    def get_organ(self, name: str) -> Optional[Callable]:
        """Get an organ callable by name."""
        return self.organs.get(name)

    def list_cells(self) -> List[str]:
        """List all cell names."""
        return list(self.cells.keys())

    def list_organs(self) -> List[str]:
        """List all organ names."""
        return list(self.organs.keys())

class PhenotypeBuilder:
    """Builds executable phenotypes from DNA."""

    def __init__(self, adapter: ArchonServiceAdapter):
        self.adapter = adapter

    async def build(self, dna: BorgDNA) -> BorgPhenotype:
        """
        Build phenotype from DNA with full cell instantiation and organ integration.

        Process:
        1. Create BorgPhenotype instance
        2. Build cells (PydanticAI agents) with organ injection
        3. Register organs (MCP tool callables)
        4. Validate phenotype
        5. Return executable phenotype

        Args:
            dna: BorgDNA to build from

        Returns:
            BorgPhenotype ready for execution

        Raises:
            PhenotypeBuildError: If building fails
        """
        logger.info(f"Building phenotype for borg: {dna.header.service_index}")

        phenotype = BorgPhenotype(dna, self.adapter)

        # Store current DNA for organ injection
        self._current_dna = dna
        self._current_borg_id = dna.header.service_index

        try:
            # Build cells with organ injection
            await self._build_cells(phenotype)

            # Register organs
            await self._register_organs(phenotype)

            # Validate
            await self._validate_phenotype(phenotype)

            # Mark as built
            phenotype.is_built = True
            phenotype.build_timestamp = asyncio.get_event_loop().time()

            logger.info(f"Successfully built phenotype with {len(phenotype.cells)} cells and {len(phenotype.organs)} organs")
            return phenotype

        except Exception as e:
            error_msg = f"Failed to build phenotype: {e}"
            logger.error(error_msg)
            raise PhenotypeBuildError(dna.header.service_index, error_msg)
        finally:
            # Clean up temporary state
            self._current_dna = None
            self._current_borg_id = None

    async def _build_cells(self, phenotype: BorgPhenotype):
        """Build cells from DNA with organ injection."""
        for cell in phenotype.dna.cells:
            try:
                cell_instance = await self._build_cell(cell)

                # Inject available organs into the cell
                organ_names = [organ.name for organ in phenotype.dna.organs]
                await self._inject_organs_into_cell(cell_instance, organ_names, phenotype.dna.header.service_index)

                phenotype.cells[cell.name] = cell_instance
                logger.debug(f"Built cell: {cell.name} with {len(organ_names)} organs injected")
            except Exception as e:
                raise PhenotypeBuildError(
                    phenotype.dna.header.service_index,
                    f"Failed to build cell '{cell.name}': {e}"
                )

    async def _build_cell(self, cell: Cell) -> Any:
        """
        Build a single cell instance.

        Args:
            cell: Cell definition from DNA

        Returns:
            Cell instance (PydanticAI agent)
        """
        # Map logic types to agent types
        agent_type_map = {
            'rag_agent': 'rag',
            'document_agent': 'document',
            'decision_maker': 'custom',
            'data_processor': 'custom'
        }

        agent_type = agent_type_map.get(cell.logic_type, 'custom')

        if agent_type == 'custom':
            # For custom logic types, create a basic agent
            return await self._create_custom_cell(cell)
        else:
            # Use Archon agent service
            return await self._create_archon_cell(cell, agent_type)

    async def _create_archon_cell(self, cell: Cell, agent_type: str) -> Any:
        """
        Create cell using Archon agent service.

        Args:
            cell: Cell definition
            agent_type: Archon agent type

        Returns:
            Cell instance
        """
        # This would create a wrapper around Archon agent
        # For now, return a placeholder
        class ArchonCell:
            def __init__(self, name: str, agent_type: str, parameters: Dict[str, Any]):
                self.name = name
                self.agent_type = agent_type
                self.parameters = parameters

            async def execute(self, task: str) -> Dict[str, Any]:
                # Call Archon agent
                return await self.adapter.run_agent(
                    agent_type=self.agent_type,
                    prompt=task,
                    context=self.parameters
                )

        return ArchonCell(cell.name, agent_type, cell.parameters)

    async def _create_custom_cell(self, cell: Cell) -> Any:
        """
        Create custom cell implementation.

        Args:
            cell: Cell definition

        Returns:
            Custom cell instance
        """
        # Create custom cell based on logic type
        if cell.logic_type == 'decision_maker':
            return await self._create_decision_maker_cell(cell)
        elif cell.logic_type == 'data_processor':
            return await self._create_data_processor_cell(cell)
        else:
            # Generic custom cell
            class CustomCell:
                def __init__(self, name: str, logic_type: str, parameters: Dict[str, Any]):
                    self.name = name
                    self.logic_type = logic_type
                    self.parameters = parameters

                async def execute(self, task: str) -> Dict[str, Any]:
                    # Use RagAgent for custom cells
                    return await self.adapter.run_agent(
                        agent_type='rag',
                        prompt=f"Execute as {self.logic_type}: {task}",
                        context=self.parameters
                    )

            return CustomCell(cell.name, cell.logic_type, cell.parameters)

    async def _create_decision_maker_cell(self, cell: Cell) -> Any:
        """Create decision maker cell with actual logic."""
        class DecisionMakerCell:
            def __init__(self, name: str, parameters: Dict[str, Any], adapter: ArchonServiceAdapter):
                self.name = name
                self.parameters = parameters
                self.adapter = adapter

            async def execute(self, task: str) -> Dict[str, Any]:
                """Execute decision making logic using Archon agents."""
                try:
                    # Enhanced decision making prompt
                    strategy = self.parameters.get('strategy', 'utility_maximization')
                    prompt = f"""As a decision maker using {strategy} strategy, analyze and make a decision about:

{task}

Consider:
- Available options and their consequences
- Risk factors and uncertainties
- Resource constraints and costs
- Long-term vs short-term implications
- Ethical considerations

Provide a clear decision with reasoning."""

                    # Use Archon agent for decision making
                    result = await self.adapter.run_agent(
                        agent_type='rag',
                        prompt=prompt,
                        context={
                            'strategy': strategy,
                            'model': self.parameters.get('model', 'gpt-4'),
                            'max_tokens': self.parameters.get('max_tokens', 500)
                        }
                    )

                    return {
                        'cell_type': 'decision_maker',
                        'decision': result.get('response', result),
                        'strategy_used': strategy,
                        'timestamp': asyncio.get_event_loop().time()
                    }

                except Exception as e:
                    logger.error(f"Decision maker execution failed: {e}")
                    return {
                        'cell_type': 'decision_maker',
                        'error': str(e),
                        'fallback_decision': 'Unable to make decision due to system error'
                    }

        return DecisionMakerCell(cell.name, cell.parameters, self.adapter)

    async def _create_data_processor_cell(self, cell: Cell) -> Any:
        """Create data processor cell with actual logic."""
        class DataProcessorCell:
            def __init__(self, name: str, parameters: Dict[str, Any], adapter: ArchonServiceAdapter):
                self.name = name
                self.parameters = parameters
                self.adapter = adapter

            async def execute(self, task: str) -> Dict[str, Any]:
                """Execute data processing logic using Archon agents."""
                try:
                    # Enhanced data processing prompt
                    prompt = f"""As a data processor, analyze and process the following data/information:

{task}

Perform the following:
1. Extract key information and patterns
2. Identify trends, anomalies, or insights
3. Structure the data appropriately
4. Provide actionable conclusions
5. Suggest next steps if applicable

Be thorough but concise in your analysis."""

                    # Use document agent for data processing
                    result = await self.adapter.run_agent(
                        agent_type='document',
                        prompt=prompt,
                        context={
                            'model': self.parameters.get('model', 'gpt-4'),
                            'max_tokens': self.parameters.get('max_tokens', 500),
                            'processing_type': 'analysis'
                        }
                    )

                    return {
                        'cell_type': 'data_processor',
                        'processed_data': result.get('response', result),
                        'insights': [],  # Would be extracted from result
                        'timestamp': asyncio.get_event_loop().time()
                    }

                except Exception as e:
                    logger.error(f"Data processor execution failed: {e}")
                    return {
                        'cell_type': 'data_processor',
                        'error': str(e),
                        'fallback_result': 'Unable to process data due to system error'
                    }

        return DataProcessorCell(cell.name, cell.parameters, self.adapter)

    async def _inject_organs_into_cell(self, cell_instance, organ_names: List[str], borg_id: str):
        """
        Inject organ callables into a cell instance for seamless integration.

        Args:
            cell_instance: The cell instance to inject organs into
            organ_names: List of organ names to inject
            borg_id: Borg identifier for organ registration
        """
        from .cell_organ_protocol import CellOrganBridge

        bridge = CellOrganBridge(self.adapter)

        # Create organ callables and inject them
        injected_organs = {}
        for organ_name in organ_names:
            # Find the organ definition in current DNA
            organ_def = None
            if hasattr(self, '_current_dna') and self._current_dna:
                for organ in self._current_dna.organs:
                    if organ.name == organ_name:
                        organ_def = organ
                        break

            if organ_def:
                try:
                    organ_callable = bridge.register_organ(
                        organ_name=organ_name,
                        mcp_tool=organ_def.mcp_tool,
                        endpoint=organ_def.url,
                        borg_id=borg_id
                    )
                    injected_organs[organ_name] = organ_callable
                    logger.debug(f"Injected organ {organ_name} into cell {getattr(cell_instance, 'name', 'unknown')}")
                except Exception as e:
                    logger.warning(f"Failed to inject organ {organ_name}: {e}")
                    # Continue with other organs even if one fails

        # Inject the organs into the cell
        cell_instance.organs = injected_organs
        cell_instance.available_organs = list(injected_organs.keys())

        # Add organ usage methods to cell
        cell_instance.call_organ = self._create_organ_caller(cell_instance)
        cell_instance.has_organ = lambda name: name in injected_organs

    def _create_organ_caller(self, cell_instance):
        """
        Create a convenient organ caller method for the cell.

        Args:
            cell_instance: The cell instance

        Returns:
            Callable that allows easy organ invocation
        """
        async def call_organ(organ_name: str, **kwargs):
            """Call an organ by name with parameters."""
            if organ_name not in cell_instance.organs:
                raise ValueError(f"Organ '{organ_name}' not available in this cell")

            organ_callable = cell_instance.organs[organ_name]
            return await organ_callable(**kwargs)

        return call_organ

    async def _register_organs(self, phenotype: BorgPhenotype):
        """Register organs as callables."""
        for organ in phenotype.dna.organs:
            try:
                organ_callable = await self._register_organ(organ)
                phenotype.organs[organ.name] = organ_callable
                logger.debug(f"Registered organ: {organ.name}")
            except Exception as e:
                raise PhenotypeBuildError(
                    phenotype.dna.header.service_index,
                    f"Failed to register organ '{organ.name}': {e}"
                )

    async def _register_organ(self, organ: Organ) -> Callable:
        """
        Create callable for organ using CellOrganBridge with enhanced error handling.

        Args:
            organ: Organ definition

        Returns:
            Async callable for organ invocation
        """
        # Use CellOrganBridge for proper organ registration
        from .cell_organ_protocol import CellOrganBridge

        bridge = CellOrganBridge(self.adapter)
        organ_callable = bridge.register_organ(
            organ_name=organ.name,
            mcp_tool=organ.mcp_tool,
            endpoint=organ.url,
            borg_id=getattr(self, '_current_borg_id', organ.name)  # Use organ name as fallback borg_id
        )

        # Store metadata on callable
        organ_callable.tool_name = organ.mcp_tool
        organ_callable.endpoint = organ.url
        organ_callable.version = organ.abi_version
        organ_callable.price_cap = organ.price_cap

        return organ_callable

    async def _validate_phenotype(self, phenotype: BorgPhenotype):
        """
        Validate that phenotype is properly built.

        Args:
            phenotype: Phenotype to validate

        Raises:
            PhenotypeBuildError: If validation fails
        """
        errors = []

        # Check that we have at least one cell or organ
        if not phenotype.cells and not phenotype.organs:
            errors.append("Phenotype must have at least one cell or organ")

        # Check cell validity
        for name, cell in phenotype.cells.items():
            if not hasattr(cell, 'execute'):
                errors.append(f"Cell '{name}' missing execute method")

        # Check organ validity
        for name, organ in phenotype.organs.items():
            if not callable(organ):
                errors.append(f"Organ '{name}' is not callable")

        # Check DNA integrity
        if not phenotype.dna.validate_integrity():
            errors.append("DNA integrity validation failed")

        if errors:
            raise PhenotypeBuildError(
                phenotype.dna.header.service_index,
                f"Phenotype validation failed: {'; '.join(errors)}"
            )

    async def rebuild_phenotype(self, phenotype: BorgPhenotype, dna_updates: Dict[str, Any]) -> BorgPhenotype:
        """
        Rebuild phenotype with DNA updates (for evolution).

        Args:
            phenotype: Current phenotype
            dna_updates: DNA updates to apply

        Returns:
            Updated phenotype
        """
        # Merge DNA updates
        updated_dna = self.adapter.dna_parser.merge_dna(phenotype.dna, dna_updates)

        # Build new phenotype
        return await self.build(updated_dna)

    async def _calculate_task_cost(
        self,
        result: Dict[str, Any],
        execution_time: float,
        wealth: Optional[float]
    ) -> Dict[str, Any]:
        """
        Calculate task execution cost based on organs used and time.

        Args:
            result: Task execution result
            execution_time: Time taken to execute
            wealth: Current borg wealth

        Returns:
            Cost information dictionary
        """
        from decimal import Decimal

        total_cost = Decimal('0')
        organ_costs = {}

        # Calculate costs for organs used during execution
        organs_used = result.get('organs_used', [])
        for organ_name in organs_used:
            # Get organ price cap from current DNA if available
            price_cap = Decimal('0.001')  # Default fallback
            if hasattr(self, '_current_dna') and self._current_dna:
                for organ in self._current_dna.organs:
                    if organ.name == organ_name:
                        price_cap = Decimal(str(organ.price_cap))
                        break

            # Use price cap as cost estimate (simplified for Phase 1)
            organ_costs[organ_name] = price_cap
            total_cost += price_cap

        # Add base execution cost (time-based)
        base_execution_cost = Decimal('0.0001') * Decimal(str(execution_time))
        total_cost += base_execution_cost

        # Calculate cell costs from current DNA
        cell_costs = {}
        if hasattr(self, '_current_dna') and self._current_dna:
            for cell in self._current_dna.cells:
                cell_costs[cell.name] = Decimal(str(cell.cost_estimate))
                total_cost += cell_costs[cell.name]

        cost_info = {
            'total_cost': str(total_cost),
            'organ_costs': {k: str(v) for k, v in organ_costs.items()},
            'cell_costs': {k: str(v) for k, v in cell_costs.items()},
            'execution_cost': str(base_execution_cost),
            'execution_time': execution_time,
            'currency': 'DOT',
            'wealth_sufficient': wealth is None or float(wealth) >= float(total_cost),
            'cost_breakdown': {
                'organs': str(sum(Decimal(str(v)) for v in organ_costs.values())),
                'cells': str(sum(Decimal(str(v)) for v in cell_costs.values())),
                'execution': str(base_execution_cost)
            }
        }

        return cost_info

    def calculate_phenotype_cost(self, dna: BorgDNA) -> Dict[str, Any]:
        """
        Calculate total cost of building and maintaining a phenotype.

        Args:
            dna: BorgDNA to calculate costs for

        Returns:
            Cost breakdown dictionary with decimal precision
        """
        from decimal import Decimal, getcontext

        # Set high precision for DOT calculations
        getcontext().prec = 10

        total_cost = Decimal('0')
        cell_costs = {}
        organ_costs = {}

        # Calculate cell costs
        for cell in dna.cells:
            cell_cost = Decimal(str(cell.cost_estimate))
            cell_costs[cell.name] = cell_cost
            total_cost += cell_cost

        # Calculate organ costs (price caps)
        for organ in dna.organs:
            organ_cost = Decimal(str(organ.price_cap))
            organ_costs[organ.name] = organ_cost
            total_cost += organ_cost

        # Add base phenotype maintenance cost
        base_cost = Decimal('0.001')  # Fixed cost per phenotype
        total_cost += base_cost

        return {
            'total_cost': str(total_cost),
            'cell_costs': {k: str(v) for k, v in cell_costs.items()},
            'organ_costs': {k: str(v) for k, v in organ_costs.items()},
            'base_cost': str(base_cost),
            'currency': 'DOT',
            'cost_breakdown': {
                'cells': str(sum(Decimal(str(v)) for v in cell_costs.values())),
                'organs': str(sum(Decimal(str(v)) for v in organ_costs.values())),
                'base': str(base_cost)
            },
            'decimal_precision': getcontext().prec
        }