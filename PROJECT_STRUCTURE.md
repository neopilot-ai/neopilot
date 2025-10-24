# Neopilot Project Structure

**Last Updated**: October 24, 2025  
**Version**: 2.0 (Reorganized)

## Overview

This document describes the complete project structure after reorganization for better maintainability and clarity.

## Directory Tree

```
neopilot/
├── .github/                          # GitHub configuration
│   ├── workflows/
│   │   └── build-and-test.yml        # CI/CD pipeline
│   └── LINTING_QUICK_REFERENCE.md    # Quick linting guide
│
├── deploy/                           # 🆕 All deployment configuration
│   ├── k8s/                          # Kubernetes manifests
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secrets.yaml
│   │   ├── secrets.example.yaml
│   │   ├── ai-gateway-deployment.yaml
│   │   ├── workflow-deployment.yaml
│   │   ├── prometheus-deployment.yaml
│   │   ├── cert-manager-setup.yaml
│   │   ├── ingress.yaml
│   │   └── README.md
│   ├── monitoring/                   # Monitoring configuration
│   │   ├── grafana/
│   │   │   ├── dashboards/
│   │   │   │   ├── neopilot-overview.json
│   │   │   │   └── dashboards.yaml
│   │   │   └── datasources/
│   │   │       └── prometheus.yml
│   │   └── prometheus/
│   │       ├── prometheus.yml
│   │       └── alerts/
│   │           └── neopilot-alerts.yml
│   └── README.md                     # Deployment guide
│
├── docker/                           # 🆕 Docker configuration
│   ├── Dockerfile.ai-gateway         # AI Gateway image
│   ├── Dockerfile.workflow           # Workflow Service image
│   ├── docker-compose.yml            # Local development stack
│   └── README.md                     # Docker guide
│
├── docs/                             # Documentation
│   ├── API.md                        # API documentation
│   ├── DEPLOYMENT.md                 # Deployment guide
│   ├── LINTING.md                    # Code quality guide
│   ├── developer.md                  # Developer workflows
│   └── pyproject.md                  # Configuration docs
│
├── scripts/                          # Automation scripts
│   ├── setup-secrets.sh              # Kubernetes secrets setup
│   ├── setup-ssl.sh                  # SSL certificate setup
│   └── fix-lint.sh                   # Auto-fix linting issues
│
├── src/neopilot/                     # Source code
│   ├── ai_gateway/                   # AI Gateway Service (694 items)
│   │   ├── api/
│   │   │   ├── v1/, v2/, v3/, v4/    # API versions
│   │   │   ├── middleware/
│   │   │   │   └── rate_limiting.py  # Rate limiting
│   │   │   ├── openapi_config.py     # OpenAPI config
│   │   │   └── schemas.py            # API schemas
│   │   ├── code_suggestions/
│   │   ├── chat/
│   │   ├── models/
│   │   ├── prompts/
│   │   ├── integrations/
│   │   └── abuse_detection/
│   │
│   ├── neoai_workflow_service/       # Workflow Service (172 items)
│   │   ├── agent_platform/
│   │   ├── agents/
│   │   ├── workflows/
│   │   ├── tools/
│   │   ├── gitlab/
│   │   ├── security/
│   │   ├── tracking/
│   │   └── server.py
│   │
│   ├── integration_tests/            # Integration tests
│   ├── performance_tests/            # Performance tests
│   └── hello_world.py                # Example module
│
├── tests/                            # Unit tests
│   ├── conftest.py
│   ├── test_methods.py
│   └── ...
│
├── .flake8                           # Flake8 configuration
├── .gitignore                        # Git ignore rules
├── CODE_OF_CONDUCT.md                # Code of conduct
├── CONTRIBUTING.md                   # Contributing guide
├── LICENSE                           # MIT License
├── Makefile                          # Build and deployment commands
├── README.md                         # Project overview
├── pyproject.toml                    # Project configuration
├── uv.lock                           # Dependency lock file
│
└── Documentation Files               # Project documentation
    ├── ARCHITECTURE.md               # System architecture
    ├── COMPLETE_SETUP_SUMMARY.md     # Complete setup overview
    ├── DEPLOYMENT_CHECKLIST.md       # Deployment checklist
    ├── DEPLOY_REORGANIZATION.md      # Deploy reorg notes
    ├── DOCKER_REORGANIZATION.md      # Docker reorg notes
    ├── FINAL_SETUP_GUIDE.md          # Quick setup guide
    ├── IMPLEMENTATION_SUMMARY.md     # Implementation details
    ├── LINTING_FIXES.md              # Linting fixes summary
    ├── PROJECT_STRUCTURE.md          # This file
    └── STRUCTURE_REVIEW.md           # Structure review
```

## Key Directories

### 📦 deploy/
**Purpose**: All deployment and infrastructure configuration

**Contents**:
- **k8s/**: Kubernetes manifests for production deployment
- **monitoring/**: Prometheus and Grafana configuration

**When to use**: Deploying to Kubernetes or setting up monitoring

### 🐳 docker/
**Purpose**: Docker images and local development stack

**Contents**:
- Dockerfiles for both services
- docker-compose.yml for local development

**When to use**: Building images or running locally

### 📚 docs/
**Purpose**: Comprehensive project documentation

**Contents**:
- API documentation
- Deployment guides
- Developer guides

**When to use**: Learning about the project or deploying

### 🔧 scripts/
**Purpose**: Automation and setup scripts

**Contents**:
- Secrets management
- SSL setup
- Linting fixes

**When to use**: Setting up environments or automating tasks

### 💻 src/neopilot/
**Purpose**: Application source code

**Contents**:
- AI Gateway Service
- Workflow Service
- Shared utilities

**When to use**: Development and testing

## File Organization Principles

### 1. Separation of Concerns
- **Source code**: `src/`
- **Tests**: `tests/`
- **Deployment**: `deploy/`
- **Docker**: `docker/`
- **Documentation**: `docs/` + root-level docs

### 2. Logical Grouping
- All Kubernetes files in `deploy/k8s/`
- All monitoring in `deploy/monitoring/`
- All Docker in `docker/`

### 3. Self-Documenting
- Each major directory has a README.md
- Clear naming conventions
- Consistent structure

### 4. Easy Navigation
- Flat structure where possible
- Deep nesting only when necessary
- Predictable locations

## Common Tasks

### Development

```bash
# Start local environment
make dev

# Run tests
make test

# Fix linting
make format-fix
```

### Deployment

```bash
# Deploy to Kubernetes
make k8s-deploy

# Build Docker images
make docker-build

# Start local stack
make local-up
```

### Documentation

```bash
# View API docs
open http://localhost:8000/docs

# Read deployment guide
cat docs/DEPLOYMENT.md

# Check project structure
cat PROJECT_STRUCTURE.md
```

## Recent Changes

### Version 2.0 (October 24, 2025)

**Major Reorganization**:
1. ✅ Created `deploy/` directory
   - Moved `k8s/` → `deploy/k8s/`
   - Moved `grafana/` → `deploy/monitoring/grafana/`
   - Moved `prometheus/` → `deploy/monitoring/prometheus/`

2. ✅ Created `docker/` directory
   - Moved `Dockerfile.*` → `docker/`
   - Moved `docker-compose.yml` → `docker/`

3. ✅ Updated all references
   - Makefile commands
   - docker-compose volume mounts
   - Documentation
   - Scripts

**Benefits**:
- Cleaner root directory
- Better organization
- Easier to find files
- Industry best practices

## Configuration Files

### Root Level
- **pyproject.toml**: Python project configuration
- **uv.lock**: Dependency lock file
- **.flake8**: Linting configuration
- **Makefile**: Build commands
- **.gitignore**: Git ignore rules

### Deploy
- **deploy/k8s/**: Kubernetes manifests
- **deploy/monitoring/**: Monitoring configuration

### Docker
- **docker/**: Docker images and compose

## Documentation Files

### Quick Start
- **README.md**: Project overview
- **FINAL_SETUP_GUIDE.md**: Quick setup
- **COMPLETE_SETUP_SUMMARY.md**: Complete overview

### Detailed Guides
- **ARCHITECTURE.md**: System architecture
- **CONTRIBUTING.md**: How to contribute
- **docs/DEPLOYMENT.md**: Deployment guide
- **docs/API.md**: API documentation
- **docs/LINTING.md**: Code quality guide

### Reference
- **DEPLOYMENT_CHECKLIST.md**: Pre-deployment checklist
- **IMPLEMENTATION_SUMMARY.md**: What was built
- **PROJECT_STRUCTURE.md**: This file

## Best Practices

1. **Keep root clean**: Only essential files in root
2. **Group related files**: Use directories for organization
3. **Document everything**: README in each major directory
4. **Consistent naming**: Follow established patterns
5. **Logical hierarchy**: Deep nesting only when needed

## See Also

- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [deploy/README.md](deploy/README.md) - Deployment guide
- [docker/README.md](docker/README.md) - Docker guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guide

---

**Maintained by**: Neopilot Team  
**Last Review**: October 24, 2025  
**Status**: ✅ Current
