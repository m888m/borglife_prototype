# borglife_prototype/tests/mocks/jam_mock.py
"""
Mock implementation of JAM (Justification and Motivation) interface for testing.

Provides deterministic responses for economic model interactions without
requiring actual JAM service connections.
"""

import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal


class JAMInterfaceMock:
    """
    Mock JAM interface for testing economic model interactions.

    Simulates wealth tracking, cost calculations, and billing operations
    with configurable behavior for testing different scenarios.
    """

    def __init__(self):
        self.wealth_balances: Dict[str, Decimal] = {}
        self.transaction_history: List[Dict[str, Any]] = []
        self.should_fail = False
        self.fail_on_next_calls = 0

    async def get_wealth_balance(self, borg_id: str) -> Decimal:
        """Get current wealth balance for a borg."""
        self._record_call('get_wealth_balance', borg_id=borg_id)

        if self._should_fail():
            raise Exception(f"Mock JAM failure: get_wealth_balance for {borg_id}")

        return self.wealth_balances.get(borg_id, Decimal('100.0'))  # Default 100 DOT

    async def update_wealth_balance(self, borg_id: str, amount: Decimal, operation: str) -> bool:
        """Update wealth balance for a borg."""
        self._record_call('update_wealth_balance', borg_id=borg_id, amount=amount, operation=operation)

        if self._should_fail():
            raise Exception(f"Mock JAM failure: update_wealth_balance for {borg_id}")

        current_balance = self.wealth_balances.get(borg_id, Decimal('100.0'))
        new_balance = current_balance + amount

        # Prevent negative balances
        if new_balance < 0:
            return False

        self.wealth_balances[borg_id] = new_balance

        # Record transaction
        self.transaction_history.append({
            'borg_id': borg_id,
            'amount': str(amount),
            'operation': operation,
            'balance_before': str(current_balance),
            'balance_after': str(new_balance),
            'timestamp': asyncio.get_event_loop().time()
        })

        return True

    async def deduct_cost(self, borg_id: str, cost: Decimal, description: str) -> bool:
        """Deduct cost from borg wealth."""
        return await self.update_wealth_balance(borg_id, -cost, f"cost_deduction: {description}")

    async def add_reward(self, borg_id: str, reward: Decimal, description: str) -> bool:
        """Add reward to borg wealth."""
        return await self.update_wealth_balance(borg_id, reward, f"reward: {description}")

    async def calculate_task_cost(self, task_type: str, complexity: str = 'medium') -> Decimal:
        """Calculate estimated cost for a task."""
        self._record_call('calculate_task_cost', task_type=task_type, complexity=complexity)

        if self._should_fail():
            raise Exception(f"Mock JAM failure: calculate_task_cost for {task_type}")

        # Mock cost calculation based on task type and complexity
        base_costs = {
            'rag_query': Decimal('0.001'),
            'decision_making': Decimal('0.003'),
            'data_processing': Decimal('0.005'),
            'organ_call': Decimal('0.002')
        }

        complexity_multipliers = {
            'low': Decimal('0.5'),
            'medium': Decimal('1.0'),
            'high': Decimal('2.0'),
            'complex': Decimal('3.0')
        }

        base_cost = base_costs.get(task_type, Decimal('0.001'))
        multiplier = complexity_multipliers.get(complexity, Decimal('1.0'))

        return base_cost * multiplier

    async def estimate_organ_cost(self, organ_name: str, operation: str, params: Dict[str, Any]) -> Decimal:
        """Estimate cost for organ usage."""
        self._record_call('estimate_organ_cost', organ_name=organ_name, operation=operation, params=params)

        if self._should_fail():
            raise Exception(f"Mock JAM failure: estimate_organ_cost for {organ_name}")

        # Mock organ cost estimation
        organ_base_costs = {
            'web_search': Decimal('0.001'),
            'data_analysis': Decimal('0.003'),
            'document_search': Decimal('0.002'),
            'computation': Decimal('0.005')
        }

        base_cost = organ_base_costs.get(organ_name, Decimal('0.001'))

        # Add complexity based on parameters
        param_complexity = len(str(params)) * Decimal('0.00001')
        return base_cost + param_complexity

    async def get_transaction_history(self, borg_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for a borg."""
        self._record_call('get_transaction_history', borg_id=borg_id, limit=limit)

        if self._should_fail():
            raise Exception(f"Mock JAM failure: get_transaction_history for {borg_id}")

        # Filter transactions for this borg
        borg_transactions = [t for t in self.transaction_history if t['borg_id'] == borg_id]
        return borg_transactions[-limit:]  # Return most recent

    async def validate_economic_constraints(self, borg_id: str, operation_cost: Decimal) -> Dict[str, Any]:
        """Validate if an operation can be performed economically."""
        self._record_call('validate_economic_constraints', borg_id=borg_id, operation_cost=operation_cost)

        if self._should_fail():
            raise Exception(f"Mock JAM failure: validate_economic_constraints for {borg_id}")

        current_balance = await self.get_wealth_balance(borg_id)

        return {
            'can_perform': current_balance >= operation_cost,
            'current_balance': str(current_balance),
            'operation_cost': str(operation_cost),
            'remaining_balance': str(current_balance - operation_cost) if current_balance >= operation_cost else str(current_balance)
        }

    async def get_economic_metrics(self, borg_id: str) -> Dict[str, Any]:
        """Get economic performance metrics for a borg."""
        self._record_call('get_economic_metrics', borg_id=borg_id)

        if self._should_fail():
            raise Exception(f"Mock JAM failure: get_economic_metrics for {borg_id}")

        transactions = await self.get_transaction_history(borg_id, limit=100)

        total_spent = Decimal('0')
        total_earned = Decimal('0')

        for tx in transactions:
            amount = Decimal(tx['amount'])
            if amount < 0:
                total_spent += abs(amount)
            else:
                total_earned += amount

        current_balance = await self.get_wealth_balance(borg_id)

        return {
            'borg_id': borg_id,
            'current_balance': str(current_balance),
            'total_spent': str(total_spent),
            'total_earned': str(total_earned),
            'net_position': str(total_earned - total_spent),
            'transaction_count': len(transactions),
            'average_transaction': str((total_earned - total_spent) / max(len(transactions), 1))
        }

    def _record_call(self, method: str, **kwargs):
        """Record method call for testing verification."""
        # Could be extended to track calls if needed
        pass

    def _should_fail(self) -> bool:
        """Determine if current call should fail."""
        if self.fail_on_next_calls > 0:
            self.fail_on_next_calls -= 1
            return True
        return self.should_fail

    def configure_failure(self, should_fail: bool = True, fail_next_n: int = 0):
        """Configure mock to fail on subsequent calls."""
        self.should_fail = should_fail
        self.fail_on_next_calls = fail_next_n

    def reset_state(self):
        """Reset mock state for testing."""
        self.wealth_balances.clear()
        self.transaction_history.clear()
        self.should_fail = False
        self.fail_on_next_calls = 0

    def set_initial_balance(self, borg_id: str, balance: Decimal):
        """Set initial balance for testing."""
        self.wealth_balances[borg_id] = balance