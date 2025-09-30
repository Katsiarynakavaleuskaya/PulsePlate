#!/bin/bash

# Активация интерпретатора для проекта PulsePlate
# Использование: source activate_interpreter.sh

echo "🚀 Активация интерпретатора для PulsePlate..."

# Получаем директорию проекта динамически на основе расположения скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# Переходим в директорию проекта
cd "$PROJECT_DIR" || { echo "❌ Ошибка: не удалось перейти в директорию $PROJECT_DIR" >&2; return 1 2>/dev/null || exit 1; }

# Проверяем существование и читаемость файла активации виртуального окружения
if [ -r ".venv/bin/activate" ]; then
    # Активируем виртуальное окружение
    source .venv/bin/activate
else
    echo "❌ Ошибка: Файл .venv/bin/activate не найден или недоступен для чтения" >&2
    echo "   Убедитесь, что виртуальное окружение создано в директории: $PROJECT_DIR" >&2
    return 1 2>/dev/null || exit 1
fi

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
echo "   pptest-file <file>: run a specific test file"
echo "   pptest-class <file> <class>: run a specific test class"
echo "   pptest-method <file> <class> <method>: run a specific test method"

echo ""
echo "🎯 Готово! Интерпретатор активирован."
