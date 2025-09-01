ENV_FILE=.env

# ============================================
# Help
# ============================================

help: ## Show this help
	@printf "\n"
	@printf "Available commands:\n"
	@awk '\
	/^# =+/ { getline; sub(/\r$$/,"", $$0); if ($$0 ~ /^# /) { gsub(/^# */,"", $$0); if($$0) printf "\n\033[1;34m%s:\033[0m\n", $$0 } } \
	/^[a-zA-Z0-9_.-]+:.*##/ { sub(/\r$$/,"", $$0); split($$0,a,":"); split($$0,b,"## *"); printf "  \033[36m%-25s\033[0m %s\n", a[1], b[2] }' $(MAKEFILE_LIST)
	@printf "\n"

# ============================================
# Service Management
# ============================================

build: ## Build docker containers
	docker compose --env-file $(ENV_FILE) build

up: ## Start all services
	docker compose --env-file $(ENV_FILE) up

down:  ## Stop all services
	docker compose --env-file $(ENV_FILE) down

logs:  ## Show container logs
	docker compose --env-file $(ENV_FILE) logs -f

restart:  ## Restart services (down, build, up)
	make down && make build && make up

# ============================================
# Migration Commands
# ============================================

migrate: ## Run Django migrations
	@echo "========================================="
	@echo "Django Database Migrations"
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Running Django migrations..."
	@docker compose --env-file $(ENV_FILE) run --rm web migrate-django.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Django migrations completed!"
	@echo "========================================="
