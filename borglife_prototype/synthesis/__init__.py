"""
Synthesis Module for BorgLife Phase 1

Handles DNA parsing, phenotype building, and borg synthesis
from Archon-integrated components.
"""

from .dna_parser import DNAParser, BorgDNA, DNAHeader, Cell, Organ
from .phenotype_builder import PhenotypeBuilder, BorgPhenotype

__all__ = [
    'DNAParser', 'BorgDNA', 'DNAHeader', 'Cell', 'Organ',
    'PhenotypeBuilder', 'BorgPhenotype'
]