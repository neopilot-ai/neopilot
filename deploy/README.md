# Deployment Configuration

This directory contains all deployment and infrastructure configuration for Neopilot.

## Directory Structure

```
deploy/
├── k8s/                          # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── secrets.example.yaml
│   ├── ai-gateway-deployment.yaml
│   ├── workflow-deployment.yaml
│   ├── prometheus-deployment.yaml
│   ├── cert-manager-setup.yaml
│   ├── ingress.yaml
│   └── README.md
└── monitoring/                   # Monitoring configuration
    ├── grafana/                  # Grafana dashboards
    │   ├── dashboards/
    │   │   ├── neopilot-overview.json
    │   │   └── dashboards.yaml
    │   └── datasources/
    │       └── prometheus.yml
    └── prometheus/               # Prometheus configuration
        ├── prometheus.yml
        └── alerts/
            └── neopilot-alerts.yml
```

## Quick Start

### Kubernetes Deployment

```bash
# 1. Set up secrets
cd deploy/k8s
./../../scripts/setup-secrets.sh

# 2. Set up SSL
./../../scripts/setup-ssl.sh

# 3. Deploy all services
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secrets.yaml
kubectl apply -f deploy/k8s/ai-gateway-deployment.yaml
kubectl apply -f deploy/k8s/workflow-deployment.yaml
kubectl apply -f deploy/k8s/prometheus-deployment.yaml
kubectl apply -f deploy/k8s/ingress.yaml

# Or use Makefile
make k8s-deploy
```

### Monitoring Setup

```bash
# Prometheus is deployed with k8s manifests
# Grafana dashboards are auto-provisioned

# Access Grafana
kubectl port-forward -n neopilot svc/grafana 3000:3000

# Access Prometheus
kubectl port-forward -n neopilot svc/prometheus 9090:9090
```

## Components

### Kubernetes (k8s/)

Production-ready Kubernetes manifests for:
- **Namespace**: Isolated environment
- **ConfigMap**: Application configuration
- **Secrets**: Sensitive credentials
- **Deployments**: AI Gateway & Workflow Service
- **Services**: Load balancing
- **Ingress**: External access with SSL
- **HPA**: Auto-scaling
- **Prometheus**: Monitoring stack

See [k8s/README.md](k8s/README.md) for details.

### Monitoring (monitoring/)

Complete monitoring stack:

#### Grafana
- **Dashboards**: Pre-built visualization dashboards
- **Datasources**: Prometheus connection
- **Auto-provisioning**: Automatic dashboard loading

#### Prometheus
- **Configuration**: Service discovery and scraping
- **Alert Rules**: 13 production-ready alerts
- **Retention**: 30-day data retention

## Configuration

### Environment Variables

Set these before deploying:

```bash
# Required
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GITLAB_API_TOKEN="glpat-..."

# Optional
export VERTEX_AI_PROJECT="your-project"
export VERTEX_AI_LOCATION="us-central1"
```

### Secrets

Update `deploy/k8s/secrets.yaml` with actual values:

```bash
# Use the setup script
./scripts/setup-secrets.sh

# Or manually edit
cp deploy/k8s/secrets.example.yaml deploy/k8s/secrets.yaml
# Edit deploy/k8s/secrets.yaml
kubectl apply -f deploy/k8s/secrets.yaml
```

### Domain Configuration

Update `deploy/k8s/ingress.yaml`:

```yaml
spec:
  tls:
  - hosts:
    - api.yourdomain.com  # Change this
    secretName: neopilot-tls
  rules:
  - host: api.yourdomain.com  # Change this
```

## Deployment Workflows

### Development

```bash
# Use docker-compose for local development
docker-compose -f docker/docker-compose.yml up -d
```

### Staging

```bash
# Deploy to staging namespace
kubectl apply -f deploy/k8s/ --namespace=neopilot-staging
```

### Production

```bash
# 1. Update secrets
./scripts/setup-secrets.sh

# 2. Update domain in ingress
vim deploy/k8s/ingress.yaml

# 3. Set up SSL
./scripts/setup-ssl.sh

# 4. Deploy
kubectl apply -f deploy/k8s/

# 5. Verify
kubectl get pods -n neopilot
kubectl get svc -n neopilot
```

## Monitoring

### Dashboards

Access Grafana dashboards:

```bash
kubectl port-forward -n neopilot svc/grafana 3000:3000
# Open http://localhost:3000 (admin/admin)
```

Available dashboards:
- **Neopilot Overview**: Main operational dashboard
- Request rate, error rate, latency
- Resource usage (CPU, memory)
- Token usage tracking

### Alerts

13 alert rules configured:
- HighErrorRate
- HighLatency
- ServiceDown
- HighMemoryUsage
- HighCPUUsage
- PodRestarting
- HighRateLimitHits
- HighWorkflowFailureRate
- TokenUsageSpike
- LowDiskSpace
- DatabaseConnectionPoolExhausted
- CertificateExpiringSoon

Configure alert notifications in Prometheus/Alertmanager.

## Scaling

### Manual Scaling

```bash
# Scale AI Gateway
kubectl scale deployment ai-gateway -n neopilot --replicas=5

# Scale Workflow Service
kubectl scale deployment workflow-service -n neopilot --replicas=3
```

### Auto-scaling

HPA is configured in deployment manifests:
- **AI Gateway**: 3-10 replicas (CPU 70%, Memory 80%)
- **Workflow Service**: 2-8 replicas (CPU 75%, Memory 85%)

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n neopilot

# Describe pod
kubectl describe pod <pod-name> -n neopilot

# View logs
kubectl logs <pod-name> -n neopilot
```

### Monitoring Not Working

```bash
# Check Prometheus targets
kubectl port-forward -n neopilot svc/prometheus 9090:9090
# Open http://localhost:9090/targets

# Check Grafana datasource
kubectl port-forward -n neopilot svc/grafana 3000:3000
# Configuration > Data Sources
```

### SSL Certificate Issues

```bash
# Check certificate status
kubectl get certificate -n neopilot
kubectl describe certificate neopilot-tls -n neopilot

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

## Best Practices

1. **Secrets**: Never commit secrets to git
2. **Namespaces**: Use separate namespaces for environments
3. **Resource Limits**: Always set resource requests and limits
4. **Health Checks**: Configure liveness and readiness probes
5. **Monitoring**: Set up alerts before deploying to production
6. **Backups**: Regular backups of persistent data
7. **SSL**: Always use TLS in production
8. **Updates**: Use rolling updates for zero-downtime deployments

## See Also

- [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Full deployment guide
- [../DEPLOYMENT_CHECKLIST.md](../DEPLOYMENT_CHECKLIST.md) - Pre-deployment checklist
- [../docker/README.md](../docker/README.md) - Docker configuration
- [../Makefile](../Makefile) - Build and deployment commands

## Support

For deployment support:
- Check [DEPLOYMENT_CHECKLIST.md](../DEPLOYMENT_CHECKLIST.md)
- See [k8s/README.md](k8s/README.md) for Kubernetes details
- Open an issue on GitHub
