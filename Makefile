# Research Deep Agent — common tasks. Run `make help` for the list.
.DEFAULT_GOAL := help
IMAGE ?= research-deep-agent:latest

.PHONY: help install test run cli image compose-up compose-down \
        k8s-deploy operator-deploy chaos storybook mcp tofu-plan tofu-apply

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

test: ## Run the test suite
	pytest -q

run: ## Run the API + control panel locally on :8080
	uvicorn server:app --host 0.0.0.0 --port 8080

cli: ## Interactive CLI (set Q="..." for a one-off)
	@if [ -n "$$Q" ]; then python main.py "$$Q"; else python main.py; fi

image: ## Build the OCI image with Cloud Native Buildpacks
	./scripts/build-image.sh $(IMAGE)

compose-up: ## Run the agent with docker compose (uses .env)
	docker compose up

compose-down: ## Stop the docker compose stack
	docker compose down

k8s-deploy: ## Deploy to Kubernetes (needs deploy/k8s/secret.yaml)
	kubectl apply -k deploy/k8s

operator-deploy: ## Install the ResearchAgent operator (CRD + RBAC + manager)
	kubectl apply -k deploy/operator/config

chaos: ## Apply Chaos Mesh resilience experiments
	kubectl apply -f deploy/chaos/

storybook: ## Run the UI component explorer (Storybook)
	cd ui && npm install && npm run storybook

mcp: ## Run the MCP server (stdio)
	python mcp_server.py

tofu-plan: ## OpenTofu plan (needs deploy/tofu/terraform.tfvars)
	cd deploy/tofu && tofu init && tofu plan

tofu-apply: ## OpenTofu apply to the target cluster
	cd deploy/tofu && tofu init && tofu apply
