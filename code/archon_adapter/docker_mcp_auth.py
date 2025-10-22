from typing import Dict, Optional
import os

class DockerMCPAuthManager:
    """Manage authentication for Docker MCP organs"""

    def __init__(self):
        self.credentials = {}

    def add_credential(self, organ_name: str, cred_type: str, value: str):
        """Add credential for organ"""
        if organ_name not in self.credentials:
            self.credentials[organ_name] = {}
        self.credentials[organ_name][cred_type] = value

    def get_credential(self, organ_name: str, cred_type: str = None) -> Optional[str]:
        """Get credential for organ"""
        if organ_name not in self.credentials:
            return None

        if cred_type:
            return self.credentials[organ_name].get(cred_type)
        else:
            # Return first available credential
            creds = self.credentials[organ_name]
            return next(iter(creds.values())) if creds else None

    def load_from_env(self):
        """Load credentials from environment variables"""
        # Gmail
        if 'GMAIL_APP_PASSWORD' in os.environ:
            self.add_credential('gmail', 'app_password', os.environ['GMAIL_APP_PASSWORD'])

        # Stripe
        if 'STRIPE_API_KEY' in os.environ:
            self.add_credential('stripe', 'api_key', os.environ['STRIPE_API_KEY'])

        # Bitcoin
        if 'BITCOIN_RPC_USER' in os.environ and 'BITCOIN_RPC_PASS' in os.environ:
            self.add_credential('bitcoin', 'rpc_user', os.environ['BITCOIN_RPC_USER'])
            self.add_credential('bitcoin', 'rpc_pass', os.environ['BITCOIN_RPC_PASS'])