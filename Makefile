.PHONY: up down logs rebuild

up: ## Build and start everything (one command)
	docker compose up -d --build

down: ## Stop everything
	docker compose down

logs: ## Follow all logs
	docker compose logs -f

rebuild: ## Rebuild and restart
	docker compose up -d --build --force-recreate
