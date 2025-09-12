#!/bin/bash
# Скрипт для запуска проверки покрытия

echo "🚀 Запуск проверки покрытия тестов..."
echo "=================================="

# Переход в директорию проекта
cd /Users/katsiarynakavaleuskaya/BMI-App_2025_clean

# Запуск тестов с покрытием
python -m pytest tests --cov=. --cov-report=term-missing --cov-fail-under=97 -q

echo ""
echo "📊 Проверка завершена!"
echo "Для детального отчета откройте htmlcov/index.html"
