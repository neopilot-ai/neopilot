# Neopilot Architecture & Project Structure

## Overview
Neopilot is a comprehensive AI-powered workflow and code assistance platform consisting of multiple integrated services.

## Project Structure

```
neopilot/
├── src/neopilot/                      # Main source code
│   ├── __init__.py                    # Package initialization
│   ├── ai_gateway/                    # AI Gateway Service (694 items)
│   │   ├── api/                       # API endpoints
│   │   │   ├── v1/                    # API version 1
│   │   │   ├── v2/                    # API version 2
│   │   │   ├── v3/                    # API version 3
│   │   │   ├── v4/                    # API version 4
│   │   │   ├── middleware/            # Authentication, logging, etc.
│   │   │   └── server.py              # Main API server
│   │   ├── code_suggestions/          # Code completion & suggestions
│   │   ├── chat/                      # Chat functionality
│   │   ├── models/                    # Model integrations
│   │   ├── prompts/                   # Prompt management
│   │   ├── integrations/              # Third-party integrations
│   │   ├── abuse_detection/           # Security & abuse prevention
│   │   ├── app.py                     # Application entry point
│   │   ├── config.py                  # Configuration management
│   │   ├── container.py               # Dependency injection
│   │   └── main.py                    # Main execution
│   │
│   ├── neoai_workflow_service/        # Neoai Workflow Service (172 items)
│   │   ├── agent_platform/            # Agent platform integration
│   │   ├── agents/                    # AI agents
│   │   ├── checkpointer/              # State checkpointing
│   │   ├── components/                # Reusable components
│   │   ├── entities/                  # Data models
│   │   ├── errors/                    # Error handling
│   │   ├── executor/                  # Workflow execution
│   │   ├── gitlab/                    # GitLab integration
│   │   ├── interceptors/              # gRPC interceptors
│   │   ├── policies/                  # Access policies
│   │   ├── security/                  # Security validation
│   │   ├── slash_commands/            # Command handlers
│   │   ├── tools/                     # Workflow tools
│   │   ├── tracking/                  # Metrics & analytics
│   │   ├── workflows/                 # Workflow definitions
│   │   ├── client.py                  # Client interface
│   │   ├── server.py                  # gRPC server
│   │   └── llm_factory.py             # LLM initialization
│   │
│   ├── clients/                       # Client libraries
│   │   └── ruby/                      # Ruby client SDK
│   │       ├── lib/gitlab/neoai_workflow_service/
│   │       └── gitlab-neoai-workflow-service-client.gemspec
│   │
│   ├── config/                        # Configuration files
│   │   └── events/                    # Event definitions (YAML)
│   │
│   ├── contract/                      # Protocol Buffers contracts
│   │   ├── contract_pb2.py
│   │   └── contract_pb2_grpc.py
│   │
│   ├── eval/                          # Evaluation & testing
│   │   ├── generate_dataset.py
│   │   └── main.py
│   │
│   ├── integration_tests/             # Integration tests
│   ├── performance_tests/             # Performance & stress tests
│   ├── lints/                         # Custom linting rules
│   └── lib/                           # Shared utilities
│
├── tests/                             # Unit tests
│   ├── conftest.py                    # Pytest configuration
│   └── test_methods.py
│
├── docs/                              # Documentation
│   ├── index.rst                      # Documentation index
│   ├── conf.py                        # Sphinx configuration
│   ├── developer.md                   # Developer guide
│   ├── pyproject.md                   # Project config docs
│   └── requirements.txt               # Doc dependencies
│
├── .github/                           # GitHub workflows & templates
├── .vscode/                           # VS Code settings
├── .devcontainer/                     # Dev container config
├── pyproject.toml                     # Project configuration
├── uv.lock                            # Dependency lock file
├── README.md                          # Project overview
├── LICENSE                            # MIT License
└── CODE_OF_CONDUCT.md                 # Code of conduct
```

## Core Components

### 1. AI Gateway Service
**Purpose**: Main API gateway for AI-powered features

**Key Modules**:
- **API Endpoints**: Multi-versioned REST API (v1-v4)
- **Code Suggestions**: AI-powered code completion and generation
- **Chat**: Conversational AI interface
- **Models**: Integration with multiple LLM providers (OpenAI, Anthropic, Vertex AI, Amazon Q)
- **Prompts**: Centralized prompt management and registry
- **Abuse Detection**: Security and content filtering

**Technologies**:
- FastAPI for API framework
- Dependency injection via containers
- Structured logging and monitoring
- Prometheus metrics

### 2. Neoai Workflow Service
**Purpose**: Orchestrates complex AI workflows and agent interactions

**Key Modules**:
- **Workflows**: Predefined workflow patterns (chat, code generation, etc.)
- **Agents**: Autonomous AI agents with tool access
- **Tools**: Extensible tool system for agent capabilities
- **GitLab Integration**: Deep integration with GitLab APIs
- **Security**: Request validation and access control
- **Tracking**: Metrics and event tracking

**Technologies**:
- gRPC for service communication
- LangChain/LangGraph for agent orchestration
- GitLab Cloud Connector
- Event-driven architecture

### 3. Client Libraries
**Purpose**: SDKs for consuming services

**Available Clients**:
- Ruby client for GitLab integration
- Python client (internal)

### 4. Configuration & Events
**Purpose**: Centralized configuration and event definitions

**Components**:
- Event schemas (YAML)
- Service configuration
- Feature flags

## Architecture Patterns

### Dependency Injection
- Container-based DI for loose coupling
- Async dependency resolution
- Testable component design

### Layered Architecture
```
Presentation Layer (API)
    ↓
Business Logic Layer (Services/Workflows)
    ↓
Data Access Layer (Clients/Integrations)
    ↓
Infrastructure Layer (Monitoring/Logging)
```

### Event-Driven Design
- Internal events for tracking
- Workflow state management
- Asynchronous processing

## Technology Stack

### Core
- **Python 3.9+**: Primary language
- **FastAPI**: Web framework
- **gRPC**: Service communication
- **Protocol Buffers**: Contract definitions

### AI/ML
- **LangChain**: LLM orchestration
- **LangGraph**: Agent workflows
- **Multiple LLM Providers**: OpenAI, Anthropic, Vertex AI, Amazon Q

### Infrastructure
- **Prometheus**: Metrics
- **Structured Logging**: JSON logging
- **GitLab Cloud Connector**: Service mesh

### Development
- **uv**: Fast Python package manager
- **pytest**: Testing framework
- **black**: Code formatting
- **pylint/flake8**: Linting
- **pre-commit**: Git hooks

## Testing Strategy

### Test Types
1. **Unit Tests**: `tests/` directory
2. **Integration Tests**: `src/neopilot/integration_tests/`
3. **Performance Tests**: `src/neopilot/performance_tests/`
4. **Evaluation**: `src/neopilot/eval/`

### Coverage
- Target: 100% (configurable in pyproject.toml)
- Branch coverage enabled
- Continuous monitoring

## Build & Deployment

### Build System
- **Flit**: Simple Python packaging
- **pyproject.toml**: PEP 621 compliant
- **uv**: Fast dependency resolution

### CI/CD
- GitHub Actions workflows
- Pre-commit hooks
- Automated testing

## Security

### Security Measures
- Request validation (security module)
- Abuse detection
- Access policies
- GitLab authentication integration
- Custom security exceptions

## Monitoring & Observability

### Metrics
- Prometheus integration
- Custom metrics tracking
- Performance profiling

### Logging
- Structured JSON logging
- Request/response logging
- Error tracking

## Development Workflow

### Setup
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install dev dependencies
uv sync --extra test

# Activate virtual environment
source .venv/bin/activate
```

### Testing
```bash
# Run unit tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run integration tests
uv run pytest -m integration

# Run performance tests
uv run pytest -m slow
```

### Code Quality
```bash
# Format code
uv run black src/

# Lint code
uv run flake8 src/
uv run pylint src/

# Run pre-commit hooks
uv run pre-commit run --all-files
```

## Configuration

### Environment Variables
- Managed through GitLab Cloud Connector
- Service-specific configuration
- Feature flags

### Configuration Files
- `pyproject.toml`: Project metadata and tool config
- `config/events/*.yml`: Event definitions
- `.pre-commit-config.yaml`: Git hooks

## Future Enhancements

### Recommended Improvements
1. **API Documentation**: Add OpenAPI/Swagger specs
2. **Service Mesh**: Enhanced service discovery
3. **Caching Layer**: Redis integration for performance
4. **Message Queue**: Async task processing
5. **Database Layer**: Persistent storage for workflows
6. **Monitoring Dashboard**: Grafana integration
7. **API Rate Limiting**: Request throttling
8. **Enhanced Security**: OAuth2/JWT tokens
9. **Multi-tenancy**: Tenant isolation
10. **Horizontal Scaling**: Load balancing support

## Contributing

See `CODE_OF_CONDUCT.md` and `SUPPORT.md` for contribution guidelines.

## License

MIT License - See `LICENSE` file for details.
