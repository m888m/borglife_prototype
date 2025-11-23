#!/usr/bin/env python3
"""
Live USDB Stablecoin Creator for Westend Asset Hub
Standalone script using keyring dispenser key.
"""

import asyncio
import os
import sys
from decimal import Decimal
from typing import Any, Dict, Optional

import keyring
from substrateinterface import Keypair, SubstrateInterface

sys.path.insert(0, os.path.dirname(__file__))


async def main():
    # RPC
    rpc_url = "wss://westend-asset-hub-rpc.polkadot.io"

    # Load dispenser private key
    service
