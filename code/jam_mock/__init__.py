"""
JAM Mock Interface

Mock implementation of JAM on-chain storage for Phase 1 prototyping.
"""

from .interface import JAMInterface, JAMMockInterface, JAMMode
from .kusama_adapter import WestendAdapter
from .local_mock import LocalJAMMock
from .recovery import OnChainRecovery

# Backward compatibility alias
KusamaAdapter = WestendAdapter

__all__ = [
    'JAMInterface',
    'JAMMockInterface',
    'JAMMode',
    'WestendAdapter',
    'KusamaAdapter',  # Backward compatibility
    'LocalJAMMock',
    'OnChainRecovery'
]