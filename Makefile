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

## Refresh locked dependencies inside the existing .venv
venv-sync: ## Refresh .venv from locked requirements without recreating it
	@test -x .venv/bin/python || (echo "$(RED)❌ .venv missing. Run 'make venv' first.$(NC)" && exit 1)
	$(PIP) install -U pip
	@if [ -f requirements-dev.txt ]; then $(PIP) install -r requirements-dev.txt; fi
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi
	@echo "$(GREEN)✅ .venv refreshed from locked requirements$(NC)"

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

## Fast tests (deterministic smoke subset)
test-fast: ## Run smoke tests (deterministic subset)
	@echo "$(YELLOW)⚡ Smoke tests...$(NC)"
	. .venv/bin/activate && pytest -q tests/edges tests/test_remaining_modules.py --maxfail=3

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
	. .venv/bin/activate && diff-cover coverage.xml --compare-branch=origin/main --fail-under=97
	@echo "$(GREEN)✅ Diff-coverage соответствует требованиям$(NC)"

## Typecheck with mypy (no cache for clean runs)
typecheck: ## Run mypy typecheck on app and core
	@echo "$(YELLOW)🔬 Проверка типов (mypy)...$(NC)"
	. .venv/bin/activate && mypy --no-incremental --cache-dir=/dev/null app core
	@echo "$(GREEN)✅ Типы корректны$(NC)"

## Fail-fast local dependency parity check for make verify
verify-env: ## Check .venv for verify-critical locked dependencies
	@echo "$(YELLOW)🧰 Проверка parity локального verify-окружения...$(NC)"
	@test -x .venv/bin/python || (echo "$(RED)❌ .venv missing. Run 'make venv' first.$(NC)" && exit 1)
	. .venv/bin/activate && python scripts/ci/check_local_verify_environment.py
	@echo "$(GREEN)✅ Verify-окружение готово$(NC)"

## Full verification gate (all checks must pass before push)
## NOTE: Currently runs pytest twice (test-fast + diff-cov). Optimization possible via
## single coverage run + diff-cover on existing XML. Keeping as-is for simplicity;
## can be optimized in a follow-up PR if runtime becomes a bottleneck.
verify: verify-env lint typecheck test-fast diff-cov ## Run all gates: env + lint + typecheck + tests + diff-coverage
	@echo "$(GREEN)🎉 Все проверки пройдены! Ready for push.$(NC)"

# --- App Icon L4 silhouette control ------------------------------------------

ICON_SVG ?= assets/brand/icon/core/v1.0/icon_core_v1.svg
ICON_60 ?= assets/brand/icon/core/v1.0/icon_core_v1_60.png
ICON_1024 ?= assets/brand/icon/core/v1.0/icon_core_v1_1024.png

# Baseline ratios (from docs/design/EMBLEM_CORE_v1.0_LOCK.md)
ICON_BASELINE_WHITE ?= 0.0000
ICON_BASELINE_BLACK ?= 0.0000
TOKEN_PARITY_PATHS := frontend/src/styles/tokens.css frontend/src/styles/tokens.ts ios/PulsePlate/DesignSystem/DesignTokens.generated.swift ios/PulsePlate/DesignSystem/DesignTokens.swift ios/PulsePlate/Extensions/Color+Assets.swift ios/PulsePlate/Assets.xcassets/Navy.colorset/Contents.json ios/PulsePlate/Assets.xcassets/AppPrimary.colorset/Contents.json ios/PulsePlate/Assets.xcassets/AccentGreen.colorset/Contents.json ios/PulsePlate/Assets.xcassets/HeartRed.colorset/Contents.json ios/PulsePlate/Assets.xcassets/Gold.colorset/Contents.json
TOKEN_PARITY_TESTS := tests/test_design_token_parity.py tests/test_design_invariant_guard.py tests/test_frontend_raw_hex_guard.py

.PHONY: icon-silhouette-lock icon-silhouette-check design-guard tokens-build tokens-check

## Validate icon core v1.0 folder structure
icon-core-validate:
	python3 scripts/validate_icon_core_v1.py

## Enforce design invariant manifest, palette, and lock hashes
design-guard:
	python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json

## Build design-token runtime mirrors from the repo authoring tree
tokens-build:
	@echo "$(YELLOW)🎨 Building design token runtime mirrors...$(NC)"
	@missing_paths=""; \
	for path in tokens docs/design/figma-manifest.json frontend/package.json; do \
		if [ ! -e "$$path" ]; then \
			missing_paths="$$missing_paths\n$$path"; \
		fi; \
	done; \
	if [ -n "$$missing_paths" ]; then \
		printf 'Missing design token pipeline input(s):%b\n' "$$missing_paths"; \
		exit 1; \
	fi; \
	cd frontend && npm run tokens:build

## Run design-token generation hooks, drift gate, guard, and deterministic parity tests
tokens-check:
	@echo "$(YELLOW)🧪 Checking design token pipeline parity...$(NC)"
	@before_diff=$$(mktemp); \
	after_diff=$$(mktemp); \
	trap 'rm -f "$$before_diff" "$$after_diff"' EXIT; \
	git diff -- $(TOKEN_PARITY_PATHS) > "$$before_diff"; \
	$(MAKE) --no-print-directory tokens-build && \
	(cd frontend && npm run tokens:check) && \
	git diff -- $(TOKEN_PARITY_PATHS) > "$$after_diff" && \
	diff -u "$$before_diff" "$$after_diff" && \
	python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json && \
	if [ -x .venv/bin/python ]; then \
		. .venv/bin/activate && python -m pytest -q $(TOKEN_PARITY_TESTS); \
	else \
		python3 -m pytest -q $(TOKEN_PARITY_TESTS); \
	fi
	@echo "$(GREEN)✅ Design token pipeline checks passed$(NC)"

## Print silhouette hashes + density ratios (initial lock/evidence)
icon-silhouette-lock:
	shasum -a 256 "$(ICON_SVG)"
	python3 scripts/silhouette_hash.py "$(ICON_60)"
	python3 scripts/silhouette_hash.py "$(ICON_1024)"

## Enforce baseline density drift thresholds (warning >1%, hard fail >3%)
icon-silhouette-check:
	python3 scripts/silhouette_hash.py "$(ICON_60)" \
		--baseline-white-ratio "$(ICON_BASELINE_WHITE)" \
		--baseline-black-ratio "$(ICON_BASELINE_BLACK)"
	python3 scripts/silhouette_hash.py "$(ICON_1024)" \
		--baseline-white-ratio "$(ICON_BASELINE_WHITE)" \
		--baseline-black-ratio "$(ICON_BASELINE_BLACK)"

## Figma Design Execution Targets
## Usage: make design-validate SCREEN=ios.home
##        make design-execute SCREEN=ios.home
##        make design-verify

.PHONY: design-validate design-execute design-verify design-list

## List available screens for design execution
design-list:
	@echo "$(BLUE)📋 Available screens for design execution:$(NC)"
	python3 scripts/design/generate_figma_instructions.py --list-screens

## Validate design instruction for a screen (dry-run)
design-validate:
ifndef SCREEN
	@echo "$(RED)❌ Error: SCREEN not specified$(NC)"
	@echo "Usage: make design-validate SCREEN=ios.home"
	@exit 1
endif
	@echo "$(YELLOW)🔍 Validating design instruction for $(SCREEN)...$(NC)"
	python3 scripts/design/execute_design.py --screen $(SCREEN) --validate-only

## Execute design instruction for a screen via MCP
design-execute:
ifndef SCREEN
	@echo "$(RED)❌ Error: SCREEN not specified$(NC)"
	@echo "Usage: make design-execute SCREEN=ios.home"
	@exit 1
endif
	@echo "$(YELLOW)🎨 Executing design for $(SCREEN)...$(NC)"
	python3 scripts/design/execute_design.py --screen $(SCREEN) --execute

## Verify all designs against instructions
design-verify:
	@echo "$(YELLOW)✅ Verifying all designs...$(NC)"
	python3 scripts/design/verify_design.py --all

## Coverage HTML and open report (uses .coveragerc)
cov-html: ## Generate HTML coverage and open in browser
	@echo "$(YELLOW)📊 Создание HTML отчета...$(NC)"
	. .venv/bin/activate && coverage erase && coverage run -m pytest && coverage html && open htmlcov/index.html

## Lint (flake8)
lint: ## Lint with flake8
	@echo "$(YELLOW)🔍 Проверка качества кода...$(NC)"
	. .venv/bin/activate && flake8 .

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
## Usage: make ios-test [IOS_SIM_NAME="iPhone 16e"] [IOS_SIM_OS=latest]
## Optional:
## - IOS_ONLY_TESTING="Target[/Class[/test]],..." (comma-separated)
## - IOS_SKIP_TESTING="Target[/Class[/test]],..." (comma-separated)
## - IOS_DESTINATION="platform=iOS Simulator,id=<UDID>" (overrides name/OS destination)
## Default: iPhone 16e (local development). CI uses UDID-only destination (see ios/AGENTS.md).
## NOTE: Uses -project (workspace scheme has test action issue).
ios-test: ## Run iOS unit tests (recommended before pushing iOS PR)
	@echo "$(YELLOW)🧪 Запуск iOS unit tests...$(NC)"
	@SIM_NAME="$(or $(IOS_SIM_NAME),iPhone 16e)"; \
		SIM_OS="$(or $(IOS_SIM_OS),latest)"; \
		DESTINATION="$${IOS_DESTINATION:-$(IOS_DESTINATION)}"; \
		if [ -z "$$DESTINATION" ]; then DESTINATION="platform=iOS Simulator,name=$$SIM_NAME,OS=$$SIM_OS"; fi; \
		echo "Using destination: $$DESTINATION"; \
		ONLY_ITEMS="$${IOS_ONLY_TESTING:-$(IOS_ONLY_TESTING)}"; \
		SKIP_ITEMS="$${IOS_SKIP_TESTING:-$(IOS_SKIP_TESTING)}"; \
		SKIP_PROVIDED=""; \
		if [ -n "$${IOS_SKIP_TESTING+x}" ]; then SKIP_PROVIDED="1"; fi; \
		if [ "$(origin IOS_SKIP_TESTING)" != "undefined" ]; then SKIP_PROVIDED="1"; fi; \
		ONLY_FLAGS=""; \
		SKIP_FLAGS=""; \
		if [ -n "$$ONLY_ITEMS" ]; then \
			IFS=','; for t in $$ONLY_ITEMS; do t=$${t# }; t=$${t% }; [ -n "$$t" ] && ONLY_FLAGS="$$ONLY_FLAGS -only-testing:$$t"; done; unset IFS; \
		else \
			ONLY_FLAGS="-only-testing:PulsePlateTests/ThinClientGuardsTests -only-testing:PulsePlateTests/ProKeyProviderTests -only-testing:PulsePlateTests/KeychainStoreTests -only-testing:PulsePlateTests/BMIServiceTests -only-testing:PulsePlateTests/BMIResponseDecodingTests -only-testing:PulsePlateTests/BMIRequestEncodingTests -only-testing:PulsePlateTests/LocaleParsingTests -only-testing:PulsePlateTests/HTTPClientTests -only-testing:PulsePlateTests/APIClientTests -only-testing:PulsePlateTests/BMIServiceThinAdapterTests"; \
		fi; \
		if [ -z "$$ONLY_ITEMS" ] && [ -z "$$SKIP_PROVIDED" ]; then \
			SKIP_FLAGS="-skip-testing:PulsePlateUITests"; \
		fi; \
		if [ -n "$$SKIP_ITEMS" ]; then \
			IFS=','; for t in $$SKIP_ITEMS; do t=$${t# }; t=$${t% }; [ -n "$$t" ] && SKIP_FLAGS="$$SKIP_FLAGS -skip-testing:$$t"; done; unset IFS; \
		fi; \
		cd ios && xcodebuild test \
			-project PulsePlate.xcodeproj \
			-scheme PulsePlate \
			$$SKIP_FLAGS \
			$$ONLY_FLAGS \
			-destination "$$DESTINATION" \
			-configuration Debug \
			-derivedDataPath ../.derivedData \
			-enableCodeCoverage NO \
			-parallel-testing-enabled NO
	@echo "$(GREEN)✅ iOS тесты пройдены$(NC)"

.PHONY: all help venv venv-sync setup-automation dev test test-fast cov cov-check cov-html lint fmt fmt-check security pre-commit quick-check auto-push safe-push feature sync-main status clean check-all fix-all ci smoke-auto smoke-8000 smoke-8001 docker-build docker-build-dev docker-run docker-run-dev docker-stop docker-clean docker-logs docker-shell bandit-full diff-cov typecheck verify verify-env openapi frontend-install openapi-check ios-test icon-silhouette-lock icon-silhouette-check icon-core-validate design-guard tokens-build tokens-check design-validate design-execute design-verify design-list
