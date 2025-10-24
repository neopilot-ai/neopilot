# Neopilot

**AI-Powered Workflow and Code Assistance Platform**

Neopilot is a comprehensive AI platform that provides intelligent code suggestions, workflow automation, and conversational AI capabilities. Built with modern Python practices following PEP 621 standards, it integrates multiple AI services and provides a robust API gateway for AI-powered development tools.

## Features

- 🤖 **AI Gateway**: Multi-versioned REST API for AI services
- 🔄 **Workflow Automation**: Orchestrate complex AI-powered workflows
- 💬 **Conversational AI**: Chat interface with context-aware responses
- 🛠️ **Code Suggestions**: Intelligent code completion and generation
- 🔌 **Multi-Provider Support**: OpenAI, Anthropic, Vertex AI, Amazon Q
- 🔐 **Enterprise Security**: Built-in authentication and abuse detection
- 📊 **Monitoring**: Prometheus metrics and structured logging
- 🧪 **Comprehensive Testing**: Unit, integration, and performance tests

## Architecture

Neopilot consists of two main services:

1. **AI Gateway Service**: FastAPI-based REST API providing code suggestions, chat, and model integrations
2. **Neoai Workflow Service**: gRPC service for orchestrating AI agents and complex workflows

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## 🚀 Quick Start

### One-Command Setup

```bash
# Start complete development environment
make dev
```

This will:
- Install all dependencies with uv
- Start Docker services (API, Database, Redis, Prometheus, Grafana)
- Open API at http://localhost:8000
- Open Swagger docs at http://localhost:8000/docs

### Prerequisites

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd neopilot-1

# Install dependencies
uv sync

# Install development dependencies
uv sync --extra test

# Activate virtual environment
source .venv/bin/activate
```

### Running Tests

```bash
# Run all unit tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run integration tests
uv run pytest -m integration

# Run specific test file
uv run pytest tests/test_methods.py
```

### Development

```bash
# Format code
uv run black src/

# Lint code
uv run flake8 src/
uv run pylint src/

# Run pre-commit hooks
uv run pre-commit run --all-files
```

## Project Structure

```
neopilot/
├── src/neopilot/              # Main source code
│   ├── ai_gateway/            # AI Gateway Service
│   ├── neoai_workflow_service/ # Workflow orchestration
│   ├── clients/               # Client SDKs
│   ├── config/                # Configuration files
│   └── contract/              # Protocol Buffers
├── tests/                     # Unit tests
├── docs/                      # Documentation
├── pyproject.toml             # Project configuration
└── uv.lock                    # Dependency lock file
```

## Configuration

Project configuration is managed through `pyproject.toml` following PEP 621 standards:

- **Build System**: Flit for simple packaging
- **Dependencies**: Managed via uv for fast resolution
- **Code Quality**: Black, Flake8, Pylint, Bandit
- **Testing**: Pytest with coverage reporting
- **Type Checking**: Pyright

## Documentation

- [Architecture Guide](ARCHITECTURE.md) - Detailed architecture and design patterns
- [Developer Guide](docs/developer.md) - Development workflows
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines
- [Support](SUPPORT.md) - Getting help

## Contributing

We welcome contributions! Please see our [Code of Conduct](CODE_OF_CONDUCT.md) and [Support](SUPPORT.md) documentation.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📚 Documentation

- **[COMPLETE_SETUP_SUMMARY.md](COMPLETE_SETUP_SUMMARY.md)** - Complete overview of everything
- **[FINAL_SETUP_GUIDE.md](FINAL_SETUP_GUIDE.md)** - Quick setup guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Production deployment
- **[docs/API.md](docs/API.md)** - API documentation
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deployment guide
- **[docs/LINTING.md](docs/LINTING.md)** - Code quality guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contributing guide

## 🛠️ Common Commands

```bash
# Development
make dev              # Start development environment
make format           # Format code with Black
make lint             # Run all linters
make test             # Run tests
make test-cov         # Run tests with coverage

# Docker
make docker-build     # Build Docker images
make local-up         # Start local stack
make local-down       # Stop local stack

# Kubernetes
make k8s-deploy       # Deploy to Kubernetes
make k8s-status       # Check deployment status
make k8s-logs         # View logs

# Monitoring
make monitor-grafana  # Open Grafana dashboard
make monitor-prometheus  # Open Prometheus

# Cleanup
make clean            # Clean build artifacts
make clean-all        # Clean everything
```

See `make help` for all available commands.

## Technology Stack

- **Framework**: FastAPI, gRPC
- **AI/ML**: LangChain, LangGraph
- **Package Manager**: uv
- **Testing**: Pytest
- **Code Quality**: Black, Flake8, Pylint, Bandit
- **Monitoring**: Prometheus, Grafana
- **Infrastructure**: Docker, Kubernetes
- **CI/CD**: GitHub Actions
- **Build**: Flit

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

For support, please see [SUPPORT.md](SUPPORT.md).

---

**Built with ❤️ by KhulnaSoft DevOps**