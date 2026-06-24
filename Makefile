# TinyInsta — shortcuts. Datastores come online via profiles (see docs/ROADMAP.md).
COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- Lifecycle --------------------------------------------------------------
.PHONY: infra
infra: ## Start core infrastructure (traefik, postgres, redis, redpanda, keycloak)
	$(COMPOSE) --profile infra up -d

.PHONY: up
up: ## Start infra + all datastores + all application services
	$(COMPOSE) --profile infra --profile mongo --profile minio --profile neo4j --profile search --profile apps up -d

.PHONY: build
build: ## (Re)build application images
	$(COMPOSE) --profile apps build

.PHONY: ps
ps: ## Show container status
	$(COMPOSE) ps

.PHONY: logs
logs: ## Tail logs (use SVC=user-svc to target a service)
	$(COMPOSE) logs -f $(SVC)

.PHONY: down
down: ## Stop everything
	$(COMPOSE) --profile infra --profile mongo --profile minio --profile neo4j --profile search --profile apps down

.PHONY: clean
clean: ## Stop everything AND remove volumes (destroys data)
	$(COMPOSE) --profile infra --profile mongo --profile minio --profile neo4j --profile search --profile apps down -v

# --- Validation -------------------------------------------------------------
.PHONY: config
config: ## Validate the docker-compose configuration
	$(COMPOSE) --profile infra --profile apps config -q && echo "compose OK"

# --- Frontend ---------------------------------------------------------------
.PHONY: front
front: ## Run the Next.js frontend in dev mode
	cd frontend && pnpm install && pnpm dev
