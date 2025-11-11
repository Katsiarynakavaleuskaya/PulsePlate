#!/bin/bash
# Настройка CLI алиасов для PulsePlate проекта
# Использование: source setup_cli_aliases.sh

# Определяем режим загрузки: автоматический (тихий) или интерактивный (с выводом)
AUTO_LOAD="${SETUP_ALIASES_QUIET:-false}"
# Флаг для отладки автоматического определения PROJECT_ROOT
AUTO_LOAD_DEBUG="${SETUP_ALIASES_DEBUG:-false}"

# Установка PROJECT_ROOT через переменную окружения или интерактивный ввод
if [ -z "${PROJECT_ROOT:-}" ]; then
    # Попробуем автоматически определить путь к проекту
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # Проверяем наличие pyproject.toml и либо app.py, либо app/ директории
    if [ -f "$SCRIPT_DIR/pyproject.toml" ] && { [ -f "$SCRIPT_DIR/app.py" ] || [ -d "$SCRIPT_DIR/app" ]; }; then
        # Валидация прошла успешно - устанавливаем PROJECT_ROOT
        PROJECT_ROOT="$SCRIPT_DIR"
        # Выводим подтверждение только после успешной валидации и в соответствующем режиме
        if [ "$AUTO_LOAD" != "true" ] || [ "$AUTO_LOAD_DEBUG" = "true" ]; then
            echo "🔍 Автоматически определен путь к проекту: $PROJECT_ROOT"
        fi
    else
        # Интерактивный режим только если не тихая загрузка
        if [ "$AUTO_LOAD" != "true" ]; then
            while true; do
                read -r -p "Введите путь к корню проекта PulsePlate: " PROJECT_ROOT
                if [ -n "$PROJECT_ROOT" ] && [ -d "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/pyproject.toml" ] && { [ -f "$PROJECT_ROOT/app.py" ] || [ -d "$PROJECT_ROOT/app" ]; }; then
                    break
                else
                    echo "❌ Неверный путь. Убедитесь, что директория существует и содержит pyproject.toml и app.py (или app/ директорию)"
                fi
            done
        else
            # Тихая загрузка - просто выходим если не можем определить путь
            return 0 2>/dev/null || exit 0
        fi
    fi
fi

[ "$AUTO_LOAD" != "true" ] && echo "🚀 Настройка CLI алиасов для PulsePlate..."

# Функция для создания алиаса
# Оптимизировано: проверка AUTO_LOAD вынесена в переменную для производительности
_QUIET_MODE=false
[ "$AUTO_LOAD" = "true" ] && _QUIET_MODE=true

# Counter for created aliases and functions (for summary output)
_alias_count=0

validate_command() {
    # Validate a command string before creating an alias.
    # Args:
    #   command: The command string to validate
    #   project_root: The PROJECT_ROOT path for variable expansion
    # Returns:
    #   Non-zero exit status on failure, outputs error message to stdout
    local command="$1"
    local project_root="${2:-$PROJECT_ROOT}"

    # Extract first word to determine command type
    local first_word
    first_word=$(echo "$command" | awk '{print $1}')

    # Check if command is a simple executable name (no slash, no spaces)
    if [[ "$command" != */* ]] && [[ "$command" != *" "* ]]; then
        if ! command -v "$command" >/dev/null 2>&1; then
            echo "executable not found: $command"
            return 1
        fi
    # Check if first word contains a path (contains a slash)
    elif [[ "$first_word" == */* ]]; then
        # Expand variables in the path using parameter substitution
        local expanded_path="${first_word//\$PROJECT_ROOT/$project_root}"

        if [ ! -x "$expanded_path" ]; then
            if [ ! -f "$expanded_path" ]; then
                echo "file not found: $expanded_path"
            else
                echo "file not executable: $expanded_path"
            fi
            return 1
        fi
    # Complex shell snippet - check syntax
    else
        # Expand variables for syntax check (but don't execute)
        local expanded_command="${command//\$PROJECT_ROOT/$project_root}"

        # Check if bash is available before syntax validation
        if command -v bash >/dev/null 2>&1; then
        if ! bash -n -c "$expanded_command" >/dev/null 2>&1; then
            echo "syntax error in shell command"
            return 1
            fi
        else
            # bash -n not available; skip syntax check (non-fatal)
            :
        fi
    fi

    return 0
}

create_alias() {
    local alias_name="$1"
    local command="$2"
    local target_file="${3:-}"  # Optional third parameter: file path to validate

    # If target_file is provided, validate it exists
    if [ -n "$target_file" ]; then
        # Expand the path (handle variables like $PROJECT_ROOT)
        # Using parameter substitution to safely expand $PROJECT_ROOT
        local expanded_path="${target_file//\$PROJECT_ROOT/$PROJECT_ROOT}"

        # Check if the file exists using absolute path
        if [ ! -f "$expanded_path" ]; then
            if [ "$_QUIET_MODE" = "false" ]; then
                echo "⚠️  Пропуск создания алиаса '$alias_name': файл не найден: $expanded_path"
            fi
            return 1
        fi
    fi

    # Validate the command before creating the alias
    local validation_error
    validation_error=$(validate_command "$command" "$PROJECT_ROOT")
    local validation_failed=$?

    if [ "$validation_failed" -ne 0 ]; then
        if [ "$_QUIET_MODE" = "false" ]; then
            echo "⚠️  Алиас '$alias_name' НЕ создан из-за ошибки валидации: $validation_error"
        fi
        # Skip creating alias if validation fails
        return 1
    else
        _alias_count=$((_alias_count + 1))
    fi
    # shellcheck disable=SC2139
    # SC2139 is acknowledged: $PROJECT_ROOT expands at definition time (acceptable)
    # Note: Command substitutions in aliases also freeze at definition time
    alias "$alias_name"="$command"
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
# Оптимизация: используем предвычисленную переменную
_alias_count=$((_alias_count + 3))

# Покрытие кода
create_alias "ppcov" "cd $PROJECT_ROOT && python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=xml"

# Coverage with threshold enforcement (default 97%)
# Allows overriding via PPCOV_FAIL_UNDER env variable.
create_alias "ppcov-check" "cd $PROJECT_ROOT && python -m pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=\${PPCOV_FAIL_UNDER:-97}"

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
_alias_count=$((_alias_count + 1))

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
_alias_count=$((_alias_count + 2))

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

# Claude Code with PulsePlate role
# Alias disabled due to account suspension; re-enable by uncommenting after account restoration
# TODO: Re-enable ppclaude when Claude Code account is restored; verify claude_with_role.sh is available
# create_alias "ppclaude" "$PROJECT_ROOT/scripts/claude_with_role.sh" "$PROJECT_ROOT/scripts/claude_with_role.sh"

# Выводим информацию только в интерактивном режиме
if [ "$AUTO_LOAD" != "true" ]; then
    echo ""
    echo "✅ Created $_alias_count aliases and functions"
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
    echo "🤖 Claude Code команды:"
    echo "  ⚠️  ppclaude временно отключен (аккаунт в бане)"
    echo "  claude                - Обычный Claude Code (без роли) - также отключен"
    echo ""
    echo "✅ Готово! Все алиасы активны в текущей сессии."
    echo ""
    echo "💾 Для постоянного использования добавьте в ~/.zshrc (или ~/.bashrc):"
    echo "   source $PROJECT_ROOT/setup_cli_aliases.sh"
fi
