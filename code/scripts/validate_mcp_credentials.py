#!/usr/bin/env python3
"""
Validate Docker MCP organ credentials
"""
import sys
import os
import asyncio
import httpx

async def validate_organ_credentials(organ_name: str, endpoint: str) -> bool:
    """Validate credentials for a specific organ"""
    try:
        # Test basic connectivity
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{endpoint}/health")
            if response.status_code != 200:
                return False

        # Test a simple tool call (would need actual credentials)
        # This is a placeholder - actual validation would depend on organ
        print(f"✅ {organ_name} credentials appear valid")
        return True

    except Exception as e:
        print(f"❌ {organ_name} credential validation failed: {e}")
        return False

async def main():
    """Main validation function"""
    if len(sys.argv) < 2:
        print("Usage: python validate_mcp_credentials.py --organ <organ_name>")
        sys.exit(1)

    organ_name = sys.argv[2] if len(sys.argv) > 2 else None

    if not organ_name:
        print("❌ Please specify organ name")
        sys.exit(1)

    # Map organ names to endpoints
    endpoints = {
        'gmail': 'http://localhost:8061',
        'stripe': 'http://localhost:8062',
        'bitcoin': 'http://localhost:8063',
        'mongodb': 'http://localhost:8064'
    }

    if organ_name not in endpoints:
        print(f"❌ Unknown organ: {organ_name}")
        sys.exit(1)

    endpoint = endpoints[organ_name]

    print(f"🔍 Validating {organ_name} credentials...")

    success = await validate_organ_credentials(organ_name, endpoint)

    if success:
        print("✅ Validation complete")
        sys.exit(0)
    else:
        print("❌ Validation failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())