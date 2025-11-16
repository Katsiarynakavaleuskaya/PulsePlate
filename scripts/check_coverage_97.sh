#!/usr/bin/env bash
# Скрипт для проверки 97% покрытия тестами

set -e

echo "🔍 Проверка покрытия тестами (цель: 97%)..."

# Устанавливаем переменные окружения
export PYTHONPATH=".:core:app:tests"
export VIP_MODULE_ENABLED="true"
export FEATURE_PREMIUM_NUTRITION="true"
export API_KEY="test-key"

# Запускаем тесты с покрытием
python -m pytest tests \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-fail-under=97 \
    -q \
    --maxfail=5

echo "✅ Покрытие тестами: 97%+ достигнуто!"
echo "📊 Отчет HTML доступен в htmlcov/index.html"
