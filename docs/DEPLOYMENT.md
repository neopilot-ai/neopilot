# Deployment Guide

## Overview

This guide covers deploying Neopilot services in various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Production Considerations](#production-considerations)
- [Monitoring](#monitoring)

## Prerequisites

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB minimum
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2

### Software Requirements

- Python 3.9+
- Docker 20.10+ (for containerized deployment)
- Kubernetes 1.20+ (for K8s deployment)
- PostgreSQL 13+ (for production)
- Redis 6+ (for caching)

## Environment Variables

### Required Variables

```bash
# Service Configuration
SERVICE_NAME=neopilot
SERVICE_VERSION=0.0.2
ENVIRONMENT=production  # development, staging, production

# AI Gateway
AI_GATEWAY_HOST=0.0.0.0
AI_GATEWAY_PORT=8000
AI_GATEWAY_WORKERS=4

# Workflow Service
WORKFLOW_SERVICE_HOST=0.0.0.0
WORKFLOW_SERVICE_PORT=50051

# GitLab Integration
GITLAB_URL=https://gitlab.com
GITLAB_API_TOKEN=<your-token>

# LLM Providers
OPENAI_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>
VERTEX_AI_PROJECT=<project-id>
VERTEX_AI_LOCATION=us-central1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/neopilot
REDIS_URL=redis://localhost:6379/0

# Monitoring
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Optional Variables

```bash
# Feature Flags
ENABLE_ABUSE_DETECTION=true
ENABLE_RATE_LIMITING=true
ENABLE_CACHING=true

# Performance
MAX_CONCURRENT_WORKFLOWS=100
REQUEST_TIMEOUT=300
WORKER_TIMEOUT=600

# Security
ALLOWED_ORIGINS=https://gitlab.com,https://app.example.com
JWT_SECRET=<secret-key>
ENCRYPTION_KEY=<encryption-key>
```

## Local Development

### Using uv

```bash
# Install dependencies
uv sync --extra test

# Set environment variables
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG

# Run AI Gateway
uv run python -m neopilot.ai_gateway.main

# Run Workflow Service (in another terminal)
uv run python -m neopilot.neoai_workflow_service.server
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ai-gateway:
    build:
      context: .
      dockerfile: Dockerfile.ai-gateway
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/neopilot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./src:/app/src

  workflow-service:
    build:
      context: .
      dockerfile: Dockerfile.workflow
    ports:
      - "50051:50051"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/neopilot
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=neopilot
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
```

Run with:

```bash
docker-compose up -d
```

## Docker Deployment

### Dockerfile for AI Gateway

See `docker/Dockerfile.ai-gateway`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uv", "run", "python", "-m", "neopilot.ai_gateway.main"]
```

### Dockerfile for Workflow Service

See `docker/Dockerfile.workflow`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD grpc_health_probe -addr=:50051 || exit 1

# Run application
CMD ["uv", "run", "python", "-m", "neopilot.neoai_workflow_service.server"]
```

### Build and Run

```bash
# Build images
docker build -f docker/Dockerfile.ai-gateway -t neopilot-ai-gateway:latest .
docker build -f docker/Dockerfile.workflow -t neopilot-workflow:latest .

# Run containers
docker run -d \
  --name ai-gateway \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  neopilot-ai-gateway:latest

docker run -d \
  --name workflow-service \
  -p 50051:50051 \
  -e ENVIRONMENT=production \
  neopilot-workflow:latest
```

## Kubernetes Deployment

### Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: neopilot
```

### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: neopilot-config
  namespace: neopilot
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  AI_GATEWAY_PORT: "8000"
  WORKFLOW_SERVICE_PORT: "50051"
```

### Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: neopilot-secrets
  namespace: neopilot
type: Opaque
stringData:
  OPENAI_API_KEY: "<your-key>"
  ANTHROPIC_API_KEY: "<your-key>"
  GITLAB_API_TOKEN: "<your-token>"
  DATABASE_URL: "postgresql://user:pass@postgres:5432/neopilot"
```

### AI Gateway Deployment

```yaml
# ai-gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-gateway
  namespace: neopilot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-gateway
  template:
    metadata:
      labels:
        app: ai-gateway
    spec:
      containers:
      - name: ai-gateway
        image: neopilot-ai-gateway:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: neopilot-config
        - secretRef:
            name: neopilot-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: ai-gateway
  namespace: neopilot
spec:
  selector:
    app: ai-gateway
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### Workflow Service Deployment

```yaml
# workflow-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workflow-service
  namespace: neopilot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: workflow-service
  template:
    metadata:
      labels:
        app: workflow-service
    spec:
      containers:
      - name: workflow-service
        image: neopilot-workflow:latest
        ports:
        - containerPort: 50051
        envFrom:
        - configMapRef:
            name: neopilot-config
        - secretRef:
            name: neopilot-secrets
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
---
apiVersion: v1
kind: Service
metadata:
  name: workflow-service
  namespace: neopilot
spec:
  selector:
    app: workflow-service
  ports:
  - port: 50051
    targetPort: 50051
  type: ClusterIP
```

### Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f ai-gateway-deployment.yaml
kubectl apply -f workflow-deployment.yaml

# Check status
kubectl get pods -n neopilot
kubectl get services -n neopilot

# View logs
kubectl logs -f deployment/ai-gateway -n neopilot
kubectl logs -f deployment/workflow-service -n neopilot
```

## Production Considerations

### 1. High Availability

- Run multiple replicas (minimum 3)
- Use pod anti-affinity rules
- Implement health checks
- Configure auto-scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-gateway-hpa
  namespace: neopilot
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 2. Database

- Use managed PostgreSQL (AWS RDS, GCP Cloud SQL)
- Enable connection pooling
- Configure backups
- Set up read replicas

### 3. Caching

- Deploy Redis cluster
- Configure cache TTL
- Implement cache warming
- Monitor cache hit rates

### 4. Security

- Use TLS/SSL certificates
- Enable network policies
- Implement RBAC
- Scan images for vulnerabilities
- Rotate secrets regularly

### 5. Monitoring

- Set up Prometheus + Grafana
- Configure alerting rules
- Track key metrics
- Enable distributed tracing

### 6. Logging

- Centralize logs (ELK, Loki)
- Use structured logging
- Set retention policies
- Configure log levels per environment

## Monitoring

### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-gateway'
    static_configs:
      - targets: ['ai-gateway:8000']
    metrics_path: '/metrics'

  - job_name: 'workflow-service'
    static_configs:
      - targets: ['workflow-service:50051']
    metrics_path: '/metrics'
```

### Key Metrics to Monitor

- **Request Rate**: requests per second
- **Error Rate**: 4xx/5xx responses
- **Latency**: p50, p95, p99 response times
- **Throughput**: tokens processed per second
- **Resource Usage**: CPU, memory, disk
- **Workflow Metrics**: execution time, success rate

### Alerting Rules

```yaml
groups:
  - name: neopilot
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 5
        for: 5m
        annotations:
          summary: "High latency detected"
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   - Check environment variables
   - Verify database connectivity
   - Review logs for errors

2. **High memory usage**
   - Reduce concurrent workflows
   - Increase memory limits
   - Check for memory leaks

3. **Slow responses**
   - Enable caching
   - Optimize database queries
   - Scale horizontally

4. **Connection errors**
   - Verify network policies
   - Check firewall rules
   - Ensure services are healthy

## Rollback

```bash
# Kubernetes rollback
kubectl rollout undo deployment/ai-gateway -n neopilot
kubectl rollout undo deployment/workflow-service -n neopilot

# Docker rollback
docker stop ai-gateway workflow-service
docker run -d --name ai-gateway neopilot-ai-gateway:previous
docker run -d --name workflow-service neopilot-workflow:previous
```

## Support

For deployment support, see [SUPPORT.md](../SUPPORT.md) or open an issue on GitHub.
