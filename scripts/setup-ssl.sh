#!/bin/bash
# Script to set up SSL certificates with cert-manager

set -e

echo "🔒 SSL Certificate Setup with cert-manager"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check if helm is installed
if ! command -v helm &> /dev/null; then
    echo -e "${YELLOW}Warning: helm is not installed. You'll need to install cert-manager manually.${NC}"
    echo "Visit: https://cert-manager.io/docs/installation/"
    exit 1
fi

echo -e "${BLUE}Step 1: Installing cert-manager${NC}"
echo "================================"
echo ""

# Add cert-manager Helm repository
echo "Adding cert-manager Helm repository..."
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
echo "Installing cert-manager..."
kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --version v1.13.0 \
  --set installCRDs=true \
  --wait

echo -e "${GREEN}✓ cert-manager installed${NC}"
echo ""

# Wait for cert-manager to be ready
echo "Waiting for cert-manager to be ready..."
kubectl wait --for=condition=Available --timeout=300s \
  deployment/cert-manager -n cert-manager
kubectl wait --for=condition=Available --timeout=300s \
  deployment/cert-manager-webhook -n cert-manager
kubectl wait --for=condition=Available --timeout=300s \
  deployment/cert-manager-cainjector -n cert-manager

echo -e "${GREEN}✓ cert-manager is ready${NC}"
echo ""

echo -e "${BLUE}Step 2: Configure ClusterIssuer${NC}"
echo "==============================="
echo ""

read -p "Enter your email for Let's Encrypt notifications: " EMAIL

if [ -z "$EMAIL" ]; then
    echo -e "${RED}Error: Email is required${NC}"
    exit 1
fi

# Update the cert-manager setup file with the email
sed "s/your-email@example.com/$EMAIL/g" k8s/cert-manager-setup.yaml > /tmp/cert-manager-setup.yaml

# Apply the ClusterIssuer
echo "Creating ClusterIssuers..."
kubectl apply -f /tmp/cert-manager-setup.yaml

echo -e "${GREEN}✓ ClusterIssuers created${NC}"
echo ""

echo -e "${BLUE}Step 3: Update Ingress${NC}"
echo "======================"
echo ""

read -p "Enter your domain (e.g., neopilot.yourdomain.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${YELLOW}Skipping domain configuration. You can update k8s/ingress.yaml manually.${NC}"
else
    # Update ingress with the domain
    sed "s/api.neopilot.yourdomain.com/api.$DOMAIN/g" k8s/ingress.yaml > /tmp/ingress.yaml
    sed -i.bak "s/grafana.neopilot.yourdomain.com/grafana.$DOMAIN/g" /tmp/ingress.yaml
    
    echo "Updated ingress configuration with domain: $DOMAIN"
    echo "API will be available at: https://api.$DOMAIN"
    echo "Grafana will be available at: https://grafana.$DOMAIN"
    echo ""
    
    read -p "Apply the ingress configuration now? (y/n): " APPLY
    if [ "$APPLY" = "y" ]; then
        kubectl apply -f /tmp/ingress.yaml
        echo -e "${GREEN}✓ Ingress applied${NC}"
    else
        echo "Ingress configuration saved to /tmp/ingress.yaml"
        echo "Apply it later with: kubectl apply -f /tmp/ingress.yaml"
    fi
fi

echo ""
echo -e "${GREEN}✓ SSL setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Ensure your DNS records point to your ingress controller's external IP:"
echo "   kubectl get svc -n ingress-nginx"
echo ""
echo "2. Check certificate status:"
echo "   kubectl get certificate -n neopilot"
echo "   kubectl describe certificate neopilot-tls -n neopilot"
echo ""
echo "3. View cert-manager logs if there are issues:"
echo "   kubectl logs -n cert-manager deployment/cert-manager"
echo ""
echo -e "${YELLOW}Note: Certificate provisioning may take a few minutes.${NC}"
