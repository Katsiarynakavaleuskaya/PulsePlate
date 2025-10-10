# PR Automation Guide

## Обзор

У нас есть два workflow для автоматизации PR:

1. **PR Automation** (`pr-automation.yml`) - основной workflow с CodeRabbit
2. **Quick Merge** (`quick-merge.yml`) - быстрый merge без CodeRabbit

## PR Automation (Основной)

### Как работает

1. **Ожидание CodeRabbit** (5 минут таймаут)
2. **Применение автофиксов** (ESLint, pre-commit)
3. **Запуск тестов** (с покрытием 97%)
4. **Коммит и push** изменений
5. **Финальная валидация** всех CI проверок

### Автоматический пропуск CodeRabbit

CodeRabbit автоматически пропускается в следующих случаях:

- **Большие PR**: более 50 измененных файлов
- **Явный пропуск**: в заголовке PR есть `[skip-coderabbit]`

### Примеры заголовков PR

```bash
# Обычный PR (CodeRabbit будет запущен)
feat: Add new nutrition calculation feature

# PR с пропуском CodeRabbit
feat: Add new nutrition calculation feature [skip-coderabbit]

# Большой PR (CodeRabbit автоматически пропущен)
feat: Major refactoring of core modules (75 files changed)
```

## Quick Merge (Быстрый)

### Когда использовать

- Срочные hotfix
- Малые изменения (typos, документация)
- Когда CodeRabbit занимает слишком много времени
- Для PR с уже проверенным кодом

### Как запустить

1. Перейдите в **Actions** → **Quick Merge**
2. Нажмите **Run workflow**
3. Укажите номер PR (или оставьте пустым для текущего)
4. Выберите опции:
   - `skip_tests`: пропустить тесты (осторожно!)

### Примеры использования

```bash
# Быстрый merge текущего PR
# (номер PR определяется автоматически)

# Merge конкретного PR
PR number: 123

# Merge без тестов (только для документации)
PR number: 123
Skip tests: true
```

## Настройка таймаутов

### CodeRabbit таймаут

По умолчанию: **5 минут**

Можно изменить через:

- Workflow input при ручном запуске
- Переменную окружения `CODE_RABBIT_TIMEOUT_MIN`

### CI валидация таймаут

По умолчанию: **5 минут** (300 секунд)

## Troubleshooting

### CodeRabbit не отвечает

**Проблема**: CodeRabbit занимает больше 5 минут

**Решения**:

1. Добавить `[skip-coderabbit]` в заголовок PR
2. Использовать Quick Merge workflow
3. Увеличить таймаут через workflow input

### Конфликты при merge

**Проблема**: `git pull` не удается из-за конфликтов

**Решение**:

- Workflow остановится с ошибкой
- Разрешите конфликты вручную
- Перезапустите workflow

### Тесты падают

**Проблема**: Покрытие кода ниже 97%

**Решения**:

1. Добавить тесты для непокрытого кода
2. Использовать Quick Merge с `skip_tests: true` (осторожно!)
3. Временно снизить требования к покрытию

## Best Practices

### Для обычных PR

1. Используйте стандартный PR Automation
2. Дождитесь CodeRabbit review (если не пропущен)
3. Проверьте автофиксы перед merge

### Для срочных изменений

1. Используйте Quick Merge
2. Убедитесь, что код уже проверен
3. Рассмотрите возможность пропуска тестов

### Для больших PR

1. Разбейте на несколько меньших PR
2. Используйте `[skip-coderabbit]` в заголовке
3. Рассмотрите Quick Merge для финального merge

## Мониторинг

### Логи workflow

- **Actions** → выберите workflow → выберите run
- Проверьте логи каждого job'а

### Статус CodeRabbit

- Проверьте **Pull requests** → **Files changed** → **CodeRabbit** tab
- Или в комментариях PR

### CI статус

- **Pull requests** → **Checks** tab
- Или в **Actions** → **final-validation** job

## Контакты

При проблемах с автоматизацией:

1. Проверьте логи workflow
2. Создайте issue с подробным описанием
3. Укажите номер PR и workflow run
