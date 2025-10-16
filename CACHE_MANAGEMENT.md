# Cache Management Guide

## Проблема
Python кеш файлы (`__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`) постоянно попадают в git коммиты, создавая конфликты и загрязняя репозиторий.

## Решения

### 1. Автоматическая очистка кеша
```bash
./scripts/clean-cache.sh
```

### 2. Безопасный коммит
```bash
./scripts/commit-clean.sh "Your commit message"
```

### 3. Pre-commit hook
Автоматически проверяет и блокирует коммиты с кеш файлами.

### 4. Обновленный .gitignore
Добавлены более строгие правила:
- `__pycache__/`
- `**/__pycache__/`
- `*.pyc`
- `*.pyo`
- `*.pyd`

## Использование

### Обычный workflow:
```bash
# Вместо git add . && git commit -m "message"
./scripts/commit-clean.sh "Your commit message"
```

### Ручная очистка:
```bash
./scripts/clean-cache.sh
git add .
git commit -m "Your message"
```

### Проверка статуса:
```bash
git status
```

## Настройка для новых разработчиков

1. Скопировать репозиторий
2. Настроить git hooks:
   ```bash
   git config core.hooksPath .githooks
   ```
3. Использовать `./scripts/commit-clean.sh` для коммитов

## Troubleshooting

### Если кеш файлы все еще попадают в коммит:
1. Запустить `./scripts/clean-cache.sh`
2. Проверить `.gitignore` правила
3. Убедиться что pre-commit hook активен

### Если pre-commit hook не работает:
```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
```
