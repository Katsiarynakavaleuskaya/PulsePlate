#!/bin/bash
# Настройка Git алиасов для автоматизации

echo "🔧 Настройка Git алиасов для PulsePlate..."

# Алиас для автоматизированного push
git config alias.autopush '!bash ./scripts/auto_push.sh'

# Алиас для быстрой проверки
git config alias.quickcheck '!bash ./scripts/quick_check.sh'

# Алиас для форматирования и автокоммита
git config alias.autoformat '!f() {
    echo "🎨 Автоформатирование кода...";
    black . && isort . &&
    git add . &&
    git commit -m "🎨 Auto-format: code style improvements" ||
    echo "Нет изменений для коммита";
}; f'

# Алиас для безопасного push в main
git config alias.safepush '!f() {
    current_branch=$(git rev-parse --abbrev-ref HEAD);
    if [[ "$current_branch" == "main" || "$current_branch" == "master" ]]; then
        echo "🛡️  Безопасный push в главную ветку...";
        bash ./scripts/auto_push.sh;
    else
        echo "🚀 Push в feature-ветку...";
        git push origin "$current_branch";
    fi;
}; f'

# Алиас для создания feature-ветки
git config alias.feature '!f() {
    if [ -z "$1" ]; then
        echo "❌ Укажите название feature: git feature <name>";
    else
        echo "🌿 Создание feature-ветки: feature/$1";
        git checkout -b "feature/$1";
        git push -u origin "feature/$1";
        echo "✅ Feature-ветка создана и настроена";
    fi;
}; f'

# Алиас для обновления main ветки
git config alias.syncmain '!f() {
    current_branch=$(git rev-parse --abbrev-ref HEAD);
    echo "🔄 Синхронизация с main...";
    git fetch origin;
    git checkout main;
    git rebase origin/main;
    if [[ "$current_branch" != "main" ]]; then
        git checkout "$current_branch";
        echo "🔀 Rebase feature-ветки на актуальный main...";
        git rebase main;
    fi;
    echo "✅ Синхронизация завершена";
}; f'

# Алиас для статуса с дополнительной информацией
git config alias.status-full '!f() {
    echo "📊 Статус репозитория PulsePlate:";
    echo "================================";
    git status;
    echo "";
    echo "📈 Статистика:";
    echo "Коммитов впереди origin: $(git rev-list --count HEAD ^origin/$(git rev-parse --abbrev-ref HEAD) 2>/dev/null || echo 0)";
    echo "Непрослеженных файлов: $(git status --porcelain | grep "^??" | wc -l)";
    echo "Измененных файлов: $(git status --porcelain | grep "^ M" | wc -l)";
    echo "";
}; f'

echo "✅ Git алиасы настроены!"
echo ""
echo "📋 Доступные команды:"
echo "  git autopush      - Полная автоматизированная проверка и push"
echo "  git quickcheck    - Быстрая проверка перед коммитом"
echo "  git autoformat    - Автоформатирование и коммит"
echo "  git safepush      - Безопасный push (с проверками для main)"
echo "  git feature <name> - Создание новой feature-ветки"
echo "  git syncmain      - Синхронизация с main веткой"
echo "  git status-full   - Расширенный статус репозитория"
echo ""
echo "💡 Пример использования:"
echo "  git feature new-nutrition-api"
echo "  # ... разработка ..."
echo "  git autoformat"
echo "  git autopush"
