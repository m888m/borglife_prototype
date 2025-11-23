from enum import Enum
from typing import Optional


class BorgState(Enum):
    CREATED = "created"  # DNA encoded, not yet activated
    ACTIVATING = "activating"  # Building phenotype
    ACTIVE = "active"  # Running and accepting tasks
    PAUSED = "paused"  # Temporarily stopped
    TERMINATED = "terminated"  # Permanently stopped
    RESURRECTING = "resurrecting"  # Rebuilding from on-chain DNA


class BorgLifecycleManager:
    """Manage borg lifecycle states"""

    async def create_borg(self, dna: BorgDNA, sponsor_id: str) -> str:
        """
        Create new borg from DNA

        Returns:
            borg_id
        """
        # Store DNA in Supabase
        # Set state to CREATED
        # Return borg_id
        pass

    async def activate_borg(self, borg_id: str) -> BorgPhenotype:
        """
        Activate borg (build phenotype)

        State: CREATED → ACTIVATING → ACTIVE
        """
        # Load DNA from storage
        # Build phenotype via synthesis module
        # Set state to ACTIVE
        # Return phenotype
        pass

    async def pause_borg(self, borg_id: str):
        """
        Pause borg execution

        State: ACTIVE → PAUSED
        """
        # Stop accepting new tasks
        # Complete in-flight tasks
        # Set state to PAUSED
        pass

    async def terminate_borg(self, borg_id: str):
        """
        Permanently terminate borg

        State: * → TERMINATED
        """
        # Complete in-flight tasks
        # Final wealth settlement
        # Store final DNA snapshot on-chain
        # Set state to TERMINATED
        pass

    async def resurrect_borg(self, dna_hash: str) -> str:
        """
        Resurrect borg from on-chain DNA

        State: TERMINATED → RESURRECTING → ACTIVE
        """
        # Retrieve DNA from chain
        # Decode to BorgDNA
        # Build new phenotype
        # Create new borg_id
        # Set state to ACTIVE
        pass
