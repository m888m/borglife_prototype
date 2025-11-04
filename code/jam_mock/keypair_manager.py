    def _save_keypair_to_disk(self, name: str, keypair: Keypair, public_info: Dict[str, Any]):
        """
        Encrypt and save keypair to disk.
        """
        # Prepare data to encrypt
        keypair_data = {
            'seed_hex': keypair.seed_hex,
            'public_key': keypair.public_key.hex(),
            'ss58_address': keypair.ss58_address,
            'ss58_format': keypair.ss58_format
        }

        # Simple XOR encryption (for development only - NOT production secure)
        json_str = json.dumps(keypair_data)
        json_bytes = json_str.encode()
        encrypted_data = self._xor_encrypt(json_bytes, self.encryption_key)

        # Save encrypted data
        keypair_file = self.storage_path / f"{name}.enc"
        with open(keypair_file, 'wb') as f:
            f.write(encrypted_data)

        # Update metadata
        metadata = self._load_metadata()
        metadata[name] = public_info
        self._save_metadata(metadata)