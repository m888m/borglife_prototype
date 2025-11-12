#!/usr/bin/env python3
"""
USDB Faucet for Test Borgs

Provides a simple faucet interface for distributing USDB to test borgs.
Replaces WND faucet dependency for economic testing.
"""

import os
import sys
import asyncio
from typing import Dict, Any, Optional
from decimal import Decimal
import json

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.usdb_distribution import USDBDistributor

class USDBFaucet:
    """Simple faucet for USDB distribution to test borgs."""

    def __init__(self):
        self.distributor = USDBDistributor()
        self.faucet_amount = Decimal('50.0')  # Default faucet amount

    async def request_funds(self, borg_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Request USDB funds for a borg.

        Args:
            borg_id: Borg ID requesting funds
            amount: Amount to request (default: faucet_amount)

        Returns:
            Faucet request result
        """
        if amount is None:
            amount = self.faucet_amount

        print(f"🚰 Faucet request: {borg_id} requesting {amount} USDB")

        # Check if borg already has funds (prevent abuse)
        current_balance = self.distributor.address_manager.get_balance(borg_id, 'USDB')
        if current_balance and current_balance > 0:
            balance_tokens = Decimal(str(current_balance)) / Decimal('1000000000000')
            if balance_tokens >= Decimal('10.0'):  # Already has significant funds
                return {
                    'success': False,
                    'error': 'Borg already has sufficient funds',
                    'current_balance': str(balance_tokens)
                }

        # Distribute funds
        result = await self.distributor._simulate_distribution(borg_id, amount)

        if result:
            return {
                'success': True,
                'borg_id': borg_id,
                'amount_distributed': str(amount),
                'message': f'Successfully distributed {amount} USDB to {borg_id}'
            }
        else:
            return {
                'success': False,
                'error': 'Distribution failed',
                'borg_id': borg_id
            }

    async def get_faucet_status(self) -> Dict[str, Any]:
        """Get faucet status and recent distributions."""
        status = await self.distributor.get_distribution_status()
        status.update({
            'faucet_amount': str(self.faucet_amount),
            'faucet_active': True
        })
        return status

    async def bulk_faucet_request(self, borg_ids: List[str]) -> Dict[str, Any]:
        """Request funds for multiple borgs."""
        results = []
        successful = 0

        for borg_id in borg_ids:
            result = await self.request_funds(borg_id)
            results.append(result)
            if result['success']:
                successful += 1

        return {
            'total_requests': len(borg_ids),
            'successful': successful,
            'failed': len(borg_ids) - successful,
            'results': results
        }

async def main():
    """Main entry point for faucet."""
    if len(sys.argv) < 2:
        print("Usage: python usdb_faucet.py <command> [args...]")
        print("Commands:")
        print("  request <borg_id> [amount]     - Request funds for a borg")
        print("  bulk <borg_id1> <borg_id2> ... - Request funds for multiple borgs")
        print("  status                         - Show faucet status")
        sys.exit(1)

    command = sys.argv[1]

    try:
        faucet = USDBFaucet()

        if command == 'request':
            if len(sys.argv) < 3:
                print("❌ Borg ID required")
                sys.exit(1)

            borg_id = sys.argv[2]
            amount = Decimal(sys.argv[3]) if len(sys.argv) > 3 else None

            result = await faucet.request_funds(borg_id, amount)
            print(json.dumps(result, indent=2, default=str))

        elif command == 'bulk':
            if len(sys.argv) < 3:
                print("❌ At least one borg ID required")
                sys.exit(1)

            borg_ids = sys.argv[2:]
            result = await faucet.bulk_faucet_request(borg_ids)
            print(json.dumps(result, indent=2, default=str))

        elif command == 'status':
            result = await faucet.get_faucet_status()
            print(json.dumps(result, indent=2, default=str))

        else:
            print(f"❌ Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())