#!/bin/bash
# Быстрая проверка перед push - облегченная версия / Lightweight pre-push helper

set -e

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}⚡ Быстрая проверка PulsePlate${NC}"

PY_COMPILE_BIN="${VENV_PYTHON:-}"
if [ -z "$PY_COMPILE_BIN" ] && [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PY_COMPILE_BIN="$VIRTUAL_ENV/bin/python"
fi
if [ -z "$PY_COMPILE_BIN" ]; then
    PY_COMPILE_BIN="$(command -v python3 || command -v python)"
fi

collect_staged_python_files() {
    STAGED_PY_FILES=()

    while IFS= read -r -d '' file; do
        if [ -n "$file" ]; then
            STAGED_PY_FILES+=("$file")
        fi
    done < <(git diff --cached --name-only -z --diff-filter=ACMR -- '*.py')
}

run_on_staged_python_files() {
    local label="$1"
    local success_message="$2"
    local failure_message="$3"
    shift 3

    echo -e "${YELLOW}${label}${NC}"

    if [ ${#STAGED_PY_FILES[@]} -eq 0 ]; then
        echo -e "${BLUE}ℹ️  Нет staged Python файлов, шаг пропущен${NC}"
        return 0
    fi

    if "$@" "${STAGED_PY_FILES[@]}"; then
        echo -e "${GREEN}${success_message}${NC}"
    else
        echo -e "${RED}${failure_message}${NC}"
        exit 1
    fi
}

collect_staged_python_files

# 1. Cheap deterministic local bundle / Дешёвый детерминированный локальный набор
echo -e "${YELLOW}🧪 Запуск cheap local validation bundle...${NC}"
make validate-min

# 2. Проверка форматирования только staged Python файлов
run_on_staged_python_files \
    "🎨 Проверка форматирования..." \
    "✅ Форматирование в порядке" \
    "❌ Требуется форматирование" \
    black --check --diff

# 3. Проверка импортов только staged Python файлов
run_on_staged_python_files \
    "📦 Проверка импортов..." \
    "✅ Импорты организованы" \
    "❌ Требуется организация импортов" \
    isort --check-only --diff

# 4. Проверка основных ошибок только staged Python файлов
run_on_staged_python_files \
    "🔍 Быстрая проверка ошибок..." \
    "✅ Синтаксис корректен" \
    "❌ Синтаксические ошибки" \
    "$PY_COMPILE_BIN" -m py_compile

echo -e "${GREEN}⚡ Быстрая проверка завершена успешно!${NC}"
echo -e "${BLUE}💡 Для diff-based проверки используйте: make validate-changed${NC}"
echo -e "${BLUE}💡 Для полного gate используйте: make verify${NC}"
