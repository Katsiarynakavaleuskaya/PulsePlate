#!/bin/bash
# Быстрая проверка перед push - облегченная версия

set -e

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}⚡ Быстрая проверка PulsePlate${NC}"

# 1. Smoke tests (детерминированный поднабор)
echo -e "${YELLOW}🧪 Запуск smoke-тестов...${NC}"
if python -m pytest -q tests/edges tests/test_remaining_modules.py --maxfail=1; then
    echo -e "${GREEN}✅ Smoke-тесты пройдены${NC}"
else
    echo -e "${RED}❌ Smoke-тесты провалены${NC}"
    exit 1
fi

# 2. Проверка форматирования только измененных файлов
echo -e "${YELLOW}🎨 Проверка форматирования...${NC}"
if git diff --name-only --cached | grep "\.py$" | xargs -r black --check --diff; then
    echo -e "${GREEN}✅ Форматирование в порядке${NC}"
else
    echo -e "${RED}❌ Требуется форматирование${NC}"
    echo -e "${BLUE}💡 Запустите: black .${NC}"
    exit 1
fi

# 3. Быстрая проверка импортов
echo -e "${YELLOW}📦 Проверка импортов...${NC}"
if git diff --name-only --cached | grep "\.py$" | xargs -r isort --check-only --diff; then
    echo -e "${GREEN}✅ Импорты организованы${NC}"
else
    echo -e "${RED}❌ Требуется организация импортов${NC}"
    echo -e "${BLUE}💡 Запустите: isort .${NC}"
    exit 1
fi

# 4. Проверка основных ошибок
echo -e "${YELLOW}🔍 Быстрая проверка ошибок...${NC}"
if git diff --name-only --cached | grep "\.py$" | xargs -r python -m py_compile; then
    echo -e "${GREEN}✅ Синтаксис корректен${NC}"
else
    echo -e "${RED}❌ Синтаксические ошибки${NC}"
    exit 1
fi

echo -e "${GREEN}⚡ Быстрая проверка завершена успешно!${NC}"
echo -e "${BLUE}💡 Для полной проверки используйте: ./scripts/auto_push.sh${NC}"
