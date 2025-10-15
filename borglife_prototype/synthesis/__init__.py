"""
BorgLife Synthesis Module

Handles DNA parsing, phenotype building, and borg lifecycle management.
"""

from .dna_parser import DNAParser, BorgDNA, DNAHeader, Cell, Organ
from .phenotype_builder import PhenotypeBuilder, BorgPhenotype
from .phenotype_encoder import PhenotypeEncoder
from .cell_organ_protocol import CellOrganBridge
from .dna_validator import DNAValidator

__all__ = [
    'DNAParser',
    'BorgDNA',
    'DNAHeader',
    'Cell',
    'Organ',
    'PhenotypeBuilder',
    'BorgPhenotype',
    'PhenotypeEncoder',
    'CellOrganBridge',
    'DNAValidator'
]