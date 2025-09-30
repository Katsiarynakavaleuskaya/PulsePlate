#!/bin/bash
# Простой скрипт для запуска тестов

set -e

echo "🚀 Запуск тестов PulsePlate..."

# Активируем виртуальное окружение
# Активируем виртуальное окружение
if [ ! -f ".venv/bin/activate" ]; then
    echo "❌ Виртуальное окружение не найдено. Создайте его командой: python -m venv .venv"
    exit 1
fi
source .venv/bin/activate

# Устанавливаем переменные окружения
export PYTHONPATH=".:core:app:tests"
export VIP_MODULE_ENABLED="true"
export FEATURE_PREMIUM_NUTRITION="true"
export API_KEY="test_key"
export APP_ENV="test"
export ENVIRONMENT="test"

echo "📋 Переменные окружения установлены"

# Запускаем только основные тесты
echo "🧪 Запуск основных тестов..."
python -m pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=97 -q

echo "✅ Тесты завершены"
