"""
Phenotype Builder for BorgLife Phase 1

Builds executable borg phenotypes from DNA using Archon integration.
Phenotypes consist of cells (PydanticAI agents) and organs (MCP tools).
"""

import asyncio
from typing import Dict, Any, Callable, Optional
from .dna_parser import BorgDNA, Cell, Organ


class BorgPhenotype:
    """
    Executable borg phenotype (body) built from DNA.

    Contains cells (logic units) and organs (tool interfaces)
    that work together to execute tasks.
    """

    def __init__(self, dna: BorgDNA, archon_adapter):
        """
        Initialize phenotype.

        Args:
            dna: BorgDNA structure
            archon_adapter: Archon service adapter for tool/agent access
        """
        self.dna = dna
        self.archon_adapter = archon_adapter
        self.cells: Dict[str, Callable] = {}  # name -> cell function
        self.organs: Dict[str, Callable] = {}  # name -> organ function
        self.metadata = {
            'build_time': None,
            'cell_count': 0,
            'organ_count': 0,
            'total_cost_estimate': 0.0
        }

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task using cells and organs.

        Routes task to appropriate cell based on task type,
        allowing cells to invoke organs as needed.

        Args:
            task_description: Natural language task description

        Returns:
            Dict containing result, cost, and metadata
        """
        # Simple routing logic - in Phase 2 this would be more sophisticated
        if any(keyword in task_description.lower() for keyword in ['analyze', 'process', 'data']):
            cell_name = 'data_processor'
        elif any(keyword in task_description.lower() for keyword in ['decide', 'choose', 'strategy']):
            cell_name = 'decision_maker'
        else:
            cell_name = 'data_processor'  # Default fallback

        if cell_name not in self.cells:
            available_cells = list(self.cells.keys())
            return {
                'error': f'No suitable cell found for task. Available: {available_cells}',
                'task': task_description,
                'cost': 0.0
            }

        try:
            # Execute cell with access to organs
            result = await self.cells[cell_name](task_description, self.organs)

            return {
                'result': result,
                'cell_used': cell_name,
                'organs_accessed': list(self.organs.keys()),
                'cost': self._estimate_execution_cost(),
                'dna_hash': self.dna.compute_hash()
            }

        except Exception as e:
            return {
                'error': f'Execution failed: {str(e)}',
                'cell_used': cell_name,
                'cost': 0.0
            }

    def _estimate_execution_cost(self) -> float:
        """Estimate total execution cost based on DNA."""
        total_cost = 0.0
        for cell in self.dna.cells:
            total_cost += cell.cost_estimate
        for organ in self.dna.organs:
            total_cost += organ.price_cap
        return total_cost


class PhenotypeBuilder:
    """
    Builds executable phenotypes from DNA using Archon services.

    Integrates with Archon to create cells (PydanticAI agents)
    and organs (MCP tool callables).
    """

    def __init__(self, archon_adapter):
        """
        Initialize phenotype builder.

        Args:
            archon_adapter: Configured Archon service adapter
        """
        self.archon_adapter = archon_adapter

    async def build(self, dna: BorgDNA) -> BorgPhenotype:
        """
        Build phenotype from DNA.

        Process:
        1. Parse cells → create PydanticAI agents
        2. Parse organs → register MCP tool callables
        3. Validate phenotype integrity
        4. Return executable phenotype

        Args:
            dna: BorgDNA structure to build from

        Returns:
            BorgPhenotype ready for execution

        Raises:
            ValueError: If DNA is invalid or build fails
        """
        # Validate DNA first
        from .dna_parser import DNAParser
        validation_issues = DNAParser.validate_dna(dna)
        if validation_issues:
            raise ValueError(f"Invalid DNA: {validation_issues}")

        phenotype = BorgPhenotype(dna, self.archon_adapter)

        # Build cells (PydanticAI agents)
        for cell in dna.cells:
            cell_function = await self._build_cell(cell)
            phenotype.cells[cell.name] = cell_function

        # Register organs (MCP tools)
        for organ in dna.organs:
            organ_function = await self._register_organ(organ)
            phenotype.organs[organ.name] = organ_function

        # Validate phenotype
        await self._validate_phenotype(phenotype)

        # Update metadata
        phenotype.metadata.update({
            'build_time': asyncio.get_event_loop().time(),
            'cell_count': len(phenotype.cells),
            'organ_count': len(phenotype.organs),
            'total_cost_estimate': phenotype._estimate_execution_cost()
        })

        return phenotype

    async def _build_cell(self, cell: Cell) -> Callable:
        """
        Create cell function from DNA cell definition.

        Maps cell.logic_type to appropriate Archon agent type.

        Args:
            cell: Cell definition from DNA

        Returns:
            Async callable for cell execution
        """
        logic_type = cell.logic_type
        parameters = cell.parameters

        if logic_type == 'data_processing':
            # Use RagAgent for data processing tasks
            agent_type = 'RagAgent'

        elif logic_type == 'decision_making':
            # Use DocumentAgent for decision tasks
            agent_type = 'DocumentAgent'

        else:
            # Default to RagAgent
            agent_type = 'RagAgent'

        # Create cell function that uses Archon agent
        async def cell_function(task_description: str, organs: Dict[str, Callable]) -> str:
            """
            Execute cell logic using Archon agent.

            Args:
                task_description: Task to execute
                organs: Available organ functions

            Returns:
                Execution result
            """
            try:
                # Build prompt with organ availability
                organ_list = ", ".join(organs.keys())
                enhanced_prompt = f"""
                Task: {task_description}

                Available tools/organs: {organ_list}
                Cell type: {logic_type}
                Parameters: {parameters}

                Execute this task using your capabilities and available organs.
                """

                # Call Archon agent
                result = await self.archon_adapter.run_agent(
                    agent_type=agent_type,
                    prompt=enhanced_prompt,
                    parameters=parameters
                )

                return result.get('result', 'No result returned')

            except Exception as e:
                return f"Cell execution failed: {str(e)}"

        return cell_function

    async def _register_organ(self, organ: Organ) -> Callable:
        """
        Create organ callable from DNA organ definition.

        Maps organ.mcp_tool to Archon MCP tool invocation.

        Args:
            organ: Organ definition from DNA

        Returns:
            Async callable for organ invocation
        """
        mcp_tool = organ.mcp_tool

        async def organ_function(**kwargs) -> Any:
            """
            Invoke MCP tool through Archon adapter.

            Args:
                **kwargs: Tool-specific parameters

            Returns:
                Tool execution result
            """
            try:
                result = await self.archon_adapter.call_mcp_tool(
                    tool_name=mcp_tool,
                    parameters=kwargs
                )
                return result
            except Exception as e:
                return f"Organ invocation failed: {str(e)}"

        return organ_function

    async def _validate_phenotype(self, phenotype: BorgPhenotype) -> None:
        """
        Validate phenotype integrity.

        Checks:
        - All cells built successfully
        - All organs registered
        - DNA-phenotype hash consistency

        Args:
            phenotype: Phenotype to validate

        Raises:
            ValueError: If validation fails
        """
        # Check cell completeness
        expected_cells = {cell.name for cell in phenotype.dna.cells}
        actual_cells = set(phenotype.cells.keys())
        if expected_cells != actual_cells:
            missing = expected_cells - actual_cells
            extra = actual_cells - expected_cells
            raise ValueError(f"Cell mismatch - missing: {missing}, extra: {extra}")

        # Check organ completeness
        expected_organs = {organ.name for organ in phenotype.dna.organs}
        actual_organs = set(phenotype.organs.keys())
        if expected_organs != actual_organs:
            missing = expected_organs - actual_organs
            extra = actual_organs - expected_organs
            raise ValueError(f"Organ mismatch - missing: {missing}, extra: {extra}")

        # Verify DNA integrity
        if not phenotype.dna.verify_integrity():
            raise ValueError("DNA integrity check failed: H(D') != H(D)")

        # Test basic execution capability
        test_result = await phenotype.execute_task("Test phenotype validation")
        if 'error' in test_result:
            raise ValueError(f"Phenotype execution test failed: {test_result['error']}")