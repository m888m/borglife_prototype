#!/usr/bin/env python3
"""
Westend Balance Check Script - FIXED VERSION
Test connection to live Westend network and check dispenser balance with proper SCALE codec.
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from scalecodec import ScaleDecoder, ScaleType
    from scalecodec.type_registry import load_type_registry_preset
    SCALE_AVAILABLE = True
except ImportError:
    print("⚠️  SCALE codec not available - install with: pip install scalecodec")
    SCALE_AVAILABLE = False
    ScaleDecoder = None
    load_type_registry_preset = None

import requests
from substrateinterface import Keypair, SubstrateInterface


class WestendBalanceChecker:
    """Fixed Westend balance checker with proper SCALE decoding."""

    def __init__(self, endpoint: str = "https://westend.api.onfinality.io/public"):
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        # Initialize SCALE codec
        self.scale_decoder = None
        if SCALE_AVAILABLE:
            try:
                load_type_registry_preset("westend")
                self.scale_decoder = ScaleDecoder.get_decoder_class('AccountInfo')
                print("✅ SCALE codec initialized for Westend")
            except Exception as e:
                print(f"⚠️  SCALE codec initialization failed: {e}")

        # Initialize substrate-interface for WebSocket queries
        self.substrate = None
        try:
            self.substrate = SubstrateInterface(
                url="wss://westend.api.onfinality.io/public-ws",
                ss58_format=42
            )
            print("✅ WebSocket connection established")
        except Exception as e:
            print(f"⚠️  WebSocket connection failed: {e}")

    def get_chain_info(self) -> Optional[Dict[str, Any]]:
        """Get basic chain information."""
        payload = {'jsonrpc': '2.0', 'method': 'system_chain', 'params': [], 'id': 1}
        response = self.session.post(self.endpoint, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result.get('result')
        return None

    def get_block_number(self) -> Optional[int]:
        """Get current block number."""
        payload = {'jsonrpc': '2.0', 'method': 'chain_getHeader', 'params': [], 'id': 1}
        response = self.session.post(self.endpoint, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('result') and 'number' in result['result']:
                return int(result['result']['number'], 16)
        return None

    def get_account_balance_websocket(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account balance using substrate-interface WebSocket (RECOMMENDED)."""
        if not self.substrate:
            return None

        try:
            account_info = self.substrate.query(
                module='System',
                storage_function='Account',
                params=[address]
            )

            if account_info.value and 'data' in account_info.value:
                data = account_info.value['data']
                return {
                    'free': data.get('free', 0),
                    'reserved': data.get('reserved', 0),
                    'misc_frozen': data.get('misc_frozen', 0),
                    'fee_frozen': data.get('fee_frozen', 0)
                }
        except Exception as e:
            print(f"WebSocket balance query failed: {e}")

        return None

    def get_account_balance_raw(self, address: str) -> Optional[str]:
        """Get raw account balance data (SCALE encoded) using manual storage key."""
        try:
            # Manual key generation using proper Substrate hashing
            keypair = Keypair(ss58_address=address)
            pubkey_bytes = keypair.public_key

            # Use xxhash for TwoX128 (proper Substrate implementation)
            import xxhash
            system_hash = xxhash.xxh128(b"System").digest()[:16]  # TwoX128
            account_hash = xxhash.xxh128(b"Account").digest()[:16]  # TwoX128

            # Blake2_128Concat for the address
            import hashlib
            pubkey_hash = hashlib.blake2b(pubkey_bytes, digest_size=16).digest()

            # Concatenate: TwoX128(System) + TwoX128(Account) + Blake2_128Concat(address)
            storage_key = system_hash + account_hash + pubkey_hash + pubkey_bytes
            storage_key_hex = '0x' + storage_key.hex()

            # Query storage
            payload = {
                'jsonrpc': '2.0',
                'method': 'state_getStorage',
                'params': [storage_key_hex],
                'id': 1
            }

            response = self.session.post(self.endpoint, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get('result')

        except Exception as e:
            print(f"Raw balance query failed: {e}")

        return None

    def decode_scale_balance(self, raw_hex: str) -> Optional[Dict[str, Any]]:
        """Decode SCALE-encoded account balance data."""
        if not SCALE_AVAILABLE or not self.scale_decoder or not raw_hex:
            return None

        try:
            # Remove 0x prefix if present
            hex_data = raw_hex[2:] if raw_hex.startswith('0x') else raw_hex

            # Decode SCALE data
            account_info = self.scale_decoder.decode(hex_data)

            return {
                'nonce': account_info.get('nonce', 0),
                'consumers': account_info.get('consumers', 0),
                'providers': account_info.get('providers', 0),
                'sufficients': account_info.get('sufficients', 0),
                'data': {
                    'free': account_info['data'].get('free', 0),
                    'reserved': account_info['data'].get('reserved', 0),
                    'misc_frozen': account_info['data'].get('misc_frozen', 0),
                    'fee_frozen': account_info['data'].get('fee_frozen', 0)
                }
            }

        except Exception as e:
            print(f"SCALE decoding failed: {e}")
            return None


async def main():
    """Main balance check function."""
    print("🔍 WESTEND BALANCE CHECK - FIXED VERSION")
    print("=" * 60)

    # Dispenser address
    dispenser_address = "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD"

    # Initialize checker
    checker = WestendBalanceChecker()

    # Test basic connectivity
    print("\n🌐 Testing Westend connectivity...")
    chain = checker.get_chain_info()
    if chain:
        print(f"✅ Connected to: {chain}")
    else:
        print("❌ Failed to connect to Westend")
        return

    block_num = checker.get_block_number()
    if block_num:
        print(f"✅ Current block: {block_num:,}")
    else:
        print("❌ Failed to get block number")
        return

    # Check dispenser account
    print(f"\n💰 Checking dispenser balance: {dispenser_address}")

    # Method 1: WebSocket query (RECOMMENDED)
    print("\n📊 Method 1: WebSocket Query (Recommended)")
    ws_balance = checker.get_account_balance_websocket(dispenser_address)
    if ws_balance:
        free_balance = ws_balance['free']
        wnd_balance = free_balance / (10 ** 12)
        print("✅ WebSocket Balance:")
        print(f"   Free: {free_balance:,} planck ({wnd_balance:.6f} WND)")
        print(f"   Reserved: {ws_balance['reserved']:,} planck")
        print(f"   Frozen: {ws_balance['misc_frozen']:,} planck")

        if wnd_balance > 0:
            print("🎉 Dispenser has WND balance!")
        else:
            print("⚠️  Dispenser balance is zero")
    else:
        print("❌ WebSocket balance query failed")

    # Method 2: Raw SCALE data
    print("\n📊 Method 2: Raw SCALE Data + Manual Decoding")
    raw_data = checker.get_account_balance_raw(dispenser_address)
    if raw_data:
        print(f"✅ Raw storage data: {raw_data[:100]}...")

        decoded_balance = checker.decode_scale_balance(raw_data)
        if decoded_balance:
            free_balance = decoded_balance['data']['free']
            wnd_balance = free_balance / (10 ** 12)
            print("✅ SCALE Decoded Balance:")
            print(f"   Free: {free_balance:,} planck ({wnd_balance:.6f} WND)")
            print(f"   Reserved: {decoded_balance['data']['reserved']:,} planck")
            print(f"   Nonce: {decoded_balance['nonce']}")
        else:
            print("❌ SCALE decoding failed")
    else:
        print("❌ Raw balance data query failed")

    print("\n" + "=" * 60)
    print("BALANCE CHECK COMPLETE")

    # Summary
    if ws_balance and ws_balance['free'] > 0:
        wnd_amount = ws_balance['free'] / (10 ** 12)
        print(f"📋 SUMMARY: Dispenser has {wnd_amount:.6f} WND available for transfers")
    else:
        print("📋 SUMMARY: Unable to confirm dispenser balance")


if __name__ == "__main__":
    asyncio.run(main())