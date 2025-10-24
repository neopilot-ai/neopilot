# Docker Configuration

This directory contains all Docker-related files for the Neopilot project.

## Files

- **Dockerfile.ai-gateway** - Docker image for AI Gateway service
- **Dockerfile.workflow** - Docker image for Workflow service
- **docker-compose.yml** - Complete development stack

## Quick Start

### Build Images

```bash
# From project root
make docker-build

# Or manually
docker build -f docker/Dockerfile.ai-gateway -t neopilot-ai-gateway:latest .
docker build -f docker/Dockerfile.workflow -t neopilot-workflow:latest .
```

### Start Development Stack

```bash
# From project root
make local-up

# Or manually
docker-compose -f docker/docker-compose.yml up -d
```

### Stop Stack

```bash
make local-down

# Or manually
docker-compose -f docker/docker-compose.yml down
```

## Services

The docker-compose stack includes:

- **ai-gateway** (port 8000) - AI Gateway API
- **workflow-service** (port 50051) - Workflow Service
- **db** (port 5432) - PostgreSQL database
- **redis** (port 6379) - Redis cache
- **prometheus** (port 9090) - Metrics collection
- **grafana** (port 3000) - Dashboards (admin/admin)

## Environment Variables

Set these in `.env` file or export before running:

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# GitLab
GITLAB_URL=https://gitlab.com
GITLAB_API_TOKEN=glpat-...

# Optional
VERTEX_AI_PROJECT=your-project
VERTEX_AI_LOCATION=us-central1
```

## Image Details

### AI Gateway Image

- **Base**: python:3.11-slim
- **Size**: ~500MB
- **User**: non-root (neopilot)
- **Health Check**: HTTP on /health
- **Exposed Port**: 8000

### Workflow Service Image

- **Base**: python:3.11-slim
- **Size**: ~550MB
- **User**: non-root (neopilot)
- **Health Check**: gRPC health probe
- **Exposed Port**: 50051

## Production Deployment

For production, push images to your registry:

```bash
# Tag images
docker tag neopilot-ai-gateway:latest your-registry/neopilot-ai-gateway:v1.0.0
docker tag neopilot-workflow:latest your-registry/neopilot-workflow:v1.0.0

# Push to registry
docker push your-registry/neopilot-ai-gateway:v1.0.0
docker push your-registry/neopilot-workflow:v1.0.0
```

## Troubleshooting

### Build Fails

```bash
# Clear build cache
docker builder prune -a

# Rebuild without cache
docker build --no-cache -f docker/Dockerfile.ai-gateway -t neopilot-ai-gateway:latest .
```

### Container Won't Start

```bash
# Check logs
docker-compose -f docker/docker-compose.yml logs ai-gateway
docker-compose -f docker/docker-compose.yml logs workflow-service

# Check container status
docker-compose -f docker/docker-compose.yml ps
```

### Port Conflicts

If ports are already in use, modify `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change host port
```

## Best Practices

1. **Multi-stage builds** - Used to minimize image size
2. **Non-root user** - Security best practice
3. **Health checks** - Ensure services are ready
4. **Layer caching** - Optimized for fast rebuilds
5. **Secrets** - Never commit secrets, use environment variables

## See Also

- [DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Full deployment guide
- [Makefile](../Makefile) - Build commands
- [k8s/](../k8s/) - Kubernetes manifests
