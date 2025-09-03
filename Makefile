SHELL := /bin/bash
PIP ?= . .venv/bin/activate && pip

## Show this help
help:
	@echo "Available targets:" && \
	awk 'BEGIN{FS=":.*##"} /^[a-zA-Z0-9_.-]+:.*##/{printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## Create & install venv deps
venv: ## Create venv and install requirements
	$(PIP) install -U pip
	@if [ -f requirements-dev.txt ]; then $(PIP) install -r requirements-dev.txt; fi
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi

## Run local dev server on :8001
dev: ## Run uvicorn on 0.0.0.0:8001 (reload)
	uvicorn app:app --reload --host 0.0.0.0 --port 8001

## Run tests (quiet)
test: ## Run pytest
	. .venv/bin/activate && pytest -q

## Coverage in terminal + XML (uses .coveragerc)
cov: ## Run coverage with pytest (term + XML)
	. .venv/bin/activate && coverage erase && coverage run -m pytest -q && coverage report -m && coverage xml

## Coverage HTML and open report (uses .coveragerc)
cov-html: ## Generate HTML coverage and open in browser
	. .venv/bin/activate && coverage erase && coverage run -m pytest && coverage html && open htmlcov/index.html

## Lint (ruff)
lint: ## Lint with ruff
	ruff check .

## Auto-fix (ruff)
fmt: ## Format with ruff --fix
	ruff check . --fix || true

## Smoke test (auto: 8000 then 8001)
smoke-auto: ## Try health+bmi on 8000 then 8001
	@if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then \
		echo "Using 8000"; \
		bash ./scripts/smoke.sh http://127.0.0.1:8000; \
	elif curl -fsS http://127.0.0.1:8001/api/v1/health >/dev/null 2>&1; then \
		echo "Using 8001"; \
		bash ./scripts/smoke.sh http://127.0.0.1:8001; \
	else \
		echo "No server found on 8000/8001"; exit 1; \
	fi

## Smoke test on :8000
smoke-8000: ## Smoke against http://127.0.0.1:8000
	bash ./scripts/smoke.sh http://127.0.0.1:8000

## Smoke test on :8001
smoke-8001: ## Smoke against http://127.0.0.1:8001
	bash ./scripts/smoke.sh http://127.0.0.1:8001

## Build docker image
docker-build: ## docker build -t bmi-app:dev .
	docker build -t bmi-app:dev .

## Run docker (foreground) on :8000
docker-run: ## docker run --rm -p 8000:8000 bmi-app:dev
	docker run --rm -p 8000:8000 bmi-app:dev

## Run docker (background) on :8000
docker-run-bg: ## docker run -d --name bmi-app -p 8000:8000 bmi-app:dev
	docker run -d --name bmi-app -p 8000:8000 bmi-app:dev

## Stop & remove docker container
docker-stop: ## stop & remove container bmi-app
	- docker stop bmi-app 2>/dev/null || true
	- docker rm bmi-app 2>/dev/null || true

## Restart docker on :8001 (background)
docker-restart-8001: ## run -d --name bmi-app -p 8001:8000 bmi-app:dev
	- docker rm -f bmi-app 2>/dev/null || true
	docker run -d --name bmi-app -p 8001:8000 bmi-app:dev
	@echo "✅ Open: http://127.0.0.1:8001/docs"

.PHONY: help venv dev test cov cov-html lint fmt smoke-auto smoke-8000 smoke-8001 docker-build docker-run docker-run-bg docker-stop docker-restart-8001
