.PHONY: help install test lint format clean build docker-build docker-push deploy k8s-deploy local-up local-down

# Variables
PYTHON := python3
UV := uv
DOCKER_REGISTRY ?= your-registry
IMAGE_TAG ?= latest
NAMESPACE ?= neopilot

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ Help

help: ## Display this help message
	@echo "$(BLUE)Neopilot Makefile Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install dependencies with uv
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(UV) sync --extra test
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: install ## Install development dependencies
	@echo "$(BLUE)Installing development tools...$(NC)"
	$(UV) run pre-commit install
	@echo "$(GREEN)✓ Development environment ready$(NC)"

##@ Code Quality

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	$(UV) run black src/ tests/ --line-length 120
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-fix: ## Auto-fix linting issues
	@echo "$(BLUE)Auto-fixing linting issues...$(NC)"
	@bash scripts/fix-lint.sh

lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(NC)"
	$(UV) run black --check src/ tests/
	$(UV) run flake8 src/ tests/
	$(UV) run pylint src/
	@echo "$(GREEN)✓ Linting passed$(NC)"

security: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	$(UV) run bandit -r src/
	@echo "$(GREEN)✓ Security checks passed$(NC)"

type-check: ## Run type checking with pyright
	@echo "$(BLUE)Running type checks...$(NC)"
	$(UV) run pyright src/
	@echo "$(GREEN)✓ Type checking passed$(NC)"

check: format lint security ## Run all code quality checks

##@ Testing

test: ## Run unit tests
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(UV) run pytest tests/ -v
	@echo "$(GREEN)✓ Tests passed$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(UV) run pytest tests/ \
		--cov=src \
		--cov-report=html \
		--cov-report=term \
		--cov-report=xml
	@echo "$(GREEN)✓ Coverage report generated$(NC)"
	@echo "$(YELLOW)Open htmlcov/index.html to view coverage$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(UV) run pytest src/neopilot/integration_tests/ -m integration -v
	@echo "$(GREEN)✓ Integration tests passed$(NC)"

test-all: test test-integration ## Run all tests

##@ Docker

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker build -f docker/Dockerfile.ai-gateway -t neopilot-ai-gateway:$(IMAGE_TAG) .
	docker build -f docker/Dockerfile.workflow -t neopilot-workflow:$(IMAGE_TAG) .
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-tag: ## Tag Docker images for registry
	@echo "$(BLUE)Tagging Docker images...$(NC)"
	docker tag neopilot-ai-gateway:$(IMAGE_TAG) $(DOCKER_REGISTRY)/neopilot-ai-gateway:$(IMAGE_TAG)
	docker tag neopilot-workflow:$(IMAGE_TAG) $(DOCKER_REGISTRY)/neopilot-workflow:$(IMAGE_TAG)
	@echo "$(GREEN)✓ Images tagged$(NC)"

docker-push: docker-tag ## Push Docker images to registry
	@echo "$(BLUE)Pushing Docker images...$(NC)"
	docker push $(DOCKER_REGISTRY)/neopilot-ai-gateway:$(IMAGE_TAG)
	docker push $(DOCKER_REGISTRY)/neopilot-workflow:$(IMAGE_TAG)
	@echo "$(GREEN)✓ Images pushed$(NC)"

docker-all: docker-build docker-push ## Build and push Docker images

##@ Local Development

local-up: ## Start local development environment with docker-compose
	@echo "$(BLUE)Starting local environment...$(NC)"
	docker-compose -f docker/docker-compose.yml up -d
	@echo "$(GREEN)✓ Local environment started$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)Swagger: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3000 (admin/admin)$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"

local-down: ## Stop local development environment
	@echo "$(BLUE)Stopping local environment...$(NC)"
	docker-compose -f docker/docker-compose.yml down
	@echo "$(GREEN)✓ Local environment stopped$(NC)"

local-logs: ## View logs from local environment
	docker-compose -f docker/docker-compose.yml logs -f

local-restart: local-down local-up ## Restart local environment

##@ Kubernetes

k8s-setup: ## Set up Kubernetes secrets and SSL
	@echo "$(BLUE)Setting up Kubernetes...$(NC)"
	@bash scripts/setup-secrets.sh
	@bash scripts/setup-ssl.sh
	@echo "$(GREEN)✓ Kubernetes setup complete$(NC)"

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(BLUE)Deploying to Kubernetes...$(NC)"
	kubectl apply -f deploy/k8s/namespace.yaml
	kubectl apply -f deploy/k8s/configmap.yaml
	kubectl apply -f deploy/k8s/secrets.yaml
	kubectl apply -f deploy/k8s/ai-gateway-deployment.yaml
	kubectl apply -f deploy/k8s/workflow-deployment.yaml
	kubectl apply -f deploy/k8s/prometheus-deployment.yaml
	kubectl apply -f deploy/k8s/ingress.yaml
	@echo "$(GREEN)✓ Deployed to Kubernetes$(NC)"

k8s-status: ## Check Kubernetes deployment status
	@echo "$(BLUE)Checking deployment status...$(NC)"
	kubectl get pods -n $(NAMESPACE)
	kubectl get svc -n $(NAMESPACE)
	kubectl get ingress -n $(NAMESPACE)

k8s-logs: ## View Kubernetes logs
	@echo "$(BLUE)AI Gateway logs:$(NC)"
	kubectl logs -f deployment/ai-gateway -n $(NAMESPACE)

k8s-logs-workflow: ## View Workflow Service logs
	@echo "$(BLUE)Workflow Service logs:$(NC)"
	kubectl logs -f deployment/workflow-service -n $(NAMESPACE)

k8s-delete: ## Delete Kubernetes deployment
	@echo "$(RED)Deleting Kubernetes deployment...$(NC)"
	kubectl delete namespace $(NAMESPACE)
	@echo "$(GREEN)✓ Deployment deleted$(NC)"

k8s-restart: ## Restart Kubernetes deployments
	@echo "$(BLUE)Restarting deployments...$(NC)"
	kubectl rollout restart deployment/ai-gateway -n $(NAMESPACE)
	kubectl rollout restart deployment/workflow-service -n $(NAMESPACE)
	@echo "$(GREEN)✓ Deployments restarted$(NC)"

k8s-scale-up: ## Scale up deployments
	@echo "$(BLUE)Scaling up...$(NC)"
	kubectl scale deployment ai-gateway -n $(NAMESPACE) --replicas=5
	kubectl scale deployment workflow-service -n $(NAMESPACE) --replicas=3
	@echo "$(GREEN)✓ Scaled up$(NC)"

k8s-scale-down: ## Scale down deployments
	@echo "$(BLUE)Scaling down...$(NC)"
	kubectl scale deployment ai-gateway -n $(NAMESPACE) --replicas=2
	kubectl scale deployment workflow-service -n $(NAMESPACE) --replicas=1
	@echo "$(GREEN)✓ Scaled down$(NC)"

##@ Monitoring

monitor-prometheus: ## Open Prometheus dashboard
	@echo "$(BLUE)Opening Prometheus...$(NC)"
	kubectl port-forward -n $(NAMESPACE) svc/prometheus 9090:9090 &
	@sleep 2
	@open http://localhost:9090 || xdg-open http://localhost:9090 || echo "Open http://localhost:9090"

monitor-grafana: ## Open Grafana dashboard
	@echo "$(BLUE)Opening Grafana...$(NC)"
	kubectl port-forward -n $(NAMESPACE) svc/grafana 3000:3000 &
	@sleep 2
	@open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Open http://localhost:3000"

monitor-metrics: ## View metrics endpoint
	@echo "$(BLUE)Fetching metrics...$(NC)"
	curl http://localhost:8000/metrics

##@ Database

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(UV) run alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete$(NC)"

db-rollback: ## Rollback last migration
	@echo "$(BLUE)Rolling back migration...$(NC)"
	$(UV) run alembic downgrade -1
	@echo "$(GREEN)✓ Rollback complete$(NC)"

db-shell: ## Open database shell
	@echo "$(BLUE)Opening database shell...$(NC)"
	kubectl exec -it -n $(NAMESPACE) deployment/postgres -- psql -U postgres -d neopilot

##@ Build & Release

build: ## Build Python package
	@echo "$(BLUE)Building package...$(NC)"
	$(UV) build
	@echo "$(GREEN)✓ Package built$(NC)"

publish: build ## Publish package to PyPI
	@echo "$(BLUE)Publishing to PyPI...$(NC)"
	$(UV) publish
	@echo "$(GREEN)✓ Published to PyPI$(NC)"

version: ## Show current version
	@echo "$(BLUE)Current version:$(NC)"
	@grep "version" pyproject.toml | head -1

##@ Cleanup

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache
	rm -rf .pyright_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Cleaned$(NC)"

clean-docker: ## Clean Docker images and containers
	@echo "$(BLUE)Cleaning Docker...$(NC)"
	docker-compose -f docker/docker-compose.yml down -v
	docker system prune -f
	@echo "$(GREEN)✓ Docker cleaned$(NC)"

clean-all: clean clean-docker ## Clean everything

##@ CI/CD

ci-local: check test-cov ## Run CI checks locally
	@echo "$(GREEN)✓ All CI checks passed$(NC)"

pre-commit: format lint test ## Run pre-commit checks
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

##@ Documentation

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(NC)"
	@echo "$(YELLOW)API Docs: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)ReDoc: http://localhost:8000/redoc$(NC)"

docs-generate: ## Generate API documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	$(UV) run python -m neopilot.ai_gateway.main --generate-openapi > openapi.json
	@echo "$(GREEN)✓ Documentation generated$(NC)"

##@ Utilities

shell: ## Open Python shell with project context
	@echo "$(BLUE)Opening Python shell...$(NC)"
	$(UV) run python

requirements: ## Generate requirements.txt from pyproject.toml
	@echo "$(BLUE)Generating requirements.txt...$(NC)"
	$(UV) pip compile pyproject.toml -o requirements.txt
	@echo "$(GREEN)✓ requirements.txt generated$(NC)"

update-deps: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(UV) lock --upgrade
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

health-check: ## Check service health
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)Service not healthy$(NC)"

##@ Quick Commands

dev: install-dev local-up ## Set up development environment
	@echo "$(GREEN)✓ Development environment ready!$(NC)"

prod: docker-all k8s-deploy ## Deploy to production
	@echo "$(GREEN)✓ Deployed to production!$(NC)"

verify: ci-local docker-build ## Verify everything before deployment
	@echo "$(GREEN)✓ All verifications passed!$(NC)"

all: clean install check test docker-build ## Run complete build pipeline
	@echo "$(GREEN)✓ Complete build successful!$(NC)"
