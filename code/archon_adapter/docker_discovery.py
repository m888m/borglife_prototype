from typing import Dict, List

import docker


class DockerMCPDiscovery:
    """Discover and catalog Docker MCP organs"""

    def __init__(self):
        self.docker_client = docker.from_env()

    def discover_mcp_containers(self) -> Dict[str, Dict]:
        """
        Discover all running Docker MCP containers

        Returns:
            {
                organ_name: {
                    'container_id': str,
                    'endpoint': str,
                    'labels': Dict,
                    'health': str,
                    'tools': List[str]
                }
            }
        """
        mcp_containers = {}

        # Find containers with MCP labels
        containers = self.docker_client.containers.list(
            filters={"label": "mcp.server=true"}
        )

        for container in containers:
            organ_name = container.labels.get("mcp.organ_name")
            if not organ_name:
                continue

            # Extract metadata from labels
            mcp_containers[organ_name] = {
                "container_id": container.id,
                "endpoint": self._get_endpoint(container),
                "category": container.labels.get("mcp.category"),
                "version": container.labels.get("mcp.version"),
                "tools": self._discover_tools(container),
                "health": container.status,
            }

        return mcp_containers

    def _get_endpoint(self, container) -> str:
        """Extract HTTP endpoint from container"""
        # Get port mapping
        ports = container.ports
        if "8080/tcp" in ports:
            host_port = ports["8080/tcp"][0]["HostPort"]
            return f"http://localhost:{host_port}"
        return None

    async def _discover_tools(self, container) -> List[str]:
        """Query container for available MCP tools"""
        # Make HTTP call to /tools endpoint
        # Parse tool list
        pass
