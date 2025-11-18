#!/usr/bin/env bash
set -euo pipefail

echo "[CI-LOCAL] Running pre-commit checks..."
pre-commit run --all-files || true

echo "[CI-LOCAL] Backend tests (pytest) with coverage..."
pytest -q -n auto --dist=worksteal --cov=. --cov-report=term-missing

echo "[CI-LOCAL] Frontend lint..."
npm ci --prefix frontend || npm install --prefix frontend
npm run lint --prefix frontend || true

echo "[CI-LOCAL] Frontend unit tests (Vitest)..."
npm test --prefix frontend || true

echo "[CI-LOCAL] Security scans (Bandit)..."
bandit -r app core scripts

echo "[CI-LOCAL] Done."
