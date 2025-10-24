#!/bin/bash
# Script to help set up Kubernetes secrets for Neopilot

set -e

echo "🔐 Neopilot Secrets Setup"
echo "========================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace neopilot &> /dev/null; then
    echo -e "${YELLOW}Creating neopilot namespace...${NC}"
    kubectl create namespace neopilot
fi

echo "This script will help you create secrets for Neopilot."
echo "You can either:"
echo "  1. Enter values interactively"
echo "  2. Use environment variables"
echo "  3. Load from .env file"
echo ""

read -p "Choose option (1/2/3): " option

case $option in
    1)
        # Interactive mode
        echo -e "\n${GREEN}Interactive Mode${NC}"
        echo "Enter the following values (press Enter to skip optional ones):"
        echo ""
        
        read -p "Database URL [postgresql://neopilot:password@postgres:5432/neopilot]: " DATABASE_URL
        DATABASE_URL=${DATABASE_URL:-"postgresql://neopilot:password@postgres.neopilot.svc.cluster.local:5432/neopilot"}
        
        read -p "Redis URL [redis://redis:6379/0]: " REDIS_URL
        REDIS_URL=${REDIS_URL:-"redis://redis.neopilot.svc.cluster.local:6379/0"}
        
        read -sp "OpenAI API Key: " OPENAI_API_KEY
        echo ""
        
        read -sp "Anthropic API Key: " ANTHROPIC_API_KEY
        echo ""
        
        read -p "Vertex AI Project ID (optional): " VERTEX_AI_PROJECT
        VERTEX_AI_PROJECT=${VERTEX_AI_PROJECT:-""}
        
        read -p "Vertex AI Location [us-central1]: " VERTEX_AI_LOCATION
        VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-"us-central1"}
        
        read -sp "GitLab API Token: " GITLAB_API_TOKEN
        echo ""
        
        # Generate random secrets if not provided
        JWT_SECRET=$(openssl rand -hex 32)
        ENCRYPTION_KEY=$(openssl rand -hex 32)
        
        echo -e "\n${GREEN}Generated random JWT_SECRET and ENCRYPTION_KEY${NC}"
        ;;
        
    2)
        # Environment variables mode
        echo -e "\n${GREEN}Environment Variables Mode${NC}"
        echo "Using environment variables..."
        
        if [ -z "$DATABASE_URL" ]; then
            echo -e "${RED}Error: DATABASE_URL not set${NC}"
            exit 1
        fi
        ;;
        
    3)
        # .env file mode
        echo -e "\n${GREEN}.env File Mode${NC}"
        read -p "Path to .env file [.env]: " ENV_FILE
        ENV_FILE=${ENV_FILE:-.env}
        
        if [ ! -f "$ENV_FILE" ]; then
            echo -e "${RED}Error: $ENV_FILE not found${NC}"
            exit 1
        fi
        
        # Load .env file
        export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
        echo "Loaded variables from $ENV_FILE"
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

# Create the secret
echo -e "\n${YELLOW}Creating Kubernetes secret...${NC}"

kubectl create secret generic neopilot-secrets \
    --namespace=neopilot \
    --from-literal=DATABASE_URL="$DATABASE_URL" \
    --from-literal=REDIS_URL="$REDIS_URL" \
    --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
    --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    --from-literal=VERTEX_AI_PROJECT="${VERTEX_AI_PROJECT:-}" \
    --from-literal=VERTEX_AI_LOCATION="${VERTEX_AI_LOCATION:-us-central1}" \
    --from-literal=GITLAB_API_TOKEN="$GITLAB_API_TOKEN" \
    --from-literal=JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}" \
    --from-literal=ENCRYPTION_KEY="${ENCRYPTION_KEY:-$(openssl rand -hex 32)}" \
    --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✓ Secrets created successfully!${NC}"
echo ""
echo "To verify:"
echo "  kubectl get secret neopilot-secrets -n neopilot"
echo ""
echo "To update a secret:"
echo "  kubectl delete secret neopilot-secrets -n neopilot"
echo "  Then run this script again"
echo ""
echo -e "${YELLOW}⚠️  Important: Keep your secrets safe and never commit them to git!${NC}"
