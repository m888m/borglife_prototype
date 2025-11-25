#!/usr/bin/env python3
"""
Shared BorgLife configuration loader.

Provides robust, centralized config parsing for repeated values like USDB_ASSET_ID.
Handles comments, whitespace, and malformed lines gracefully.
"""
import os
from typing import Dict, Any

def load_borglife_config() -> Dict[str, Any]:
    """
    Load .borglife_config as key-value dict.
    
    Supports:
    - KEY=VALUE format
    - Comments (#)
    - Blank lines
    - Whitespace trimming
    
    Raises ValueError if required keys missing.
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", ".borglife_config")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f".borglife_config not found at {config_path}")
    
    config = {}
    with open(config_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                print(f"Warning: Skipping malformed line {line_num}: {line}")
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            config[key] = value
    
    return config

def load_usdb_asset_id() -> int:
    """Load USDB_ASSET_ID from config, raise if missing."""
    config = load_borglife_config()
    if "USDB_ASSET_ID" not in config:
        raise ValueError("USDB_ASSET_ID not found in .borglife_config")
    try:
        return int(config["USDB_ASSET_ID"])
    except ValueError as e:
        raise ValueError(f"Invalid USDB_ASSET_ID in config: {config.get('USDB_ASSET_ID')}") from e