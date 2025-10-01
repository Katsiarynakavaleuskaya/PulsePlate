#!/bin/bash
# Скрипт для запуска проверки покрытия

echo "🚀 Запуск проверки покрытия тестов..."
echo "=================================="

# Переход в директорию проекта (по расположению скрипта)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || {
  echo "❌ Не удалось определить корень проекта" >&2
  exit 1
}

# Устанавливаем порог покрытия (по умолчанию 97%)
FAIL_UNDER=${PPCOV_FAIL_UNDER:-97}

# Запуск тестов с покрытием
python -m pytest tests --cov=. --cov-report=term-missing --cov-fail-under="$FAIL_UNDER" -q

echo ""
echo "📊 Проверка завершена!"
echo "Для детального отчета откройте htmlcov/index.html"
