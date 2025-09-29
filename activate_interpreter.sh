#!/bin/bash

# Активация интерпретатора для проекта BMI-App_2025_clean
# Использование: source activate_interpreter.sh

echo "🚀 Активация интерпретатора для BMI-App_2025_clean..."

# Переходим в директорию проекта
cd /Users/katsiaryna_kavaleuskaya/Documents/BMI-App_2025_clean

# Активируем виртуальное окружение
source .venv/bin/activate

# Проверяем интерпретатор
echo "✅ Интерпретатор активирован:"
echo "   Python: $(python --version)"
echo "   Путь: $(which python)"
echo "   Рабочая директория: $(pwd)"

# Показываем доступные CLI команды
echo ""
echo "📋 Доступные CLI команды:"
echo "   pp: navigate to project folder"
echo "   pptest: run all tests"
echo "   ppcov: run tests with coverage"
echo "   pplint: linting"
echo "   ppformat: code formatting"
echo "   ppcheck: full checks (tests, coverage, linting, formatting)"
echo "   ppserver: start FastAPI server"
echo "   pppython: launch Python with project settings"
echo "   pptest_file <file>: run a specific test file"
echo "   pptest_class <file> <class>: run a specific test class"
echo "   pptest_method <file> <class> <method>: run a specific test method"

echo ""
echo "🎯 Готово! Интерпретатор активирован."
