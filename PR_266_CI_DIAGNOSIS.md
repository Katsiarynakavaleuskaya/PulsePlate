# 🔍 Диагностика PR #266: Постоянные падения CI

## 📋 Проблема

PR #266 постоянно падает в CI из-за проверки покрытия тестами 97%.

## 🎯 Причины падений CI

### 1. Проверка общего покрытия (`--cov-fail-under=97`)

**Где:** `.github/workflows/ci.yml` (строки 133, 213, 299)

```yaml
python -m pytest -m "not slow" tests --cov=. --cov-report=xml --cov-report=term-missing --junitxml=tests/results.xml -o junit_family=legacy --cov-context=test -n auto --cov-fail-under=97
```

**Проблема:** Если общее покрытие проекта ниже 97%, CI падает.

### 2. Проверка покрытия измененных строк (`diff-cover --fail-under=97`)

**Где:**
- `.github/workflows/ci.yml` (строки 360-369)
- `.github/workflows/pr-tests.yml` (строки 197-208)

```bash
diff-cover coverage.xml --compare-branch origin/${{ github.base_ref }} --fail-under=97 \
  --exclude 'core/bayesian_recommendations.py' \
  --exclude 'core/bayesian_technical_utils.py' \
  --exclude 'core/business_bayesian_analyzer.py'
```

**Проблема:** Если покрытие измененных в PR строк ниже 97%, CI падает.

## 🔧 Решения

### Решение 1: Улучшить покрытие тестами (основной подход) ⭐

**Это основной и рекомендуемый подход.** Проект требует 97% покрытия, и это требование должно соблюдаться.

1. **Проверить текущее покрытие:**
   ```bash
   pytest --cov=. --cov-report=term-missing
   ```

2. **Проверить покрытие измененных файлов:**
   ```bash
   diff-cover coverage.xml --compare-branch origin/main --fail-under=97
   ```

3. **Добавить тесты для непокрытых строк:**
   - Проверить, какие файлы изменены в PR
   - Добавить тесты для непокрытых строк

### Решение 2: Добавить исключения для проблемных файлов (допустимо с обоснованием)

Если некоторые файлы сложно покрыть тестами, добавьте их в исключения:

**В `.github/workflows/ci.yml` и `.github/workflows/pr-tests.yml`:**

```bash
diff-cover coverage.xml \
  --compare-branch origin/${{ github.base_ref }} \
  --fail-under=97 \
  --exclude 'core/bayesian_recommendations.py' \
  --exclude 'core/bayesian_technical_utils.py' \
  --exclude 'core/business_bayesian_analyzer.py' \
  --exclude 'app.py'  # Если app.py не достигает 97%
  --exclude 'core/models.py'  # Если models.py не достигает 97%
```

### Решение 3: Временно снизить порог покрытия (только в крайнем случае) ⚠️

**⚠️ ВНИМАНИЕ:** Это решение требует явного одобрения от maintainers проекта перед использованием. Проект требует 97% покрытия, и снижение порога должно быть исключительной мерой.

**Когда использовать:** Только если:
- Все другие решения исчерпаны
- Получено явное одобрение от maintainers проекта
- Есть четкий план восстановления покрытия до 97%

**Файлы для изменения:**
- `.github/workflows/ci.yml` (3 места)
- `.github/workflows/pr-tests.yml` (1 место)
- `.github/workflows/nightly-tests.yml` (1 место)

**Изменения:**
```yaml
# Было:
--cov-fail-under=97
--fail-under=97

# Станет (только с одобрением):
--cov-fail-under=95
--fail-under=95
```

## 📊 Измененные файлы в PR #266

Судя по последним коммитам, изменены следующие файлы:
- `app.py` (24 изменения)
- `core/models.py` (15 изменений)
- `app/services/food_store.py` (7 изменений)
- `core/bayesian_test_analyzer.py` (2 изменения)
- Множество тестовых файлов

## 🚀 Рекомендуемые действия

1. **Проверить покрытие измененных файлов:**
   ```bash
   git diff origin/main...HEAD --name-only | grep -E '\.py$' | grep -v test
   ```

2. **Запустить diff-cover локально (если возможно):**
   ```bash
   pytest --cov=. --cov-report=xml
   diff-cover coverage.xml --compare-branch origin/main --fail-under=97
   ```

3. **Если покрытие недостаточно:**
   - Добавить тесты для непокрытых строк
   - Или добавить файлы в исключения (временно)

4. **Проверить логи CI в GitHub:**
   - Откройте PR #266
   - Посмотрите логи шага "Run diff-cover on changed lines"
   - Найдите конкретные файлы и строки с недостаточным покрытием

## 🔍 Диагностика "зависшего курсора"

Если курсор завис, это может быть связано с:
1. **Большое количество незакоммиченных изменений** - проверьте `git status`
2. **Долгие операции** - возможно, Cursor пытается проанализировать большой объем изменений
3. **Проблемы с индексацией** - перезапустите Cursor

**Решение:**
```bash
# Проверить статус
git status

# Сохранить изменения (если нужно)
git stash

# Перезапустить Cursor
# Или просто подождать - Cursor может обрабатывать большой объем данных
```

## 📝 Следующие шаги

1. ✅ Создать этот документ с диагностикой
2. ⏳ Проверить логи CI в GitHub для PR #266
3. ⏳ Определить конкретные файлы с недостаточным покрытием
4. ⏳ Добавить тесты или исключения
5. ⏳ Перезапустить CI
