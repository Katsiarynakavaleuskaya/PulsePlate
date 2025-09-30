#!/bin/bash
# Настройка CLI алиасов для PulsePlate проекта
# Использование: source setup_cli_aliases.sh

# Установка PROJECT_ROOT через переменную окружения или интерактивный ввод
if [ -z "$PROJECT_ROOT" ]; then
    # Попробуем автоматически определить путь к проекту
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # Проверяем наличие pyproject.toml и либо app.py, либо app/ директории
    if [ -f "$SCRIPT_DIR/pyproject.toml" ] && { [ -f "$SCRIPT_DIR/app.py" ] || [ -d "$SCRIPT_DIR/app" ]; }; then
        PROJECT_ROOT="$SCRIPT_DIR"
        echo "🔍 Автоматически определен путь к проекту: $PROJECT_ROOT"
    else
        while true; do
            read -r -p "Введите путь к корню проекта PulsePlate: " PROJECT_ROOT
            if [ -n "$PROJECT_ROOT" ] && [ -d "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/pyproject.toml" ] && { [ -f "$PROJECT_ROOT/app.py" ] || [ -d "$PROJECT_ROOT/app" ]; }; then
                break
            else
                echo "❌ Неверный путь. Убедитесь, что директория существует и содержит pyproject.toml и app.py (или app/ директорию)"
            fi
        done
    fi
fi

echo "🚀 Настройка CLI алиасов для PulsePlate..."

# Функция для создания алиаса
create_alias() {
    local alias_name="$1"
    local command="$2"
    # shellcheck disable=SC2139
    # SC2139 is safe here because we only use static paths like $PROJECT_ROOT
    alias "$alias_name"="$command"
    echo "✅ Алиас '$alias_name' создан"
}

# Переход в директорию проекта
create_alias "pp" "cd $PROJECT_ROOT"

# Тестирование
create_alias "pptest" "cd $PROJECT_ROOT && python -m pytest tests/ -v"
create_alias "pptest-quick" "cd $PROJECT_ROOT && python -m pytest tests/ -q --tb=short"
create_alias "pptest-failed" "cd $PROJECT_ROOT && python -m pytest tests/ --lf --maxfail=3 -q"
# Functions for parameterized test commands
pptest-file() {
  cd "$PROJECT_ROOT" && python -m pytest "tests/$1" -v
}
pptest-class() {
  cd "$PROJECT_ROOT" && python -m pytest "tests/$1::$2" -v
}
pptest-method() {
  cd "$PROJECT_ROOT" && python -m pytest "tests/$1::$2::$3" -v
}
echo "✅ Функция 'pptest-file' создана"
echo "✅ Функция 'pptest-class' создана"
echo "✅ Функция 'pptest-method' создана"

# Покрытие кода
create_alias "ppcov" "cd $PROJECT_ROOT && python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=xml"

# Функция для покрытия с HTML и автооткрытием браузера
ppcov-html() {
  cd "$PROJECT_ROOT" || return 1
  python -m pytest tests/ --cov=. --cov-report=html || return 1
  if command -v open >/dev/null 2>&1; then
    open htmlcov/index.html
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open htmlcov/index.html
  else
    echo 'Откройте htmlcov/index.html в браузере'
  fi
}
echo "✅ Функция 'ppcov-html' создана"

create_alias "ppcov-check" "cd $PROJECT_ROOT && python -m pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=97"

# Линтинг и форматирование
create_alias "pplint" "cd $PROJECT_ROOT && flake8 ."
create_alias "ppformat" "cd $PROJECT_ROOT && black . && isort ."
create_alias "ppformat-check" "cd $PROJECT_ROOT && black --check --diff . && isort --check-only --diff ."

# Полная проверка
create_alias "ppcheck" "cd $PROJECT_ROOT && echo '🧪 Тесты...' && python -m pytest tests/ -q && echo '📊 Покрытие...' && python -m pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=97 && echo '🔍 Линтинг...' && flake8 . && echo '🎨 Форматирование...' && black --check . && isort --check-only . && echo '✅ Все проверки пройдены!'"

# Сервер
create_alias "ppserver" "cd $PROJECT_ROOT && uvicorn app:app --reload --host 0.0.0.0 --port 8001"
create_alias "ppserver-8000" "cd $PROJECT_ROOT && uvicorn app:app --reload --host 0.0.0.0 --port 8000"

# Python с настройками проекта
create_alias "pppython" "cd $PROJECT_ROOT && python"

# Make команды
create_alias "ppmake" "cd $PROJECT_ROOT && make"
create_alias "pphelp" "cd $PROJECT_ROOT && make help"

# Git команды
create_alias "ppgit" "cd $PROJECT_ROOT && git"
create_alias "ppstatus" "cd $PROJECT_ROOT && git status"
pppush() {
  cd "$PROJECT_ROOT" || return 1
  local BRANCH
  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  if [ "$BRANCH" = "HEAD" ]; then
    echo "❌ Not on a branch (detached HEAD)"
    return 1
  fi
  git push origin "$BRANCH"
}
pppull() {
  cd "$PROJECT_ROOT" || return 1
  local BRANCH
  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  if [ "$BRANCH" = "HEAD" ]; then
    echo "❌ Not on a branch (detached HEAD)"
    return 1
  fi
  git pull origin "$BRANCH"
}
echo "✅ Функция 'pppush' создана"
echo "✅ Функция 'pppull' создана"

# Безопасные команды
create_alias "ppsafe-push" "cd $PROJECT_ROOT && make safe-push"
create_alias "ppauto-push" "cd $PROJECT_ROOT && make auto-push"

# Очистка
create_alias "ppclean" "cd $PROJECT_ROOT && make clean"

# Smoke тесты
create_alias "ppsmoke" "cd $PROJECT_ROOT && make smoke-auto"
create_alias "ppsmoke-8000" "cd $PROJECT_ROOT && make smoke-8000"
create_alias "ppsmoke-8001" "cd $PROJECT_ROOT && make smoke-8001"

# Docker команды
create_alias "ppdocker-build" "cd $PROJECT_ROOT && make docker-build"
create_alias "ppdocker-run" "cd $PROJECT_ROOT && make docker-run"
create_alias "ppdocker-stop" "cd $PROJECT_ROOT && make docker-stop"

echo ""
echo "🎯 CLI алиасы настроены!"
echo ""
echo "📋 Основные команды:"
echo "  pp                    - Переход в директорию проекта"
echo "  pptest               - Запуск всех тестов"
echo "  ppcov                - Покрытие кода"
echo "  pplint               - Линтинг"
echo "  ppformat             - Форматирование кода"
echo "  ppcheck              - Полная проверка (тесты + покрытие + линтинг + форматирование)"
echo "  ppserver             - Запуск сервера на порту 8001"
echo "  ppsafe-push          - Безопасный push"
echo "  ppauto-push          - Автоматизированный push с проверками"
echo "  pphelp               - Показать все доступные make команды"
echo ""
echo "🔧 Дополнительные команды:"
echo "  pptest-quick         - Быстрые тесты"
echo "  pptest-failed        - Только упавшие тесты"
echo "  ppcov-html           - HTML отчет покрытия"
echo "  ppformat-check       - Проверка форматирования"
echo "  ppsmoke              - Smoke тесты"
echo "  ppclean              - Очистка временных файлов"
echo ""
echo "💡 Примеры использования:"
echo "  pp && pptest && ppcov && pplint && ppsafe-push"
echo "  pp && ppcheck && ppauto-push"
echo ""
echo "✅ Готово! Все алиасы активны в текущей сессии."
echo "💾 Для постоянного использования добавьте в ~/.zshrc (или ~/.bashrc):"
echo "   source $PROJECT_ROOT/setup_cli_aliases.sh"
