#!/bin/bash
# Простой скрипт для запуска тестов

set -e

echo "🚀 Запуск тестов PulsePlate..."

# Активируем виртуальное окружение
source .venv/bin/activate

# Устанавливаем переменные окружения
export PYTHONPATH=".:core:app:tests"
export VIP_MODULE_ENABLED="true"
export FEATURE_PREMIUM_NUTRITION="true"
export API_KEY="test-key"
export APP_ENV="test"
export ENVIRONMENT="test"

echo "📋 Переменные окружения установлены"

# Запускаем только основные тесты
echo "🧪 Запуск основных тестов..."
python -m pytest tests/test_app_health_and_root.py tests/test_api_smoke.py tests/test_bmi_core.py tests/test_bmi_visualization.py tests/test_bodyfat.py tests/test_daily_plate.py tests/test_exports.py tests/test_food_apis.py tests/test_llm.py tests/test_nutrition_core.py tests/test_nutrition_plate.py tests/test_premium_targets.py tests/test_premium_week_api.py tests/test_product_finder.py tests/test_recipe_db.py tests/test_shoplist_basics.py tests/test_targets.py tests/test_time_utils.py tests/test_units.py tests/test_utils_extra.py tests/test_weekly_plan.py --cov=. --cov-report=term-missing --cov-fail-under=97 -q

echo "✅ Тесты завершены"
