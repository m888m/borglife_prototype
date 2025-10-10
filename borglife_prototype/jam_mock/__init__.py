"""
JAM Mock Module for BorgLife Phase 1

Provides mock implementations of JAM (Join-Accumulate Machine) functionality
for development and testing before real JAM deployment.
"""

from .interface import JAMInterface
from .local_mock import LocalJAMMock
from .kusama_adapter import KusamaAdapter

__all__ = ['JAMInterface', 'LocalJAMMock', 'KusamaAdapter']