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

clean: ## Clean Docker resources for this project only
	@echo "========================================="
	@echo "Docker Project Cleanup"
	@echo "========================================="
	@echo "WARNING: This will remove Docker resources for this project only!"
	@echo "This includes:"
	@echo "  - Project containers (running and stopped)"
	@echo "  - Project volumes (DATABASE DATA WILL BE LOST!)"
	@echo "  - Project networks"
	@echo "  - Project images"
	@echo ""
	@read -p "Are you sure you want to continue? Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ]
	@echo "Stopping and removing all project services..."
	@docker compose --env-file $(ENV_FILE) down --volumes --remove-orphans --rmi all
	@echo "========================================="
	@echo "Project cleanup completed!"
	@echo "========================================="

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
	@docker compose --env-file $(ENV_FILE) run --rm -e USE_PGBOUNCER=false web migrate-django.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Django migrations completed!"
	@echo "========================================="

rebuild-indexes: ## Rebuild all missing database indexes from model definitions
	@echo "========================================="
	@echo "Database Index Rebuild Process"
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Running index rebuild..."
	@docker compose --env-file $(ENV_FILE) run --rm -e USE_PGBOUNCER=false web rebuild-indexes.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Index rebuild completed!"
	@echo "========================================="

# ============================================
# Database Seeding Commands
# ============================================

seed-all: ## Populate database with all test data (users, catalog, inventories, ratings, favorites)
	@echo "========================================="
	@echo "Database Full Seeding Process"
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Running full database seeding..."
	@docker compose --env-file $(ENV_FILE) run --rm -e USE_PGBOUNCER=false web seed-all-data.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Database seeding completed!"
	@echo "========================================="

create-admin: ## Create Django admin superuser using environment variables
	@echo "========================================="
	@echo "Django Admin User Creation"
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Creating Django admin user..."
	@docker compose --env-file $(ENV_FILE) run --rm -e USE_PGBOUNCER=false web create-admin.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Admin user creation completed!"
	@echo "========================================="

clean-all: ## Remove all test data from database (favorites, ratings, inventories, catalog, users)
	@echo "========================================="
	@echo "Database Full Cleanup Process"
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Running full database cleanup..."
	@docker compose --env-file $(ENV_FILE) run --rm -e USE_PGBOUNCER=false web clean-all-data.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Database cleanup completed!"
	@echo "========================================="
