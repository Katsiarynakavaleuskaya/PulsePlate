validate-data:
	python3 scripts/validate_data.py

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
	uvicorn app:app --reload --host 0.0.0.0 --port 8001

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
	@echo "$(GREEN)✅ Код отформатирован$(NC)"	@echo "$(YELLOW)🎨 Форматирование кода...$(NC)"
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

.PHONY: help venv setup-automation dev test test-fast cov cov-check cov-html lint fmt fmt-check security pre-commit quick-check auto-push safe-push feature sync-main status clean check-all fix-all ci smoke-auto smoke-8000 smoke-8001 docker-build docker-run docker-run-bg docker-stop docker-restart-8001


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

## Lint (flake8)
lint: ## Lint with flake8
	flake8 .

## Auto-fix (format + imports)
fmt: ## Format with black and isort

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

bandit:
	@echo "[bandit] scanning changed files via pre-commit"
	pre-commit run bandit --all-files

bandit-full:
	@echo "[bandit] full repo scan with safe excludes"
	bandit -q -r . -x frontend,node_modules,dist,build,test-results,.venv,venv,cache -s B101

lint:
	ruff check .
	black --check .
	mypy app scripts || true

.PHONY: help venv dev test cov cov-html lint fmt smoke-auto smoke-8000 smoke-8001 docker-build docker-run docker-run-bg docker-stop docker-restart-8001 bandit bandit-full
