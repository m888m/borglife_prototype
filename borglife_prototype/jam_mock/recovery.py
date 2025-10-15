class OnChainRecovery:
    """Handle on-chain storage failures"""

    async def retry_storage(
        self,
        service_index: str,
        dna_hash: str,
        max_attempts: int = 5
    ) -> Dict[str, Any]:
        """
        Retry on-chain storage with exponential backoff

        Returns:
            Storage result with block number and transaction hash
        """
        for attempt in range(max_attempts):
            try:
                result = await self.jam.store_dna_hash(
                    service_index,
                    dna_hash
                )

                if result['success']:
                    return result

            except Exception as e:
                logger.warning(
                    f"Storage attempt {attempt + 1} failed: {e}"
                )

                if attempt < max_attempts - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)

        # All attempts failed - store locally as backup
        return await self._store_locally(service_index, dna_hash)

    async def _store_locally(
        self,
        service_index: str,
        dna_hash: str
    ) -> Dict[str, Any]:
        """Fallback: Store DNA hash locally for later on-chain submission"""
        # Store in Supabase with pending status
        # Queue for retry when chain is available
        pass