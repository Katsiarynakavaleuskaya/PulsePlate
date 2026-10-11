#!/usr/bin/env bash
# Usage: source scripts/dev_shell.sh
# Инициализирует .venv (если отсутствует), активирует его и настраивает ключевые переменные окружения.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Source scripts/dev_shell.sh inside the supported backend container." >&2
  exit 1
fi
if [[ "$(uname -s):$(uname -m)" != "Linux:x86_64" ]]; then
  echo "Backend shell requires Linux amd64. Use make dc-up and make dc-shell; native macOS SDK is not provided." >&2
  return 1
fi
if [[ -z "${PULSEPLATE_PSYCOPG_C_SDK:-}" || -z "${PULSEPLATE_BOOTSTRAP_WHEELHOUSE:-}" ]]; then
  echo "The backend container must supply its genuine SDK and verified wheelhouse." >&2
  return 1
fi

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALLER_SCRIPT="$ROOT_DIR/scripts/ci/install_locked_python_requirements.py"

create_venv() {
  if [[ ! -f "$VENV_DIR/pyvenv.cfg" || ! -x "$VENV_DIR/bin/python" ]]; then
    echo "🆕 Создаём виртуальное окружение в $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  echo "⬆️  Обновление зависимостей через locked installer"
  PIP_REQUIRE_VIRTUALENV=1 \
    "$VENV_DIR/bin/python" "$INSTALLER_SCRIPT" \
    --python-executable "$VENV_DIR/bin/python" \
    --constraints-file "$ROOT_DIR/constraints.txt" \
    --install-dev --consume-only \
    --wheelhouse-dir "$PULSEPLATE_BOOTSTRAP_WHEELHOUSE" \
    --psycopg-sdk "$PULSEPLATE_PSYCOPG_C_SDK" \
    --require-virtualenv >/dev/null
}

if [[ ! -d "$VENV_DIR" ]] || [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  create_venv
fi

if [[ -z "${VIRTUAL_ENV:-}" || "$VIRTUAL_ENV" != "$VENV_DIR" ]]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  echo "✅ Активировано виртуальное окружение: $VENV_DIR"
fi

export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/core:$ROOT_DIR/app:$ROOT_DIR/tests"
export VIP_MODULE_ENABLED="${VIP_MODULE_ENABLED:-true}"
export APP_ENV="${APP_ENV:-local}"
export PIP_REQUIRE_VIRTUALENV=1

cat <<INFO
📦 Текущие настройки окружения:
  VIRTUAL_ENV       = $VIRTUAL_ENV
  PYTHONPATH        = $PYTHONPATH
  VIP_MODULE_ENABLED= $VIP_MODULE_ENABLED
  APP_ENV           = $APP_ENV
INFO

alias pptest='pytest -q'
alias ppcov='pytest --cov=. --cov-report=term-missing'
alias ppfix='black . --line-length 100 && isort .'
alias pplint='flake8 .'
alias ppmypy='mypy app core tests'

echo "💡 Окружение готово. Используйте pptest / ppcov / ppmypy и другие алиасы по необходимости."
