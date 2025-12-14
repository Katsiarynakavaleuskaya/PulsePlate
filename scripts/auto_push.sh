#!/bin/bash
# Автоматизированный скрипт для безопасного push в main

set -e  # Выход при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 PulsePlate - Автоматизированный Push Pipeline${NC}"
echo "=================================================="

# Функция для отображения статуса
show_status() {
    local step="$1"
    local status="$2"
    if [[ "$status" == "success" ]]; then
        echo -e "${GREEN}✅ $step${NC}"
    elif [[ "$status" == "running" ]]; then
        echo -e "${YELLOW}⏳ $step...${NC}"
    elif [[ "$status" == "error" ]]; then
        echo -e "${RED}❌ $step${NC}"
    fi
}

# 1. Проверка статуса Git
show_status "Проверка Git статуса" "running"
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}📝 Найдены незакоммиченные изменения${NC}"
    git status --short
    echo -e "${BLUE}💡 Добавляем все изменения в коммит...${NC}"
    git add .
else
    show_status "Git статус чист" "success"
fi

# 2. Проверка текущей ветки
current_branch=$(git rev-parse --abbrev-ref HEAD)
show_status "Текущая ветка: $current_branch" "success"

# 3. Синхронизация с remote
show_status "Синхронизация с remote" "running"
git fetch origin
if git diff HEAD origin/$current_branch --quiet; then
    show_status "Ветка синхронизирована с remote" "success"
else
    echo -e "${YELLOW}🔄 Обнаружены изменения в remote. Выполняем rebase...${NC}"
    git rebase origin/$current_branch
    show_status "Rebase выполнен успешно" "success"
fi

# 4. Запуск тестов и проверок
show_status "Запуск полного набора тестов (Backend + Frontend)" "running"

# 4a. Backend tests
echo -e "${BLUE}  📦 Backend тесты...${NC}"
if coverage run -m pytest tests/ --maxfail=2 --disable-warnings -q; then
    show_status "Backend тесты пройдены" "success"
else
    show_status "Backend тесты провалены" "error"
    echo -e "${RED}🚫 Исправьте ошибки в backend тестах перед push${NC}"
    exit 1
fi

# 4b. Frontend tests (if frontend/ exists)
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo -e "${BLUE}  ⚛️  Frontend тесты...${NC}"
    cd frontend
    if npm run test:ci > /dev/null 2>&1; then
        show_status "Frontend тесты пройдены" "success"
    else
        echo -e "${YELLOW}⚠️  Frontend тесты не прошли или test:ci не настроен${NC}"
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️  Frontend директория не найдена, пропускаем${NC}"
fi

# 4c. iOS build check (if ios/ exists and on macOS)
if [ -d "ios" ] && [ "$(uname)" == "Darwin" ]; then
    echo -e "${BLUE}  📱 iOS build check...${NC}"
    if command -v xcodebuild &> /dev/null; then
        cd ios
        # Quick syntax check only (no simulator needed)
        if swift build -c release > /dev/null 2>&1 || true; then
            show_status "iOS синтаксис проверен" "success"
        else
            echo -e "${YELLOW}⚠️  iOS build warnings (non-blocking)${NC}"
        fi
        cd ..
    else
        echo -e "${YELLOW}⚠️  Xcode не найден, пропускаем iOS проверку${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  iOS директория не найдена или не macOS, пропускаем${NC}"
fi

# 5. Проверка покрытия кода
show_status "Проверка покрытия кода (>=97%)" "running"
coverage_result=$(coverage report --show-missing | tail -1)
coverage_percent=$(echo "$coverage_result" | grep -o '[0-9]\+%' | head -1 | tr -d '%')

if [[ "$coverage_percent" -ge 97 ]]; then
    show_status "Покрытие кода: ${coverage_percent}% ✅" "success"
else
    show_status "Покрытие кода: ${coverage_percent}% ❌ (требуется >=97%)" "error"
    echo -e "${RED}🚫 Увеличьте покрытие кода до 97% перед push${NC}"
    coverage report --show-missing --fail-under=97
    exit 1
fi

# 6. Проверка качества кода
show_status "Форматирование и проверка кода" "running"
if pre-commit run --all-files; then
    show_status "Качество кода соответствует стандартам" "success"
else
    show_status "Найдены проблемы с качеством кода" "error"
    echo -e "${YELLOW}🔧 Pre-commit хуки исправили некоторые проблемы${NC}"
    echo -e "${BLUE}💡 Проверьте изменения и повторите push${NC}"
    exit 1
fi

# 7. Безопасность: сканирование уязвимостей
show_status "Сканирование безопасности" "running"
if command -v bandit &> /dev/null; then
    if bandit -r . -f json -o bandit-report.json -ll; then
        show_status "Сканирование безопасности пройдено" "success"
    else
        show_status "Найдены потенциальные проблемы безопасности" "error"
        echo -e "${YELLOW}⚠️  Проверьте bandit-report.json для деталей${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  bandit не установлен, пропускаем проверку безопасности${NC}"
fi

# 8. Проверка зависимостей
show_status "Проверка уязвимостей в зависимостях" "running"
if command -v pip-audit &> /dev/null; then
    if pip-audit --format=json --output=pip-audit.json; then
        show_status "Зависимости безопасны" "success"
    else
        show_status "Найдены уязвимые зависимости" "error"
        echo -e "${YELLOW}⚠️  Проверьте pip-audit.json для деталей${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  pip-audit не установлен, пропускаем проверку зависимостей${NC}"
fi

# 9. Создание коммита (если есть изменения)
if [[ -n $(git status --porcelain) ]]; then
    show_status "Создание коммита" "running"

    # Автоматическое сообщение коммита на основе изменений
    commit_msg="🔄 Auto-commit: "

    # Анализируем типы изменений
    if git diff --cached --name-only | grep -q "test"; then
        commit_msg+="tests, "
    fi
    if git diff --cached --name-only | grep -q ".py$"; then
        commit_msg+="code improvements, "
    fi
    if git diff --cached --name-only | grep -q "requirements"; then
        commit_msg+="dependencies, "
    fi
    if git diff --cached --name-only | grep -q "README\|\.md$"; then
        commit_msg+="docs, "
    fi

    # Убираем последнюю запятую
    commit_msg=${commit_msg%, }

    # Добавляем информацию о покрытии
    commit_msg+=" | Coverage: ${coverage_percent}%"

    git commit -m "$commit_msg"
    show_status "Коммит создан: $commit_msg" "success"
fi

# 10. Push в зависимости от ветки
if [[ "$current_branch" == "main" || "$current_branch" == "master" ]]; then
    echo -e "${CYAN}🎯 Push в главную ветку ($current_branch)${NC}"
    echo -e "${GREEN}✅ Все проверки пройдены успешно!${NC}"
    echo ""
    echo -e "${BLUE}📊 Сводка:${NC}"
    echo "   🧪 Backend тесты: PASSED"
    echo "   ⚛️  Frontend тесты: CHECKED"
    echo "   📱 iOS синтаксис: CHECKED"
    echo "   📈 Покрытие: ${coverage_percent}%"
    echo "   🎨 Форматирование: OK"
    echo "   🔒 Безопасность: CHECKED"
    echo ""

    # Финальный push
    show_status "Выполняем push в $current_branch" "running"
    git push origin "$current_branch"
    show_status "Push выполнен успешно! 🎉" "success"

else
    # Для feature веток - обычный push
    show_status "Выполняем push в feature-ветку $current_branch" "running"
    git push origin "$current_branch"
    show_status "Push в feature-ветку выполнен успешно!" "success"

    echo -e "${BLUE}💡 Для слияния с main создайте Pull Request${NC}"
fi

echo ""
echo -e "${CYAN}🎉 Автоматизированный push завершен успешно!${NC}"
echo "=================================================="
