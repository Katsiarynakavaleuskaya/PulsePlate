#!/usr/bin/env bash
set -euo pipefail

echo "[CI-LOCAL] Running pre-commit checks..."
if ! pre-commit run --all-files; then
  echo "[CI-LOCAL][WARN] pre-commit checks failed." >&2
fi

echo "[CI-LOCAL] Backend tests (pytest) with coverage..."
pytest -q -n auto --dist=worksteal --cov=. --cov-report=term-missing

echo "[CI-LOCAL] Frontend lint..."
npm ci --prefix frontend || npm install --prefix frontend
if ! npm run lint --prefix frontend; then
  echo "[CI-LOCAL][WARN] Frontend lint failed." >&2
fi

echo "[CI-LOCAL] Frontend unit tests (Vitest)..."
if ! npm test --prefix frontend; then
  echo "[CI-LOCAL][WARN] Frontend unit tests failed." >&2
fi

echo "[CI-LOCAL] Security scans (Bandit)..."
if ! bandit -r .; then
  echo "[CI-LOCAL][WARN] Bandit security scan failed." >&2
fi

echo "[CI-LOCAL] Done."
