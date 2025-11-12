#!/bin/bash
set -e

echo "🔧 Setting up Docker MCP Organ Library"

# Create Docker network if it doesn't exist
docker network create borglife-network 2>/dev/null || true

# Pull Docker MCP organ images
echo "Pulling Docker MCP organ images..."

# Gmail MCP
docker pull mcp/server/gmail:1.2.0
docker tag mcp/server/gmail:1.2.0 mcp-gmail:latest

# Stripe MCP
docker pull mcp/server/stripe:2.3.0
docker tag mcp/server/stripe:2.3.0 mcp-stripe:latest

# Bitcoin MCP
docker pull mcp/server/bitcoin:1.1.0
docker tag mcp/server/bitcoin:1.1.0 mcp-bitcoin:latest

# MongoDB MCP
docker pull mcp/server/mongodb:1.1.0
docker tag mcp/server/mongodb:1.1.0 mcp-mongodb:latest

echo "✅ Docker MCP organs ready"