#!/usr/bin/env python3
"""
Validate prerequisites for BorgLife development environment
"""
import sys
import subprocess
import asyncio
import httpx

async def check_service_health(url: str, name: str) -> bool:
    """Check if a service is healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.status_code < 500
    except:
        return False

def run_command(cmd: str) -> tuple[bool, str]:
    """Run shell command and return success status and output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip()
    except:
        return False, ""

async def main():
    """Main validation function"""
    print("🔍 Validating BorgLife Development Prerequisites")
    print("=" * 50)

    all_passed = True

    # Check Docker
    print("\n🐳 Checking Docker...")
    success, output = run_command("docker --version")
    if success:
        print(f"✅ Docker available: {output}")
    else:
        print("❌ Docker not found - install Docker Desktop")
        all_passed = False

    # Check Docker Compose
    success, output = run_command("docker compose version")
    if success:
        print(f"✅ Docker Compose available: {output}")
    else:
        print("❌ Docker Compose not found")
        all_passed = False

    # Check if archon_app-network exists
    print("\n🌐 Checking Docker networks...")
    success, output = run_command("docker network ls")
    if "archon_app-network" in output:
        print("✅ archon_app-network exists")
    else:
        print("❌ archon_app-network not found (start Archon first)")
        all_passed = False

    # Check borglife-network
    if "borglife-network" in output:
        print("✅ borglife-network exists")
    else:
        print("❌ borglife-network not found")
        all_passed = False

    # Check Archon services
    print("\n🤖 Checking Archon services...")
    archon_healthy = await check_service_health("http://localhost:8181/health", "Archon Server")
    if archon_healthy:
        print("✅ Archon Server healthy")
    else:
        print("❌ Archon Server not responding")
        all_passed = False

    mcp_healthy = await check_service_health("http://localhost:8051/health", "Archon MCP")
    if mcp_healthy:
        print("✅ Archon MCP healthy")
    else:
        print("❌ Archon MCP not responding")
        all_passed = False

    # Check Docker MCP organs (sample)
    print("\n🔧 Checking Docker MCP organs...")
    organs_to_check = [
        ("http://localhost:8061/health", "Gmail MCP"),
        ("http://localhost:8062/health", "Stripe MCP"),
        ("http://localhost:8063/health", "Bitcoin MCP")
    ]

    for url, name in organs_to_check:
        healthy = await check_service_health(url, name)
        if healthy:
            print(f"✅ {name} healthy")
        else:
            print(f"❌ {name} not responding")
            all_passed = False

    # Final result
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All prerequisites validated - ready to proceed")
        sys.exit(0)
    else:
        print("❌ Some prerequisites missing - please resolve before continuing")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())