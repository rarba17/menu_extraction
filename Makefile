# =============================================================================
# Makefile - Menu Extraction System Development & Deployment Commands
# =============================================================================
# Usage:
#   make <target>
#   make help        - Show all available commands
# =============================================================================

# ---------------------------------------------------------------------------
# Variables (override on CLI: make up ENV=production)
# ---------------------------------------------------------------------------
ENV           ?= development
APP_VERSION   ?= latest
COMPOSE_FILE  := docker-compose.yml
PROD_OVERRIDE := docker-compose.prod.yml
DEV_OVERRIDE  := docker-compose.override.yml

# Color codes for pretty output
CYAN  := \033[0;36m
GREEN := \033[0;32m
YELLOW:= \033[0;33m
RED   := \033[0;31m
RESET := \033[0m
BOLD  := \033[1m

# Always use Docker Compose v2 plugin (avoids bugs in legacy docker-compose v1.29)
DOCKER_COMPOSE := docker compose

# Build flags
BUILDKIT_ENABLED := DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1

# Production compose command
PROD_CMD := $(BUILDKIT_ENABLED) $(DOCKER_COMPOSE) \
    -f $(COMPOSE_FILE) -f $(PROD_OVERRIDE)

# Development compose command (uses auto-merged override.yml)
DEV_CMD := $(BUILDKIT_ENABLED) $(DOCKER_COMPOSE) \
    -f $(COMPOSE_FILE) -f $(DEV_OVERRIDE)

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "$(BOLD)$(CYAN)Menu Extraction System - Docker Commands$(RESET)"
	@echo "$(CYAN)===========================================$(RESET)"
	@echo ""
	@echo "$(BOLD)Usage:$(RESET) make [target] [ENV=development|production]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-25s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ---------------------------------------------------------------------------
# Build targets
# ---------------------------------------------------------------------------
.PHONY: build
build: ## Build all Docker images (development)
	@echo "$(CYAN)Building development images...$(RESET)"
	$(DEV_CMD) build --parallel
	@echo "$(GREEN)✅ Build complete.$(RESET)"

.PHONY: build-prod
build-prod: ## Build production Docker images
	@echo "$(CYAN)Building production images...$(RESET)"
	$(PROD_CMD) build --parallel --no-cache
	@echo "$(GREEN)✅ Production build complete.$(RESET)"

.PHONY: build-no-cache
build-no-cache: ## Force rebuild without Docker cache
	@echo "$(YELLOW)Building without cache...$(RESET)"
	$(DEV_CMD) build --parallel --no-cache
	@echo "$(GREEN)✅ Build (no-cache) complete.$(RESET)"

.PHONY: pull
pull: ## Pull latest base images
	@echo "$(CYAN)Pulling latest base images...$(RESET)"
	$(DEV_CMD) pull
	@echo "$(GREEN)✅ Pull complete.$(RESET)"

# ---------------------------------------------------------------------------
# Run targets
# ---------------------------------------------------------------------------
.PHONY: up
up: ## Start all services in development mode (detached)
	@echo "$(CYAN)Starting services in development mode...$(RESET)"
	$(DEV_CMD) up -d
	@echo "$(GREEN)✅ Services started!$(RESET)"
	@echo ""
	@echo "  $(BOLD)Backend :$(RESET) http://localhost:8000"
	@echo "  $(BOLD)Frontend:$(RESET) http://localhost:8501"
	@echo "  $(BOLD)Redis   :$(RESET) localhost:6379"
	@echo ""
	@echo "Run '$(CYAN)make logs$(RESET)' to follow logs."

.PHONY: up-prod
up-prod: ## Start all services in production mode
	@echo "$(CYAN)Starting services in PRODUCTION mode...$(RESET)"
	$(PROD_CMD) up -d
	@echo "$(GREEN)✅ Production services started!$(RESET)"

.PHONY: up-with-nginx
up-with-nginx: ## Start all services including Nginx
	@echo "$(CYAN)Starting services with Nginx...$(RESET)"
	$(DEV_CMD) --profile with-nginx up -d
	@echo "$(GREEN)✅ Services (+ Nginx) started on port 80.$(RESET)"

.PHONY: up-fg
up-fg: ## Start services in foreground (with live logs)
	@echo "$(CYAN)Starting services in foreground...$(RESET)"
	$(DEV_CMD) up

# ---------------------------------------------------------------------------
# Stop targets
# ---------------------------------------------------------------------------
.PHONY: down
down: ## Stop and remove all containers
	@echo "$(YELLOW)Stopping all services...$(RESET)"
	$(DEV_CMD) down
	@echo "$(GREEN)✅ All services stopped.$(RESET)"

.PHONY: stop
stop: ## Stop containers without removing them
	@echo "$(YELLOW)Stopping containers...$(RESET)"
	$(DEV_CMD) stop

.PHONY: restart
restart: ## Restart all services
	@echo "$(YELLOW)Restarting all services...$(RESET)"
	$(DEV_CMD) restart
	@echo "$(GREEN)✅ Services restarted.$(RESET)"

.PHONY: restart-backend
restart-backend: ## Restart only the backend service
	@echo "$(YELLOW)Restarting backend...$(RESET)"
	$(DEV_CMD) restart backend
	@echo "$(GREEN)✅ Backend restarted.$(RESET)"

.PHONY: restart-frontend
restart-frontend: ## Restart only the frontend service
	@echo "$(YELLOW)Restarting frontend...$(RESET)"
	$(DEV_CMD) restart frontend
	@echo "$(GREEN)✅ Frontend restarted.$(RESET)"

# ---------------------------------------------------------------------------
# Logging targets
# ---------------------------------------------------------------------------
.PHONY: logs
logs: ## Follow logs from all services
	$(DEV_CMD) logs -f --tail=100

.PHONY: logs-backend
logs-backend: ## Follow backend logs only
	$(DEV_CMD) logs -f --tail=100 backend

.PHONY: logs-frontend
logs-frontend: ## Follow frontend logs only
	$(DEV_CMD) logs -f --tail=100 frontend

.PHONY: logs-redis
logs-redis: ## Follow Redis logs only
	$(DEV_CMD) logs -f --tail=100 redis

.PHONY: logs-nginx
logs-nginx: ## Follow Nginx logs only
	$(DEV_CMD) logs -f --tail=100 nginx

# ---------------------------------------------------------------------------
# Shell access
# ---------------------------------------------------------------------------
.PHONY: shell-backend
shell-backend: ## Open a shell inside the backend container
	@echo "$(CYAN)Opening shell in backend container...$(RESET)"
	$(DEV_CMD) exec backend /bin/bash

.PHONY: shell-frontend
shell-frontend: ## Open a shell inside the frontend container
	@echo "$(CYAN)Opening shell in frontend container...$(RESET)"
	$(DEV_CMD) exec frontend /bin/bash

.PHONY: shell-redis
shell-redis: ## Open Redis CLI
	@echo "$(CYAN)Opening Redis CLI...$(RESET)"
	$(DEV_CMD) exec redis redis-cli

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
.PHONY: test
test: ## Run tests inside the backend container
	@echo "$(CYAN)Running tests...$(RESET)"
	$(DEV_CMD) exec backend python -m pytest tests/ -v --tb=short
	@echo "$(GREEN)✅ Tests complete.$(RESET)"

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	$(DEV_CMD) exec backend python -m pytest tests/ -v --tb=short -f

.PHONY: lint
lint: ## Run linters (black + isort + flake8)
	@echo "$(CYAN)Running linters...$(RESET)"
	$(DEV_CMD) exec backend black --check backend/
	$(DEV_CMD) exec backend isort --check-only backend/
	$(DEV_CMD) exec backend flake8 backend/
	@echo "$(GREEN)✅ Lint passed.$(RESET)"

.PHONY: format
format: ## Auto-format code with black and isort
	@echo "$(CYAN)Formatting code...$(RESET)"
	$(DEV_CMD) exec backend black backend/
	$(DEV_CMD) exec backend isort backend/
	@echo "$(GREEN)✅ Formatting complete.$(RESET)"

# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------
.PHONY: health
health: ## Check health of all services
	@echo "$(CYAN)Checking service health...$(RESET)"
	@echo ""
	@echo "  Backend  : $$(curl -sf http://localhost:8000/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["status"])' 2>/dev/null || echo '$(RED)UNREACHABLE$(RESET)')"
	@echo "  Frontend : $$(curl -sf http://localhost:8501/_stcore/health 2>/dev/null && echo 'ok' || echo '$(RED)UNREACHABLE$(RESET)')"
	@echo "  Redis    : $$(docker exec menu-extraction-redis redis-cli ping 2>/dev/null || echo '$(RED)UNREACHABLE$(RESET)')"
	@echo ""

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
.PHONY: ps
ps: ## Show running containers and their status
	$(DEV_CMD) ps

.PHONY: stats
stats: ## Show live resource usage (CPU/memory) for all containers
	docker stats $$($(DEV_CMD) ps -q)

# ---------------------------------------------------------------------------
# Database / Cache management
# ---------------------------------------------------------------------------
.PHONY: cache-clear
cache-clear: ## Clear the application cache via API
	@echo "$(YELLOW)Clearing cache...$(RESET)"
	@curl -sf http://localhost:8000/cache/clear | python3 -m json.tool
	@echo "$(GREEN)✅ Cache cleared.$(RESET)"

.PHONY: redis-flush
redis-flush: ## Flush all Redis data (DESTRUCTIVE)
	@echo "$(RED)WARNING: This will flush ALL Redis data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm; \
		[ "$$confirm" = "y" ] && \
		docker exec menu-extraction-redis redis-cli FLUSHALL && \
		echo "$(GREEN)✅ Redis flushed.$(RESET)" || \
		echo "Aborted."

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
.PHONY: clean
clean: ## Stop containers and remove containers, volumes, networks
	@echo "$(RED)Removing all containers, volumes and networks...$(RESET)"
	$(DEV_CMD) down -v --remove-orphans
	@echo "$(GREEN)✅ Cleanup complete.$(RESET)"

.PHONY: clean-images
clean-images: ## Remove all project Docker images
	@echo "$(RED)Removing project images...$(RESET)"
	docker rmi $$(docker images 'menu-extraction-*' -q) 2>/dev/null || true
	@echo "$(GREEN)✅ Images removed.$(RESET)"

.PHONY: clean-all
clean-all: clean clean-images ## Full cleanup (containers + volumes + images)
	docker system prune -f
	@echo "$(GREEN)✅ Full system prune complete.$(RESET)"

.PHONY: prune
prune: ## Prune unused Docker resources system-wide
	@echo "$(YELLOW)Pruning unused Docker resources...$(RESET)"
	docker system prune -f --volumes
	@echo "$(GREEN)✅ Prune complete.$(RESET)"

# ---------------------------------------------------------------------------
# Production deployment helpers
# ---------------------------------------------------------------------------
.PHONY: deploy
deploy: ## Deploy to production (build + up)
	@echo "$(CYAN)Deploying to production...$(RESET)"
	$(MAKE) build-prod
	$(PROD_CMD) up -d --remove-orphans
	@echo "$(GREEN)✅ Production deployment complete.$(RESET)"

.PHONY: rollback
rollback: ## Rollback to previous image version
	@echo "$(YELLOW)Rolling back...$(RESET)"
	$(PROD_CMD) down
	APP_VERSION=previous $(PROD_CMD) up -d
	@echo "$(GREEN)✅ Rollback complete.$(RESET)"

# ---------------------------------------------------------------------------
# Initial setup
# ---------------------------------------------------------------------------
.PHONY: setup
setup: ## Initial project setup (copy .env, create dirs)
	@echo "$(CYAN)Setting up project...$(RESET)"
	@[ -f .env ] || (cp .env.example .env && echo "$(GREEN)✅ Created .env from .env.example$(RESET). Please fill in your GEMINI_API_KEY!")
	@mkdir -p outputs logs docker/nginx/certs
	@echo "$(GREEN)✅ Setup complete.$(RESET)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  1. Edit .env and add your GEMINI_API_KEY"
	@echo "  2. Run '$(CYAN)make build$(RESET)'"
	@echo "  3. Run '$(CYAN)make up$(RESET)'"
