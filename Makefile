PY=python
PIP=pip

.PHONY: venv dev test cov lint fmt smoke

venv:
\t$(PIP) install -U pip
\t@if [ -f requirements-dev.txt ]; then $(PIP) install -r requirements-dev.txt; fi
\t@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi

dev:
\tuvicorn app:app --reload --host 0.0.0.0 --port 8001

test:
\tpytest -q

cov:
\tpytest -q --cov=app --cov=bmi_core --cov-report=term-missing --cov-report=xml

lint:
\truff check .

fmt:
\truff check . --fix
\tpython -m pip install -q ruff >/dev/null 2>&1 || true

smoke:
\tcurl -s http://127.0.0.1:8001/api/v1/health
\tcurl -s -X POST http://127.0.0.1:8001/api/v1/bmi -H "Content-Type: application/json" -d '{"weight_kg":70,"height_cm":170,"group":"general"}'

docker-restart-8001:
\t- docker rm -f bmi-app 2>/dev/null || true
\tdocker run -d --name bmi-app -p 8001:8000 bmi-app:dev
\t@echo "Open: http://127.0.0.1:8001/docs"
