#!/usr/bin/env bash
set -euo pipefail

echo "[CI-LOCAL] Running pre-commit checks..."
pre-commit run --all-files || true

echo "[CI-LOCAL] Backend tests (pytest) with coverage..."
pytest -q -n auto --dist=worksteal --cov=. --cov-report=term-missing

echo "[CI-LOCAL] Frontend lint..."
./scripts/frontend_npm.sh --prefix frontend ci || ./scripts/frontend_npm.sh --prefix frontend install
./scripts/frontend_npm.sh --prefix frontend run lint || true

echo "[CI-LOCAL] Frontend unit tests (Vitest)..."
./scripts/frontend_npm.sh --prefix frontend test || true

echo "[CI-LOCAL] Security scans (Bandit)..."
bandit -r . || true

echo "[CI-LOCAL] Done."
