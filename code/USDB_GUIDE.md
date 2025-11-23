[`code/USDB_GUIDE.md`](code/USDB_GUIDE.md:1)
# USDB Stablecoin Guide

## Overview
USDB is the BorgLife stablecoin on Westend Asset Hub for economic operations.

Current ID: 50000313 (see [`code/.borglife_config`](code/.borglife_config))

## Prerequisites
- Funded dispenser in keyring (13+ WND)
- substrate-interface installed

## Creation Workflow

1. **Verify Keyring**
```bash
. ../.venv/bin/activate && python3 scripts/check_keyring.py
```

2. **Create Asset**
```bash
. ../.venv/bin/activate && python3 scripts/create_usdb_asset.py
```

3. **Verify**
Balance query shows 1M USDB in dispenser.

## Verification

**PolkadotJS Apps**
- RPC: wss://westend-asset-hub-rpc.polkadot.io
- Account: 5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD
- Assets tab, search ID 50000313

**Query Script**
```python
from substrateinterface import SubstrateInterface
sub = SubstrateInterface('wss://westend-asset-hub-rpc.polkadot.io', ss58_format=42)
balance = sub.query('Assets', 'Account', [50000313, '5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD'])
print(f"Balance: {int(balance.value['balance']) if balance.value else 0}")
```

## Troubleshooting
See [`code/TROUBLESHOOTING.md`](code/TROUBLESHOOTING.md)