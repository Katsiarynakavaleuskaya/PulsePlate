#!/usr/bin/env bash
# Usage: source scripts/dev_shell.sh
# Инициализирует .venv (если отсутствует), активирует его и настраивает ключевые переменные окружения.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "❌ Запустите скрипт через 'source scripts/dev_shell.sh' (или '. scripts/dev_shell.sh')"
  exit 1
fi

create_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "🆕 Создаём виртуальное окружение в $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  echo "⬆️  Обновление pip и установка зависимостей"
  "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel >/dev/null
  if [[ -f "$ROOT_DIR/requirements.txt" ]]; then
    "$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt" >/dev/null
  fi
  if [[ -f "$ROOT_DIR/requirements-dev.txt" ]]; then
    "$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements-dev.txt" >/dev/null
  fi
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
