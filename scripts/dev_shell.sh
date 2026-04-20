#!/usr/bin/env bash
# Usage: source scripts/dev_shell.sh
# Инициализирует .venv (если отсутствует), активирует его и настраивает ключевые переменные окружения.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALLER_SCRIPT="$ROOT_DIR/scripts/ci/install_locked_python_requirements.py"

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "❌ Запустите скрипт через 'source scripts/dev_shell.sh' (или '. scripts/dev_shell.sh')"
  exit 1
fi

create_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "🆕 Создаём виртуальное окружение в $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  if [[ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]]; then
    echo "❌ Export PULSEPLATE_PYTHON_INDEX_URL to the approved private package proxy before bootstrapping."
    return 1
  fi

  echo "⬆️  Обновление зависимостей через locked installer"
  PIP_REQUIRE_VIRTUALENV=1 \
    "$VENV_DIR/bin/python" "$INSTALLER_SCRIPT" \
    --python-executable "$VENV_DIR/bin/python" \
    --constraints-file "$ROOT_DIR/constraints.txt" \
    --install-dev \
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
