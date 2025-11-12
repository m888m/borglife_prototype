from typing import Dict, Any
import httpx

class ArchonDependencyMonitor:
    """Monitor Archon's external dependencies"""

    DEPENDENCIES = {
        'supabase': 'https://xxxxx.supabase.co/rest/v1/',
        'openai': 'https://api.openai.com/v1/models'
    }

    async def check_archon_dependencies(self) -> Dict[str, bool]:
        """Check if Archon's dependencies are healthy"""
        results = {}

        for dep_name, endpoint in self.DEPENDENCIES.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(endpoint, timeout=5.0)
                    results[dep_name] = response.status_code < 500
            except:
                results[dep_name] = False

        return results

    async def validate_full_stack(self) -> Dict[str, Any]:
        """Validate entire dependency stack"""
        return {
            'archon_services': await self.check_archon_health(),
            'archon_dependencies': await self.check_archon_dependencies(),
            'docker_mcp_organs': await self.check_docker_mcp_health(),
            'borglife_services': await self.check_borglife_health()
        }