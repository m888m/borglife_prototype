#!/usr/bin/env python3
"""
Westend Balance Check Script
Test connection to live Westend network and check dispenser balance with SCALE codec.
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
    print("✅ SCALE codec available")
except ImportError:
    print("⚠️  SCALE codec not available - install with: pip install scalecodec")
    SCALE_AVAILABLE = False
    ScaleDecoder = None
    load_type_registry_preset = None

# Try to import substrate-interface for fallback methods
try:
    from substrateinterface import SubstrateInterface
    SUBSTRATE_AVAILABLE = True
except ImportError:
    SUBSTRATE_AVAILABLE = False

import requests
from substrateinterface import Keypair


class WestendRPCClient:
    """HTTP-based Westend RPC client with SCALE decoding support."""

    def __init__(self, endpoint: str = "https://westend.api.onfinality.io/public"):
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        # Initialize SCALE codec if available
        self.scale_decoder = None
        if SCALE_AVAILABLE and load_type_registry_preset:
            try:
                # Load Westend type registry
                load_type_registry_preset("westend")
                self.scale_decoder = ScaleDecoder.get_decoder_class('AccountInfo')
                print("✅ SCALE codec initialized for Westend")
            except Exception as e:
                print(f"⚠️  SCALE codec initialization failed: {e}")
                self.scale_decoder = None
        else:
            print("⚠️  SCALE codec not available for balance decoding")

    def rpc_call(self, method: str, params: list = None, id: int = 1) -> Optional[Dict[str, Any]]:
        """Make RPC call with error handling."""
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params or [],
            'id': id
        }

        try:
            response = self.session.post(
                self.endpoint,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if 'error' in result:
                    print(f"RPC Error: {result['error']}")
                    return None
                return result.get('result')
            else:
                print(f"HTTP Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            print(f"Request failed: {e}")
            return None

    def get_chain_info(self) -> Optional[Dict[str, Any]]:
        """Get basic chain information."""
        return self.rpc_call('system_chain')

    def get_block_number(self) -> Optional[int]:
        """Get current block number."""
        header = self.rpc_call('chain_getHeader', [None])
        if header and 'number' in header:
            return int(header['number'], 16)
        return None

    def get_account_balance_raw(self, address: str) -> Optional[str]:
        """Get raw account balance data (SCALE encoded)."""
        storage_key = self._get_storage_key(address)
        if not storage_key:
            print(f"Could not generate storage key for address: {address}")
            return None

        print(f"🔑 Storage key: {storage_key}")
        result = self.rpc_call('state_getStorage', [storage_key])
        print(f"📊 Raw result: {result}")
        return result

    def get_account_balance_decoded(self, address: str) -> Optional[Dict[str, Any]]:
        """Get decoded account balance using SCALE codec with multiple fallback methods."""
        raw_data = self.get_account_balance_raw(address)
        if not raw_data:
            return None

        # Method 1: Try SCALE codec first
        if SCALE_AVAILABLE and self.scale_decoder:
            try:
                # Remove 0x prefix if present
                hex_data = raw_data[2:] if raw_data.startswith('0x') else raw_data

                # Decode SCALE data
                account_info = self.scale_decoder.decode(hex_data)

                return {
                    'nonce': account_info['nonce'],
                    'consumers': account_info['consumers'],
                    'providers': account_info['providers'],
                    'sufficients': account_info['sufficients'],
                    'data': {
                        'free': account_info['data']['free'],
                        'reserved': account_info['data']['reserved'],
                        'misc_frozen': account_info['data']['misc_frozen'],
                        'fee_frozen': account_info['data']['fee_frozen']
                    },
                    'decode_method': 'scale_codec'
                }

            except Exception as e:
                print(f"SCALE codec decoding failed: {e}")

        # Method 2: Try substrate-interface query method
        if SUBSTRATE_AVAILABLE:
            try:
                # Create temporary substrate connection
                substrate = SubstrateInterface(
                    url=self.endpoint.replace('https://', 'wss://').replace('http://', 'ws://'),
                    ss58_format=42
                )

                # Use substrate query method
                account_info = substrate.query(
                    module='System',
                    storage_function='Account',
                    params=[address]
                )

                if account_info.value:
                    data = account_info.value['data']
                    return {
                        'nonce': account_info.value.get('nonce', 0),
                        'consumers': account_info.value.get('consumers', 0),
                        'providers': account_info.value.get('providers', 0),
                        'sufficients': account_info.value.get('sufficients', 0),
                        'data': {
                            'free': data.get('free', 0),
                            'reserved': data.get('reserved', 0),
                            'misc_frozen': data.get('misc_frozen', 0),
                            'fee_frozen': data.get('fee_frozen', 0)
                        },
                        'decode_method': 'substrate_query'
                    }

            except Exception as e:
                print(f"Substrate query method failed: {e}")

        # Method 3: Manual hex decoding as final fallback
        try:
            manual_result = self._manual_decode_balance(raw_data)
            if manual_result:
                manual_result['decode_method'] = 'manual_hex'
                return manual_result
        except Exception as e:
            print(f"Manual decoding also failed: {e}")

        print("All decoding methods failed")
        return None

    def _manual_decode_balance(self, raw_hex: str) -> Optional[Dict[str, Any]]:
        """Manually decode balance data from hex with improved accuracy."""
        try:
            # Remove 0x prefix
            hex_data = raw_hex[2:] if raw_hex.startswith('0x') else raw_hex

            # Convert hex to bytes
            data_bytes = bytes.fromhex(hex_data)

            if len(data_bytes) < 16:
                print(f"Data too short for manual decoding: {len(data_bytes)} bytes")
                return None

            # AccountInfo structure in SCALE (Westend):
            # - nonce: Compact<u32> (1-5 bytes, usually 1-2)
            # - consumers: u32 (4 bytes)
            # - providers: u32 (4 bytes)
            # - sufficients: u32 (4 bytes)
            # - data: AccountData (24 bytes for free + reserved + misc_frozen + fee_frozen)

            # Parse compact encoded nonce
            nonce, nonce_bytes = self._decode_compact_u32(data_bytes)
            offset = nonce_bytes

            # Parse the u32 fields
            consumers = int.from_bytes(data_bytes[offset:offset+4], byteorder='little')
            offset += 4
            providers = int.from_bytes(data_bytes[offset:offset+4], byteorder='little')
            offset += 4
            sufficients = int.from_bytes(data_bytes[offset:offset+4], byteorder='little')
            offset += 4

            # Parse AccountData (4 x u128 = 64 bytes)
            if len(data_bytes) >= offset + 64:
                free = int.from_bytes(data_bytes[offset:offset+16], byteorder='little')
                offset += 16
                reserved = int.from_bytes(data_bytes[offset:offset+16], byteorder='little')
                offset += 16
                misc_frozen = int.from_bytes(data_bytes[offset:offset+16], byteorder='little')
                offset += 16
                fee_frozen = int.from_bytes(data_bytes[offset:offset+16], byteorder='little')

                return {
                    'nonce': nonce,
                    'consumers': consumers,
                    'providers': providers,
                    'sufficients': sufficients,
                    'data': {
                        'free': free,
                        'reserved': reserved,
                        'misc_frozen': misc_frozen,
                        'fee_frozen': fee_frozen
                    },
                    'manually_decoded': True
                }
            else:
                print(f"Insufficient data for AccountData parsing: need {offset + 64}, got {len(data_bytes)}")
                return None

        except Exception as e:
            print(f"Manual decoding failed: {e}")
            return None

    def _decode_compact_u32(self, data: bytes) -> tuple[int, int]:
        """Decode compact encoded u32 and return (value, bytes_consumed)."""
        if not data:
            return 0, 0

        first_byte = data[0]

        if first_byte < 64:  # Single byte
            return first_byte >> 2, 1
        elif first_byte < 128:  # Two bytes
            if len(data) < 2:
                return 0, 0
            value = ((first_byte & 0x3F) << 8) | data[1]
            return value, 2
        elif first_byte < 192:  # Four bytes
            if len(data) < 4:
                return 0, 0
            value = ((first_byte & 0x3F) << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
            return value, 4
        else:  # Big integer (not expected for nonce)
            return 0, 1

    def _get_storage_key(self, address: str) -> Optional[str]:
        """Generate storage key for account balance."""
        # Use manual key generation as primary method
        try:
            return self._manual_storage_key(address)
        except Exception as e:
            print(f"Failed to generate storage key: {e}")
            return None

    def _manual_storage_key(self, address: str) -> str:
        """Manually generate storage key for System.Account."""
        # Decode SS58 address to get public key
        keypair = Keypair(ss58_address=address)
        pubkey_bytes = keypair.public_key

        # Use the correct Substrate storage key format
        # System.Account storage key = TwoX128("System") + TwoX128("Account") + Blake2_128Concat(public_key)
        # But we need to use the exact format that matches the chain

        # Let's try a different approach - use the known working key from substrate-interface if possible
        try:
            from substrateinterface import SubstrateInterface
            temp_substrate = SubstrateInterface(url=self.endpoint.replace('https://', 'wss://').replace('http://', 'ws://'), ss58_format=42)
            # Try the correct method name for this version
            storage_key_obj = temp_substrate.create_storage_key("System", "Account", [address])
            # Convert to hex string for JSON serialization
            storage_key = storage_key_obj.to_hex()
            return storage_key
        except Exception as e:
            print(f"Substrate key generation failed: {e}, using manual calculation")

            # Manual calculation as fallback
            system_hash = self._xxhash128(b"System")
            account_hash = self._xxhash128(b"Account")
            pubkey_hash = self._blake2_128(pubkey_bytes)

            storage_key = system_hash + account_hash + pubkey_hash + pubkey_bytes
            return '0x' + storage_key.hex()

    def _xxhash128(self, data: bytes) -> bytes:
        """Calculate xxHash128 (TwoX128) as used in Substrate."""
        try:
            import xxhash
            return xxhash.xxh128(data).digest()[:16]
        except ImportError:
            # Fallback to blake2b if xxhash not available
            return self._blake2_128(data)

    def _blake2_128(self, data: bytes) -> bytes:
        """Calculate Blake2_128 as used in Substrate."""
        import hashlib
        return hashlib.blake2b(data, digest_size=16).digest()


async def main():
    """Main balance check function."""
    print("🔍 WESTEND BALANCE CHECK")
    print("=" * 50)

    # Dispenser address from config
    dispenser_address = "5HbUDboFxDv7DTAD1QKTNxc3NAQx1i92GwCUoc4hb9AUi9vi"

    # Initialize RPC client
    rpc = WestendRPCClient()

    # Test basic connectivity
    print("\n🌐 Testing Westend connectivity...")
    chain = rpc.get_chain_info()
    if chain:
        print(f"✅ Connected to: {chain}")
    else:
        print("❌ Failed to connect to Westend")
        return

    block_num = rpc.get_block_number()
    if block_num:
        print(f"✅ Current block: {block_num:,}")
    else:
        print("❌ Failed to get block number")
        return

    # Check dispenser account
    print(f"\n💰 Checking dispenser balance: {dispenser_address}")

    # Raw balance data
    raw_balance = rpc.get_account_balance_raw(dispenser_address)
    if raw_balance:
        print(f"✅ Raw balance data: {raw_balance[:100]}...")
    elif raw_balance is None:
        print("❌ Account not found (balance is null) - dispenser needs funding")
        print("   This is expected for a new account with zero balance")
        print("   To fund the dispenser, send WND tokens to this address")
        return
    else:
        print("❌ Failed to get raw balance data")
        return

    # Decoded balance data
    decoded_balance = rpc.get_account_balance_decoded(dispenser_address)
    if decoded_balance:
        free_balance = decoded_balance['data']['free']
        wnd_balance = free_balance / (10 ** 12)  # Convert from planck to WND

        decode_method = decoded_balance.get('decode_method', 'unknown')
        print(f"✅ Balance decoded using: {decode_method}")
        print(f"   Free: {free_balance:,} planck ({wnd_balance:.6f} WND)")
        print(f"   Reserved: {decoded_balance['data']['reserved']:,} planck")
        print(f"   Nonce: {decoded_balance['nonce']}")

        if wnd_balance > 0:
            print("🎉 Dispenser has WND balance!")
        else:
            print("⚠️  Dispenser balance is zero - needs funding")
    else:
        print("❌ All decoding methods failed")
        print("   This should not happen with valid account data")

    print("\n" + "=" * 50)
    print("BALANCE CHECK COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())