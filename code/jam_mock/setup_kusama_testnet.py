        try:
            # Test with working endpoint
            adapter = KusamaAdapter("wss://kusama.api.onfinality.io/public-ws", connect_immediately=True)
            health = adapter.health_check()

            if health['status'] == 'healthy':
                print("   ✅ Connection successful!")
                print(f"   📊 Chain: {health.get('chain_name', 'Unknown')}")
                print(f"   🔢 Block: {health.get('block_number', 'Unknown')}")
                self.setup_config['connection_test'] = True
                return True
            else:
                print(f"   ❌ Connection failed: {health.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"   ❌ Connection test failed: {e}")
            return False