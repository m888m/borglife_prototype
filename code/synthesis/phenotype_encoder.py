from typing import Dict, Any
from .dna_parser import BorgDNA, DNAHeader, Cell, Organ
from .phenotype_builder import BorgPhenotype

class PhenotypeEncoder:
    """Encode working phenotype back to DNA structure"""

    def encode(self, phenotype: BorgPhenotype) -> BorgDNA:
        """
        Convert phenotype to DNA

        Captures:
        1. Cell configurations (model, parameters, cost history)
        2. Organ selections (URLs, tools used, success rates)
        3. Performance metrics (execution times, costs)
        4. Runtime optimizations (parameter tuning)
        """
        # Extract header from phenotype metadata
        header = DNAHeader(
            code_length=self._estimate_code_length(phenotype),
            gas_limit=phenotype.dna.header.gas_limit,
            service_index=phenotype.dna.header.service_index
        )

        # Encode cells with runtime state
        cells = []
        for cell_name, cell_instance in phenotype.cells.items():
            cells.append(Cell(
                name=cell_name,
                logic_type=cell_instance.logic_type,
                parameters=self._extract_cell_params(cell_instance),
                cost_estimate=self._calculate_avg_cost(cell_instance)
            ))

        # Encode organs with usage statistics
        organs = []
        for organ_name, organ_callable in phenotype.organs.items():
            organs.append(Organ(
                name=organ_name,
                mcp_tool=organ_callable.tool_name,
                url=organ_callable.endpoint,
                abi_version=organ_callable.version,
                price_cap=self._calculate_price_cap(organ_callable)
            ))

        return BorgDNA(
            header=header,
            cells=cells,
            organs=organs,
            manifesto_hash=phenotype.dna.manifesto_hash
        )

    def _extract_cell_params(self, cell_instance) -> Dict[str, Any]:
        """Extract cell parameters including runtime tuning"""
        # Get base parameters
        params = cell_instance.base_parameters.copy()

        # Add runtime optimizations
        if hasattr(cell_instance, 'optimized_params'):
            params.update(cell_instance.optimized_params)

        return params

    def _calculate_avg_cost(self, cell_instance) -> float:
        """Calculate average cost from execution history"""
        if not hasattr(cell_instance, 'execution_history'):
            return cell_instance.cost_estimate

        costs = [e['cost'] for e in cell_instance.execution_history]
        return sum(costs) / len(costs) if costs else cell_instance.cost_estimate