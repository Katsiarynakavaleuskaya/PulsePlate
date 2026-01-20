## Default target - run all checks
all: lint test cov-check

validate-data: ensure-database-versions
	python3 scripts/validate_data.py

.PHONY: all ensure-database-versions
ensure-database-versions:
	python3 scripts/ensure_database_versions.py

# Docker targets
# 🐳 Docker Best Practices:
# - Always test builds locally: make docker-build && docker run -p 8000:8000 pulseplate:latest
# - Clean old images regularly: make docker-clean-images
# - Use versioned tags for production: docker tag pulseplate:latest pulseplate:v1.0.0
docker-build: ## Build production Docker image
	docker build -t pulseplate:latest --target production .
	docker tag pulseplate:latest pulseplate:$(shell git rev-parse --short HEAD)

docker-build-dev: ## Build development Docker image
	docker build -t pulseplate:dev --target development .

docker-run: ## Run Docker containers in background
	docker-compose up -d

docker-run-dev: ## Run development Docker containers
	docker-compose --profile dev up -d

docker-stop: ## Stop and remove Docker containers
	docker-compose down

docker-clean: ## Clean Docker containers and system
	docker-compose down -v
	docker system prune -f

docker-clean-images: ## Remove old Docker images (keep latest 3)
	@echo "Cleaning old PulsePlate images (keeping latest 3)..."
	@docker images --filter "reference=pulseplate" --format "{{.ID}} {{.CreatedAt}}" | \
		sort -k2 -r | tail -n +4 | awk '{print $$1}' | \
		xargs -r docker rmi || echo "No old images to remove"

docker-logs: ## Show Docker container logs
	docker-compose logs -f

docker-shell: ## Open shell in Docker container
	docker-compose exec pulseplate /bin/bash

health-check:
	python3 -m pytest -q tests/test_app_health_and_root.py

unit-fast:
	python3 -m pytest -q tests
SHELL := /bin/bash
PIP ?= . .venv/bin/activate && pip

# Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m # No Color

## Show this help
help:
	@echo "$(BLUE)🚀 PulsePlate - Команды автоматизации$(NC)"
	@echo "======================================"
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z0-9_.-]+:.*##/{printf "$(GREEN)%-22s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## Create & install venv deps + setup automation
venv: ## Create venv, install requirements & setup git hooks
	$(PIP) install -U pip
	@if [ -f requirements-dev.txt ]; then $(PIP) install -r requirements-dev.txt; fi
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi
	@echo "$(YELLOW)🔧 Настройка автоматизации...$(NC)"
	pre-commit install
	pre-commit install --hook-type pre-push
	chmod +x scripts/*.sh
	./scripts/setup_git_aliases.sh
	@echo "$(GREEN)✅ Окружение готово!$(NC)"

## Setup automation only (git hooks & aliases)
setup-automation: ## Setup pre-commit hooks and git aliases
	@echo "$(YELLOW)🔧 Настройка автоматизации...$(NC)"
	pre-commit install
	pre-commit install --hook-type pre-push
	chmod +x scripts/*.sh
	./scripts/setup_git_aliases.sh
	@echo "$(GREEN)✅ Автоматизация настроена!$(NC)"

## Run local dev server on :8001
dev: ## Run uvicorn on 0.0.0.0:8001 (reload)
	@echo "$(YELLOW)🔥 Запуск сервера разработки...$(NC)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

## Run tests (quiet)
test: ## Run pytest
	@echo "$(YELLOW)🧪 Запуск тестов...$(NC)"
	. .venv/bin/activate && pytest -q

## Fast tests (last failed)
test-fast: ## Run only last failed tests
	@echo "$(YELLOW)⚡ Быстрые тесты...$(NC)"
	. .venv/bin/activate && pytest --lf --maxfail=3 -q

## Coverage in terminal + XML (uses .coveragerc)
cov: ## Run coverage with pytest (term + XML)
	@echo "$(YELLOW)📊 Анализ покрытия...$(NC)"
	. .venv/bin/activate && coverage erase && coverage run -m pytest -q && coverage report -m && coverage xml
	@echo "$(GREEN)✅ Покрытие завершено$(NC)"

## Coverage check >=97%
cov-check: ## Check coverage >= 97%
	@echo "$(YELLOW)🎯 Проверка покрытия >=97%...$(NC)"
	. .venv/bin/activate && coverage run -m pytest && coverage report --fail-under=97
	@echo "$(GREEN)✅ Покрытие соответствует требованиям$(NC)"

## Diff coverage check (PR gate, >=97% on changed lines)
diff-cov: ## Check diff coverage >= 97% against origin/main
	@echo "$(YELLOW)📊 Проверка diff-coverage >=97%...$(NC)"
	. .venv/bin/activate && coverage erase && coverage run -m pytest -q && coverage xml
	diff-cover coverage.xml --compare-branch=origin/main --fail-under=97
	@echo "$(GREEN)✅ Diff-coverage соответствует требованиям$(NC)"

## Typecheck with mypy (no cache for clean runs)
typecheck: ## Run mypy typecheck on app and core
	@echo "$(YELLOW)🔬 Проверка типов (mypy)...$(NC)"
	. .venv/bin/activate && mypy --no-incremental --cache-dir=/dev/null app core
	@echo "$(GREEN)✅ Типы корректны$(NC)"

## Full verification gate (all checks must pass before push)
## NOTE: Currently runs pytest twice (test-fast + diff-cov). Optimization possible via
## single coverage run + diff-cover on existing XML. Keeping as-is for simplicity;
## can be optimized in a follow-up PR if runtime becomes a bottleneck.
verify: lint typecheck test-fast diff-cov ## Run all gates: lint + typecheck + tests + diff-coverage
	@echo "$(GREEN)🎉 Все проверки пройдены! Ready for push.$(NC)"

## Coverage HTML and open report (uses .coveragerc)
cov-html: ## Generate HTML coverage and open in browser
	@echo "$(YELLOW)📊 Создание HTML отчета...$(NC)"
	. .venv/bin/activate && coverage erase && coverage run -m pytest && coverage html && open htmlcov/index.html

## Lint (flake8)
lint: ## Lint with flake8
	@echo "$(YELLOW)🔍 Проверка качества кода...$(NC)"
	flake8 .

## Auto-fix (format + imports)
fmt: ## Format with black and isort
	@echo "$(YELLOW)🎨 Форматирование кода...$(NC)"
	black .
	isort .
	@echo "$(GREEN)✅ Код отформатирован$(NC)"

## Format check only
fmt-check: ## Check code formatting
	@echo "$(YELLOW)🔍 Проверка форматирования...$(NC)"
	black --check --diff .
	isort --check-only --diff .

## Security check
security: ## Run security checks (bandit + pip-audit)
	@echo "$(YELLOW)🔒 Проверка безопасности...$(NC)"
	bandit -r . -f json -o bandit-report.json || echo "Проверка завершена с предупреждениями"
	@if command -v pip-audit >/dev/null 2>&1; then \
		pip-audit --format=json --output=pip-audit.json || echo "Найдены уязвимости"; \
	else \
		echo "$(YELLOW)⚠️  pip-audit не установлен$(NC)"; \
	fi
	@echo "$(GREEN)✅ Проверка безопасности завершена$(NC)"

## Run all pre-commit hooks
pre-commit: ## Run all pre-commit hooks
	@echo "$(YELLOW)🔄 Запуск pre-commit хуков...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)✅ Pre-commit завершен$(NC)"

## Quick check before commit
quick-check: ## Quick check (syntax, format, imports)
	@echo "$(YELLOW)⚡ Быстрая проверка...$(NC)"
	./scripts/quick_check.sh

## Automated push with all checks
auto-push: ## Automated push with full checks
	@echo "$(YELLOW)🚀 Автоматизированный push...$(NC)"
	./scripts/auto_push.sh

## Safe push (depends on branch)
safe-push: ## Safe push (full checks for main, simple for feature)
	@echo "$(YELLOW)🛡️  Безопасный push...$(NC)"
	@current_branch=$$(git rev-parse --abbrev-ref HEAD); \
	if [[ "$$current_branch" == "main" || "$$current_branch" == "master" ]]; then \
		./scripts/auto_push.sh; \
	else \
		git push origin "$$current_branch"; \
	fi

## Create feature branch
feature: ## Create feature branch (make feature NAME=feature-name)
	@if [ -z "$(NAME)" ]; then \
		echo "$(RED)❌ Укажите название: make feature NAME=your-feature-name$(NC)"; \
	else \
		echo "$(YELLOW)🌿 Создание feature-ветки: feature/$(NAME)$(NC)"; \
		git checkout -b "feature/$(NAME)"; \
		git push -u origin "feature/$(NAME)"; \
		echo "$(GREEN)✅ Feature-ветка создана$(NC)"; \
	fi

## Sync with main branch
sync-main: ## Sync with main branch
	@echo "$(YELLOW)🔄 Синхронизация с main...$(NC)"
	@current_branch=$$(git rev-parse --abbrev-ref HEAD); \
	git fetch origin; \
	git checkout main; \
	git rebase origin/main; \
	if [[ "$$current_branch" != "main" ]]; then \
		git checkout "$$current_branch"; \
		git rebase main; \
	fi
	@echo "$(GREEN)✅ Синхронизация завершена$(NC)"

## Enhanced git status
status: ## Enhanced git status with stats
	@echo "$(BLUE)📊 Статус репозитория PulsePlate:$(NC)"
	@echo "================================"
	@git status
	@echo ""
	@echo "$(BLUE)📈 Статистика:$(NC)"
	@current_branch=$$(git rev-parse --abbrev-ref HEAD); \
	commits_ahead=$$(git rev-list --count HEAD ^origin/$$current_branch 2>/dev/null || echo "0"); \
	untracked=$$(git status --porcelain | grep "^??" | wc -l); \
	modified=$$(git status --porcelain | grep "^ M" | wc -l); \
	echo "Коммитов впереди origin: $$commits_ahead"; \
	echo "Непрослеженных файлов: $$untracked"; \
	echo "Измененных файлов: $$modified"

## Clean temporary files
clean: ## Clean temporary files
	@echo "$(YELLOW)🧹 Очистка временных файлов...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/
	rm -f bandit-report.json pip-audit.json
	@echo "$(GREEN)✅ Очистка завершена$(NC)"

## Full quality check
check-all: fmt-check lint cov-check security ## Full quality check
	@echo "$(GREEN)🎉 Все проверки пройдены успешно!$(NC)"

## Fix all auto-fixable issues
fix-all: fmt lint ## Fix all auto-fixable issues
	@echo "$(GREEN)🔧 Все исправления применены$(NC)"

## CI/CD commands
ci: test cov-check lint security ## CI/CD pipeline commands
	@echo "$(GREEN)✅ CI проверки завершены$(NC)"

## Full Bandit scan (used by pre-push hook)
## In CI mode (CI=true), fails on MEDIUM/HIGH severity findings
## In local mode, permissive (warnings only, doesn't fail)
bandit-full:
	@echo "$(YELLOW)🔒 Полное сканирование Bandit...$(NC)"
	@if [ "$(CI)" = "true" ]; then \
		echo "$(YELLOW)CI mode: строгий режим (fail on MEDIUM/HIGH)...$(NC)"; \
		bandit -r . -c .bandit --severity-level medium -f json -o bandit-report.json; \
	else \
		echo "$(YELLOW)Local mode: разрешающий режим (warnings only)...$(NC)"; \
		bandit -r . -c .bandit --severity-level medium -f json -o bandit-report.json || true; \
	fi
	@echo "$(GREEN)✅ Bandit отчет: bandit-report.json$(NC)"

## Smoke test (auto: 8000 then 8001)
smoke-auto: ## Try health+bmi on 8000 then 8001
	@if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then \
		echo "$(YELLOW)Using 8000$(NC)"; \
		bash ./scripts/smoke.sh http://127.0.0.1:8000; \
	elif curl -fsS http://127.0.0.1:8001/api/v1/health >/dev/null 2>&1; then \
		echo "$(YELLOW)Using 8001$(NC)"; \
		bash ./scripts/smoke.sh http://127.0.0.1:8001; \
	else \
		echo "$(RED)No server found on 8000/8001$(NC)"; exit 1; \
	fi

## Smoke test on :8000
smoke-8000: ## Smoke against http://127.0.0.1:8000
	bash ./scripts/smoke.sh http://127.0.0.1:8000

## Smoke test on :8001
smoke-8001: ## Smoke against http://127.0.0.1:8001
	bash ./scripts/smoke.sh http://127.0.0.1:8001

## Generate OpenAPI schema (backend) and regenerate frontend TypeScript types
openapi: frontend-install ## Generate OpenAPI schema and regenerate FE types (deterministic)
	PYTHONPATH=. python3 scripts/generate_openapi.py
	cd frontend && npm run generate-types
## Install frontend dependencies (run once or when package.json changes)
frontend-install: ## Install frontend dependencies
	@if [ -d frontend/node_modules ] && [ -f frontend/node_modules/.package-lock.json ] \
		&& cmp -s frontend/package-lock.json frontend/node_modules/.package-lock.json; then \
		echo "Frontend dependencies already installed"; \
	else \
		cd frontend && npm install --no-audit --no-fund && \
		cp package-lock.json node_modules/.package-lock.json; \
	fi

## Verify OpenAPI schema + generated TypeScript types are in sync (no git diff)
openapi-check: openapi ## Verify OpenAPI + generated FE types are committed (fails on diff)
	git diff --exit-code -- frontend/src/api/openapi.json frontend/src/api/schema.ts

## Run iOS unit tests (xcodebuild test)
## NOTE: Using -project instead of -workspace due to scheme configuration issue.
## Uses iPhone 17 locally (iPhone 16 may not exist on local machine).
## CI uses iPhone 16 (available on GitHub runner).
ios-test: ## Run iOS unit tests (recommended before pushing iOS PR)
	@echo "$(YELLOW)🧪 Запуск iOS unit tests...$(NC)"
	cd ios && xcodebuild test \
		-project PulsePlate.xcodeproj \
		-scheme PulsePlate \
		-destination 'platform=iOS Simulator,name=iPhone 17,OS=latest' \
		-configuration Debug \
		-derivedDataPath ../.derivedData \
		-enableCodeCoverage NO
	@echo "$(GREEN)✅ iOS тесты пройдены$(NC)"

.PHONY: all help venv setup-automation dev test test-fast cov cov-check cov-html lint fmt fmt-check security pre-commit quick-check auto-push safe-push feature sync-main status clean check-all fix-all ci smoke-auto smoke-8000 smoke-8001 docker-build docker-build-dev docker-run docker-run-dev docker-stop docker-clean docker-logs docker-shell bandit-full diff-cov typecheck verify openapi frontend-install openapi-check ios-test
