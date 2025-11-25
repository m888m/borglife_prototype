import pytest
import pytest_asyncio
from jam_mock.local_mock import LocalJAMMock

@pytest.mark.asyncio
async def test_dispenser_keypair_fixture(dispenser_keypair, jam_interface):
    """Verify dispenser keypair fixture loads correct address."""
    expected_address = "5EepNwM98pD9HQsms1RRcJkU3icrKP9M9cjYv1Vc9XSaMkwD"

    # Verify address and balance in non-mock mode
    if not LocalJAMMock.running():
        client = dispenser_keypair.client()

        # Verify address
        address = client.get_address()
        assert address == expected_address, f"Expected address {expected_address}, got {address}"

        # Verify balance
        balance = await client.get_balance()
        assert balance > 0, f"Expected balance to be greater than 0, got {balance}"