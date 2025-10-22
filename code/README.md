# BorgLife Prototype

*Phase 1: Phenotype-First Architecture with Archon Integration*

BorgLife is a decentralized autonomous organization (DAO) platform that enables the creation and evolution of autonomous digital entities called "borgs". This prototype implements the core functionality described in the BorgLife whitepaper, focusing on phenotype composition and execution using Archon as the synthesis engine.

## 🏗️ Architecture Overview

BorgLife implements a three-layer architecture:

1. **On-Chain (JAM)**: Trustless execution via refine/accumulate phases
2. **Off-Chain Synthesis (Archon)**: Build executable borg phenotypes from DNA
3. **Off-Chain Ecosystem**: Bidirectional DNA↔phenotype mappings

### Key Components

- **DNA Parser**: Parse borg DNA from YAML/PVM formats
- **Phenotype Builder**: Construct executable phenotypes from DNA
- **Archon Adapter**: Stable interface to Archon services
- **Proto-Borg**: Phase 1 prototype implementation
- **Borg Designer UI**: Streamlit interface for phenotype composition
- **Docker MCP Organs**: Containerized external capabilities

## 🚀 Quick Start

### Prerequisites

- Docker Desktop
- Python 3.9+
- OpenAI API key
- Supabase account (for shared database)

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd borglife_prototype
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start development environment:**
   ```bash
   ./scripts/dev.sh start
   ```

   This will:
   - Validate dependencies and configuration
   - Start Archon services
   - Launch BorgLife UI at http://localhost:8501
   - Start Docker MCP organs

### Alternative Startup Modes

```bash
# Start core services only (no Docker MCP organs)
./scripts/dev.sh start core

# Start minimal services (UI + essentials)
./scripts/dev.sh start minimal

# View service status
./scripts/dev.sh status

# View logs
./scripts/dev.sh logs borglife-ui

# Stop all services
./scripts/dev.sh stop
```

## 🎨 Using the Borg Designer UI

1. **Navigate to** http://localhost:8501
2. **Design Phenotype**: Select cells (logic units) and organs (capabilities)
3. **Test Phenotype**: Execute tasks to validate functionality
4. **Encode to DNA**: Generate DNA file for on-chain storage
5. **Fund Borg**: Add DOT for task execution costs

### Example Phenotype

```yaml
header:
  code_length: 1024
  gas_limit: 1000000
  service_index: "research-assistant-001"

cells:
  - name: "data_analyzer"
    logic_type: "data_processor"
    parameters:
      model: "gpt-4"
      max_tokens: 1000
    cost_estimate: 0.001

organs:
  - name: "web_search"
    mcp_tool: "docker_mcp:duckduckgo"
    url: "http://docker-mcp-duckduckgo:8080"
    abi_version: "1.0"
    price_cap: 0.0001

manifesto_hash: "borglife_universal_principles_hash"
```

## 🧪 Testing

### Unit Tests
```bash
pytest tests/ -v --cov=borglife_prototype
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Manual Testing
```python
import asyncio
from proto_borg import create_proto_borg, run_demo_task

async def main():
    borg = await create_proto_borg("test-borg")
    result = await run_demo_task(borg, "Analyze market trends for AI stocks")
    print(f"Result: {result}")

asyncio.run(main())
```

## 📁 Project Structure

```
borglife_prototype/
├── archon_adapter/          # Archon service integration
│   ├── adapter.py           # Main adapter class
│   ├── config.py            # Configuration management
│   ├── exceptions.py        # Custom exceptions
│   ├── fallback_manager.py  # Organ fallback strategies
│   ├── health.py            # Service health monitoring
│   └── version.py           # Version compatibility
├── synthesis/               # DNA parsing and phenotype building
│   ├── dna_parser.py        # YAML/PVM DNA parsing
│   └── phenotype_builder.py # Executable phenotype construction
├── jam_mock/                # JAM blockchain mock
├── monitoring/              # Observability and metrics
├── reputation/              # Borg reputation system
├── evolution/               # Phase 2 evolution preparation
├── security/                # Security controls
├── project_management/      # Development tracking
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
├── borg_designer_ui.py      # Streamlit UI
├── proto_borg.py           # Prototype implementation
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Container orchestration
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_SERVICE_KEY` | Supabase service key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `ARCHON_SERVER_URL` | Archon server URL | No (default: http://archon-server:8181) |
| `JAM_MOCK_MODE` | Use JAM mock instead of real blockchain | No (default: true) |

### Service Ports

- **BorgLife UI**: 8501
- **BorgLife MCP**: 8053
- **BorgLife Agent**: 8054
- **Archon Server**: 8181
- **Archon MCP**: 8051
- **Archon Agents**: 8052

## 🔒 Security

- Input validation on all user inputs
- Rate limiting per borg and organ
- Authentication for external service access
- Audit logging for all operations
- Circuit breakers for service resilience

## 📊 Monitoring

- Prometheus metrics for performance monitoring
- Health checks for all services
- Wealth tracking and cost analysis
- Reputation scoring system
- Docker MCP organ monitoring

## 🚦 Development Roadmap

### Phase 1 (Current): Phenotype-First Bootstrap
- ✅ Archon integration
- ✅ Phenotype composition UI
- ✅ DNA encoding/decoding
- ✅ Basic task execution
- ✅ Wealth tracking
- 🔄 Docker MCP organs (partial)

### Phase 2: Evolution Engine
- Genetic programming framework
- Mating market implementation
- Fitness evaluation
- Swarm coordination

### Phase 3: Full Ecosystem
- Cross-chain settlements
- Tribal organ pools
- Advanced reputation system
- Real-time orchestration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy borglife_prototype/
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE.md file for details.

## 📚 Documentation

- [BorgLife Whitepaper](https://borglife.io/whitepaper)
- [Archon Documentation](https://archon.org/docs)
- [API Reference](./docs/api.md)
- [Troubleshooting](./TROUBLESHOOTING.md)

## 🆘 Troubleshooting

### Common Issues

1. **Services won't start**: Check Docker Desktop is running and ports are available
2. **Archon connection failed**: Verify Archon services are healthy
3. **DNA parsing errors**: Validate YAML syntax and required fields
4. **Task execution fails**: Check borg wealth balance and rate limits

### Getting Help

- Check the [Troubleshooting Guide](./TROUBLESHOOTING.md)
- Review service logs: `./scripts/dev.sh logs`
- Open an issue on GitHub

## 🙏 Acknowledgments

- BorgLife whitepaper authors
- Archon team for the synthesis engine
- Docker MCP community for organ implementations
- All contributors and early adopters

---

**BorgLife**: *Autonomous Digital Life Evolving Through Market Forces*