# 🏗️ Boilerplate Development Makefile
# Universal commands for Django + DRF + Celery + React development
#
# 📖 Usage:
#   make help          - Show all available commands
#   make dev           - Start full development environment
#   make setup         - Initial project setup
#   make test          - Run all tests
#   make lint          - Run all linters
#
# 🔧 For new projects: Update BACKEND_APP and FRONTEND_APP variables

# 📋 Project Configuration (CUSTOMIZE FOR YOUR PROJECT)
PROJECT_NAME := boilerplate
BACKEND_APP := app
FRONTEND_APP := boilerplate-frontend
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# 🐳 Docker Configuration
COMPOSE_FILE := docker-compose.yml
DB_CONTAINER := $(PROJECT_NAME)_postgres
REDIS_CONTAINER := $(PROJECT_NAME)_redis

# 🎨 Colors for output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
RESET := \033[0m

# 🎯 Default target
.DEFAULT_GOAL := help

# 📖 Help command
.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)🏗️  $(PROJECT_NAME) Development Commands$(RESET)"
	@echo "$(CYAN)======================================$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

# 🚀 Development Environment
.PHONY: dev
dev: ## Start full development environment (DB + API + Worker + Frontend)
	@echo "$(BLUE)🚀 Starting full development environment...$(RESET)"
	@make -j 4 services backend-dev worker frontend-dev

.PHONY: services
services: ## Start PostgreSQL and Redis services
	@echo "$(CYAN)🐳 Starting database services...$(RESET)"
	@docker compose -f $(COMPOSE_FILE) up postgres redis -d
	@echo "$(GREEN)✅ Services started: PostgreSQL (5432), Redis (6379)$(RESET)"

.PHONY: services-with-tools
services-with-tools: ## Start services with GUI tools (pgAdmin + Redis Commander)
	@echo "$(CYAN)🐳 Starting services with GUI tools...$(RESET)"
	@docker compose -f $(COMPOSE_FILE) --profile tools up -d
	@echo "$(GREEN)✅ Services + Tools started:$(RESET)"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - Redis: localhost:6379"
	@echo "  - pgAdmin: http://localhost:8080 (admin@example.com / admin)"
	@echo "  - Redis Commander: http://localhost:8081 (admin / admin)"

.PHONY: backend-dev
backend-dev: ## Start Django development server
	@echo "$(YELLOW)🔧 Starting Django API server...$(RESET)"
	@cd $(BACKEND_DIR) && \
		DJANGO_SETTINGS_MODULE=$(BACKEND_APP).settings.local \
		uv run python manage.py runserver 0.0.0.0:8000

.PHONY: worker
worker: ## Start Celery worker
	@echo "$(MAGENTA)⚙️  Starting Celery worker...$(RESET)"
	@cd $(BACKEND_DIR) && \
		DJANGO_SETTINGS_MODULE=$(BACKEND_APP).settings.local \
		uv run celery -A $(BACKEND_APP) worker --loglevel=info

.PHONY: frontend-dev
frontend-dev: ## Start React development server
	@echo "$(CYAN)⚛️  Starting React frontend...$(RESET)"
	@cd $(FRONTEND_DIR) && pnpm dev

# 🔧 Setup Commands
.PHONY: setup
setup: ## Initial project setup (install dependencies + migrate)
	@echo "$(BLUE)📦 Setting up project...$(RESET)"
	@make backend-setup
	@make frontend-setup
	@make migrate
	@echo "$(GREEN)✅ Project setup complete!$(RESET)"

.PHONY: backend-setup
backend-setup: ## Setup backend dependencies and database
	@echo "$(YELLOW)🔧 Setting up backend...$(RESET)"
	@cd $(BACKEND_DIR) && uv sync
	@echo "$(GREEN)✅ Backend dependencies installed$(RESET)"

.PHONY: frontend-setup
frontend-setup: ## Setup frontend dependencies
	@echo "$(CYAN)⚛️  Setting up frontend...$(RESET)"
	@cd $(FRONTEND_DIR) && pnpm install
	@echo "$(GREEN)✅ Frontend dependencies installed$(RESET)"

# 🗄️ Database Management
.PHONY: migrate
migrate: ## Run Django migrations
	@echo "$(YELLOW)🗄️  Running database migrations...$(RESET)"
	@cd $(BACKEND_DIR) && \
		DJANGO_SETTINGS_MODULE=$(BACKEND_APP).settings.local \
		uv run python manage.py migrate
	@echo "$(GREEN)✅ Migrations complete$(RESET)"

.PHONY: makemigrations
makemigrations: ## Create Django migrations
	@echo "$(YELLOW)📝 Creating migrations...$(RESET)"
	@cd $(BACKEND_DIR) && \
		DJANGO_SETTINGS_MODULE=$(BACKEND_APP).settings.local \
		uv run python manage.py makemigrations
	@echo "$(GREEN)✅ Migrations created$(RESET)"

.PHONY: superuser
superuser: ## Create Django superuser
	@echo "$(YELLOW)👤 Creating superuser...$(RESET)"
	@cd $(BACKEND_DIR) && \
		DJANGO_SETTINGS_MODULE=$(BACKEND_APP).settings.local \
		uv run python manage.py createsuperuser

.PHONY: shell
shell: ## Open Django shell
	@cd $(BACKEND_DIR) && \
		DJANGO_SETTINGS_MODULE=$(BACKEND_APP).settings.local \
		uv run python manage.py shell

# 🧹 Code Quality
.PHONY: lint
lint: ## Run all linters (backend + frontend)
	@echo "$(BLUE)🧹 Running all linters...$(RESET)"
	@make backend-lint
	@make frontend-lint
	@echo "$(GREEN)✅ All linting complete$(RESET)"

.PHONY: backend-lint
backend-lint: ## Run backend linters (ruff + mypy)
	@echo "$(YELLOW)🔧 Linting backend code...$(RESET)"
	@cd $(BACKEND_DIR) && uv run ruff check .
	@cd $(BACKEND_DIR) && uv run ruff format --check .
	@cd $(BACKEND_DIR) && uv run mypy .
	@echo "$(GREEN)✅ Backend linting complete$(RESET)"

.PHONY: backend-fix
backend-fix: ## Fix backend code formatting
	@echo "$(YELLOW)🔧 Fixing backend code...$(RESET)"
	@cd $(BACKEND_DIR) && uv run ruff check . --fix
	@cd $(BACKEND_DIR) && uv run ruff format .
	@echo "$(GREEN)✅ Backend code fixed$(RESET)"

.PHONY: frontend-lint
frontend-lint: ## Run frontend linters (eslint + prettier + tsc)
	@echo "$(CYAN)⚛️  Linting frontend code...$(RESET)"
	@cd $(FRONTEND_DIR) && pnpm lint
	@cd $(FRONTEND_DIR) && pnpm format:check
	@echo "$(GREEN)✅ Frontend linting complete$(RESET)"

.PHONY: frontend-fix
frontend-fix: ## Fix frontend code formatting
	@echo "$(CYAN)⚛️  Fixing frontend code...$(RESET)"
	@cd $(FRONTEND_DIR) && pnpm lint:fix
	@cd $(FRONTEND_DIR) && pnpm format
	@echo "$(GREEN)✅ Frontend code fixed$(RESET)"

# 🧪 Testing
.PHONY: test
test: ## Run all tests (backend + frontend)
	@echo "$(BLUE)🧪 Running all tests...$(RESET)"
	@make backend-test
	@make frontend-test
	@echo "$(GREEN)✅ All tests complete$(RESET)"

.PHONY: backend-test
backend-test: ## Run backend tests (pytest)
	@echo "$(YELLOW)🔧 Running backend tests...$(RESET)"
	@cd $(BACKEND_DIR) && \
		DJANGO_SETTINGS_MODULE=$(BACKEND_APP).settings.local \
		uv run pytest -v
	@echo "$(GREEN)✅ Backend tests complete$(RESET)"

.PHONY: frontend-test
frontend-test: ## Run frontend unit tests (vitest)
	@echo "$(CYAN)⚛️  Running frontend tests...$(RESET)"
	@cd $(FRONTEND_DIR) && pnpm test:run
	@echo "$(GREEN)✅ Frontend tests complete$(RESET)"

.PHONY: e2e
e2e: ## Run end-to-end tests (playwright)
	@echo "$(MAGENTA)🎭 Running E2E tests...$(RESET)"
	@cd $(FRONTEND_DIR) && pnpm e2e
	@echo "$(GREEN)✅ E2E tests complete$(RESET)"

.PHONY: test-coverage
test-coverage: ## Run tests with coverage reports
	@echo "$(BLUE)📊 Running tests with coverage...$(RESET)"
	@cd $(BACKEND_DIR) && \
		DJANGO_SETTINGS_MODULE=$(BACKEND_APP).settings.local \
		uv run pytest --cov=$(BACKEND_APP) --cov-report=html --cov-report=term
	@cd $(FRONTEND_DIR) && pnpm test:run --coverage
	@echo "$(GREEN)✅ Coverage reports generated$(RESET)"

# 🧹 Cleanup
.PHONY: clean
clean: ## Clean up temporary files and caches
	@echo "$(RED)🧹 Cleaning up...$(RESET)"
	@docker compose -f $(COMPOSE_FILE) down --volumes --remove-orphans
	@cd $(BACKEND_DIR) && find . -name "*.pyc" -delete
	@cd $(BACKEND_DIR) && find . -name "__pycache__" -delete
	@cd $(FRONTEND_DIR) && rm -rf node_modules/.cache
	@cd $(FRONTEND_DIR) && rm -rf dist
	@echo "$(GREEN)✅ Cleanup complete$(RESET)"

.PHONY: reset
reset: clean ## Reset project (clean + fresh setup)
	@echo "$(RED)🔄 Resetting project...$(RESET)"
	@make setup
	@echo "$(GREEN)✅ Project reset complete$(RESET)"

# 🔄 Docker Management
.PHONY: docker-build
docker-build: ## Build production Docker images
	@echo "$(BLUE)🐳 Building Docker images...$(RESET)"
	@echo "$(YELLOW)⚠️  Production Docker setup not included in boilerplate$(RESET)"
	@echo "$(CYAN)💡 Add your production Dockerfile configurations here$(RESET)"

.PHONY: docker-up
docker-up: services ## Start all services via Docker
	@echo "$(GREEN)✅ All Docker services started$(RESET)"

.PHONY: docker-down
docker-down: ## Stop all Docker services
	@echo "$(RED)🛑 Stopping Docker services...$(RESET)"
	@docker compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✅ Docker services stopped$(RESET)"

.PHONY: docker-logs
docker-logs: ## View Docker service logs
	@docker compose -f $(COMPOSE_FILE) logs -f

# 🔍 Debugging
.PHONY: logs
logs: ## View application logs
	@echo "$(BLUE)📋 Application logs:$(RESET)"
	@docker compose -f $(COMPOSE_FILE) logs -f postgres redis

.PHONY: status
status: ## Check service status
	@echo "$(BLUE)📊 Service Status:$(RESET)"
	@docker compose -f $(COMPOSE_FILE) ps

.PHONY: health
health: ## Check application health
	@echo "$(BLUE)🏥 Health Check:$(RESET)"
	@curl -s http://localhost:8000/api/health/ | python -m json.tool || echo "$(RED)❌ API not responding$(RESET)"

# 📦 Production Helpers (customize for deployment)
.PHONY: build
build: ## Build for production
	@echo "$(BLUE)📦 Building for production...$(RESET)"
	@cd $(FRONTEND_DIR) && pnpm build
	@echo "$(YELLOW)⚠️  Add backend build steps for your deployment$(RESET)"
	@echo "$(GREEN)✅ Production build complete$(RESET)"

# 🚀 Quick Start
.PHONY: start
start: docker-up backend-setup frontend-setup migrate ## Quick start (first run)
	@echo "$(GREEN)🚀 Project ready! Run 'make dev' to start development$(RESET)"
	@echo "$(CYAN)📖 Available URLs:$(RESET)"
	@echo "  - API: http://localhost:8000"
	@echo "  - Frontend: http://localhost:5173"
	@echo "  - Admin: http://localhost:8000/admin"

# 📝 Development helpers
.PHONY: install
install: backend-setup frontend-setup ## Install all dependencies

.PHONY: update
update: ## Update all dependencies
	@echo "$(BLUE)📦 Updating dependencies...$(RESET)"
	@cd $(BACKEND_DIR) && uv sync --upgrade
	@cd $(FRONTEND_DIR) && pnpm update
	@echo "$(GREEN)✅ Dependencies updated$(RESET)"
