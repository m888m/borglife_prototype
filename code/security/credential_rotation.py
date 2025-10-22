from datetime import datetime, timedelta

class CredentialRotationManager:
    """Manage credential rotation for Docker MCP organs"""

    ROTATION_INTERVALS = {
        'gmail': timedelta(days=90),
        'stripe': timedelta(days=30),
        'bitcoin': timedelta(days=180)
    }

    def check_rotation_needed(self, organ_name: str) -> bool:
        """Check if credential rotation is due"""
        # Query last rotation date from Supabase
        # Compare against rotation interval
        pass

    async def rotate_credential(self, organ_name: str):
        """
        Rotate credential for Docker MCP organ

        Steps:
        1. Generate new credential via service API
        2. Update environment variable
        3. Restart container with new credential
        4. Validate new credential works
        5. Revoke old credential
        6. Log rotation event
        """
        pass