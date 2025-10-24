# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying Neopilot services.

## Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm (optional, for easier management)
- Container registry access

## Quick Start

### 1. Update Secrets

Edit `secrets.yaml` and replace placeholder values:

```bash
# Edit secrets
vi k8s/secrets.yaml

# Update these values:
# - DATABASE_URL
# - REDIS_URL
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY
# - GITLAB_API_TOKEN
# - JWT_SECRET
# - ENCRYPTION_KEY
```

### 2. Deploy

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# Deploy services
kubectl apply -f k8s/ai-gateway-deployment.yaml
kubectl apply -f k8s/workflow-deployment.yaml

# Deploy monitoring
kubectl apply -f k8s/prometheus-deployment.yaml

# Deploy ingress (optional)
kubectl apply -f k8s/ingress.yaml
```

### 3. Verify Deployment

```bash
# Check pods
kubectl get pods -n neopilot

# Check services
kubectl get svc -n neopilot

# View logs
kubectl logs -f deployment/ai-gateway -n neopilot
kubectl logs -f deployment/workflow-service -n neopilot
```

## Files

- **namespace.yaml** - Namespace definition
- **configmap.yaml** - Configuration settings
- **secrets.yaml** - Sensitive credentials (update before deploying!)
- **ai-gateway-deployment.yaml** - AI Gateway service deployment
- **workflow-deployment.yaml** - Workflow service deployment
- **prometheus-deployment.yaml** - Prometheus monitoring
- **ingress.yaml** - Ingress configuration

## Configuration

### Scaling

Adjust replicas in deployment files or use kubectl:

```bash
# Scale AI Gateway
kubectl scale deployment ai-gateway -n neopilot --replicas=5

# Scale Workflow Service
kubectl scale deployment workflow-service -n neopilot --replicas=3
```

### Auto-scaling

HPA (Horizontal Pod Autoscaler) is configured in deployment files:

- **AI Gateway**: 3-10 replicas based on CPU (70%) and memory (80%)
- **Workflow Service**: 2-8 replicas based on CPU (75%) and memory (85%)

### Resource Limits

Current resource allocation:

**AI Gateway:**
- Requests: 1 CPU, 2Gi memory
- Limits: 2 CPU, 4Gi memory

**Workflow Service:**
- Requests: 2 CPU, 4Gi memory
- Limits: 4 CPU, 8Gi memory

Adjust based on your workload in deployment files.

## Monitoring

### Prometheus

Access Prometheus:

```bash
kubectl port-forward -n neopilot svc/prometheus 9090:9090
```

Then open: http://localhost:9090

### Metrics

Services expose metrics at `/metrics` endpoint:

- AI Gateway: http://ai-gateway:8000/metrics
- Workflow Service: http://workflow-service:50051/metrics

## Ingress

The ingress configuration assumes:

- NGINX Ingress Controller installed
- cert-manager for TLS certificates
- Domain: `api.neopilot.example.com`

Update `ingress.yaml` with your domain before applying.

### Install NGINX Ingress

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx
```

### Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

## Troubleshooting

### Pods not starting

```bash
# Describe pod
kubectl describe pod <pod-name> -n neopilot

# Check events
kubectl get events -n neopilot --sort-by='.lastTimestamp'
```

### Service not accessible

```bash
# Check service endpoints
kubectl get endpoints -n neopilot

# Test from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- sh
curl http://ai-gateway.neopilot.svc.cluster.local:80/health
```

### High memory usage

```bash
# Check resource usage
kubectl top pods -n neopilot

# Increase memory limits in deployment files
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace neopilot

# Or delete individually
kubectl delete -f k8s/
```

## Production Recommendations

1. **Use External Secrets**: Replace `secrets.yaml` with external secret management
2. **Enable Network Policies**: Restrict pod-to-pod communication
3. **Set Resource Quotas**: Limit namespace resource usage
4. **Enable Pod Security**: Use Pod Security Standards
5. **Configure Backups**: Set up etcd and persistent volume backups
6. **Monitor Costs**: Track resource usage and costs
7. **Use GitOps**: Deploy via ArgoCD or Flux
8. **Enable Logging**: Centralize logs with ELK or Loki

## Support

For issues or questions, see the main [DEPLOYMENT.md](../docs/DEPLOYMENT.md) guide.
