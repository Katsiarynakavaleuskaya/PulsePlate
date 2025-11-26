# 📋 PR #266 Rollback & Step-by-Step Integration Plan

**Date**: 2025-11-27
**Status**: Planning
**Original PR**: #266 (368 files, +35516/-5820 lines)
**Issue**: CI memory exhaustion (MemoryError during pytest collection)

---

## 🚨 Корневая причина проблемы

### Техническая диагностика

1. **Размер PR**: 368 файлов, 35,516 новых строк
2. **Тесты**: 5,273 теста (↑72 новых Bayesian тестов)
3. **Memory issue**:
   - Локально тесты требуют **32GB RAM**
   - GitHub Actions предоставляет **16GB RAM**
   - MemoryError на этапе **pytest collection** (до запуска тестов)

### Попытки решения (не сработали)

- ❌ pytest-xdist (`-n auto`) - всё равно коллектит все тесты
- ❌ Исключение Bayesian тестов (`--ignore`) - помогло частично (5273→4981), но недостаточно
- ❌ Отключение Bayesian plugin (`-p no:bayesian_plugin`) - не помогло
- ❌ Запуск только smoke тестов (`-m smoke`) - pytest всё равно коллектит 5273 теста

### Вывод

PR слишком большой для атомарной интеграции. Необходим откат и поэтапное внедрение.

---

## ✅ PLAN A: Rollback & Incremental Integration (RECOMMENDED)

### Стратегия

Закрыть PR #266, создать последовательность **маленьких PR** по 20-50 файлов каждый.

---

## 📦 Разбивка изменений на группы

### Группа 1: CI/CD Infrastructure Updates (HIGHEST PRIORITY)

**Цель**: Обновить CI/CD конфиги для поддержки будущих изменений

**Файлы** (~20 файлов):
```
.github/workflows/ci.yml
.github/workflows/pr-tests.yml
.github/workflows/pr-coverage.yml
.github/workflows/nightly-tests.yml
.github/workflows/build.yml
.github/workflows/codeql.yml
.github/workflows/trivy.yml
.github/actions/init-test-db/action.yml
.pre-commit-config.yaml
.bandit.yaml
.coveragerc
.flake8
pytest.ini
.gitignore
pyproject.toml (если изменён)
```

**PR #1**: `ci: update workflows and pre-commit configuration`

**Критерии приёмки**:
- ✅ CI проходит (все jobs зелёные)
- ✅ Coverage ≥ 97%
- ✅ No breaking changes

**Ожидаемое время**: 1-2 дня

---

### Группа 2: Core Bayesian Infrastructure (Phase 1)

**Цель**: Добавить базовые классы для Bayesian анализаторов (без функционала)

**Файлы** (~30 файлов):
```
core/bayesian/__init__.py
core/bayesian/base_analyzer.py
core/bayesian/metrics.py
core/bayesian/utils.py
tests/test_base_bayesian_analyzer.py
tests/test_bayesian_metrics.py
docs/BAYESIAN_IMPLEMENTATION_PLAN.md
docs/BAYESIAN_EXPANSION_STRATEGY.md
docs/BAYESIAN_TEST_DIAGNOSTICS.md
```

**PR #2**: `feat(bayesian): add base infrastructure for Bayesian analyzers`

**Критерии приёмки**:
- ✅ Базовые классы созданы
- ✅ Тесты покрывают базовую функциональность
- ✅ Coverage ≥ 97%
- ✅ Документация обновлена
- ✅ **ВАЖНО**: Существующий код НЕ затронут (backward compatible)

**Ожидаемое время**: 2-3 дня

---

### Группа 3: Bayesian Test Plugin & Diagnostics

**Цель**: Добавить pytest plugin для Bayesian диагностики (с фикс памяти)

**Файлы** (~25 файлов):
```
pytest_bayesian_plugin.py
conftest.py (обновление)
tests/conftest.py (обновление)
tests/test_pytest_bayesian_plugin_unit.py
tests/test_pytest_bayesian_plugin_coverage.py
tests/test_pytest_plugin_category.py
core/bayesian_test_analyzer.py
tests/test_bayesian_test_analyzer_unit.py
tests/test_bayesian_analyzer.py
```

**PR #3**: `feat(testing): add Bayesian pytest plugin with memory safety`

**КРИТИЧЕСКИ ВАЖНЫЕ ИЗМЕНЕНИЯ**:

1. **Memory leak fix** в `pytest_bayesian_plugin.py`:
```python
def pytest_collection_modifyitems(self, items):
    """Clear accumulated data IMMEDIATELY after collection."""
    # Process items...
    # CRITICAL: Clear to prevent memory leak
    self.test_contexts.clear()
    self.test_start_times.clear()
```

2. **Отключение в PR Tests**:
```yaml
# .github/workflows/pr-tests.yml
pytest -m smoke -p no:bayesian_plugin --cov=. --cov-report=xml
```

**Критерии приёмки**:
- ✅ Plugin работает в основном CI (test-pr, test-main)
- ✅ Plugin отключен в PR Tests (Fast)
- ✅ NO memory leaks (проверить локально с 5000+ тестов)
- ✅ Coverage ≥ 97%

**Ожидаемое время**: 2-3 дня

---

### Группа 4: Bayesian Nutrition Analyzer (Core Feature)

**Цель**: Добавить валидатор данных о питании

**Файлы** (~35 файлов):
```
core/nutrition_bayesian_analyzer.py
core/bayesian/nutrition_data_validator.py (если есть)
tests/test_nutrition_bayesian_analyzer_counters.py
tests/test_nutrition_bayesian_analyzer_extra.py
tests/test_nutrition_data_validator.py (если есть)
data/population_nutrition_stats.json (если есть)
config/medical_safety.yaml (если есть)
```

**PR #4**: `feat(nutrition): add Bayesian nutrition data validator`

**Критерии приёмки**:
- ✅ Валидатор работает корректно
- ✅ False positives < 5%
- ✅ Coverage ≥ 97%
- ✅ Medical safety checks работают (если включены)

**Ожидаемое время**: 3-4 дня

---

### Группа 5: Business Bayesian Analyzers

**Цель**: Добавить бизнес-аналитику

**Файлы** (~30 файлов):
```
core/business_bayesian_analyzer.py
tests/test_business_bayesian_analyzer_configs.py
tests/test_bayesian_business_and_utils.py
tests/test_comprehensive_bayesian_analyzer.py
tests/test_integrated_bayesian_analyzer.py
tests/test_comprehensive_and_integrated_analyzers.py
core/comprehensive_bayesian_analyzer.py (если есть)
```

**PR #5**: `feat(analytics): add business Bayesian analyzers`

**Критерии приёмки**:
- ✅ Анализаторы работают
- ✅ Coverage ≥ 97%
- ✅ Интеграция с существующим кодом

**Ожидаемое время**: 3-4 дня

---

### Группа 6: App Integration & API Endpoints

**Цель**: Интеграция Bayesian валидации в API

**Файлы** (~40 файлов):
```
app.py (обновление)
app/dependencies.py
app/routers/bmi_pro.py
app/routers/foods.py
app/routers/premium_week.py
app/routers/recipes.py
app/routers/vip.py
app/routers/users.py
app/routers/test.py
app/services/food_store.py
app/schemas/vip.py
tests/test_app*.py (обновления)
tests/test_vip*.py (обновления)
```

**PR #6**: `feat(api): integrate Bayesian validation into endpoints`

**Критерии приёмки**:
- ✅ Новый endpoint `/api/validate_meal` работает
- ✅ Существующие endpoints не сломаны
- ✅ Coverage ≥ 97%
- ✅ Security проверки (аутентификация, rate limiting)

**Ожидаемое время**: 3-4 дня

---

### Группа 7: Database Migrations

**Цель**: Добавить новые таблицы для Bayesian фич

**Файлы** (~10 файлов):
```
alembic/versions/202501110001_add_nutrition_tables.py
alembic/versions/202501120000_add_locale_server_default.py
alembic/versions/202501120001_add_ingredients_defaults.py
alembic/versions/202501170001_add_context_table.py
alembic/versions/202501180001_tighten_nutrition_constraints.py
```

**PR #7**: `feat(db): add migrations for Bayesian features`

**Критерии приёмки**:
- ✅ Миграции применяются корректно (up/down)
- ✅ Данные не теряются
- ✅ Тесты с новыми таблицами работают

**Ожидаемое время**: 1-2 дня

---

### Группа 8: Documentation & Scripts

**Цель**: Обновить документацию

**Файлы** (~50 файлов):
```
README.md
CHANGES_SUMMARY.md
CI_CD_FIXES_SUMMARY.md
CLAUDE.md
CONTRIBUTING.md
ПАМЯТЬ_ИСПРАВЛЕНИЯ.md
docs/BAYESIAN_*.md (все)
PR_*.md (все PR-related docs)
MEMORY_ISSUE_FIXES.md
TYPE_HINTS_SOLUTION.md
.claude/* (все файлы)
```

**PR #8**: `docs: update documentation for Bayesian features`

**Критерии приёмки**:
- ✅ Документация актуальна
- ✅ Примеры работают
- ✅ Markdown линтер проходит

**Ожидаемое время**: 1 день

---

### Группа 9: Remaining Tests & Utilities

**Цель**: Добавить оставшиеся тесты и утилиты

**Файлы** (~50 файлов):
```
tests/test_bayesian_script_runner.py
tests/test_bayesian_quality_report.py
tests/test_run_tests_bayesian_coverage.py
tests/utils/* (все обновления)
tests_strict/* (все обновления)
Прочие test_*.py файлы
```

**PR #9**: `test: add comprehensive Bayesian test suite`

**Критерии приёмки**:
- ✅ Все тесты проходят
- ✅ Coverage ≥ 97%
- ✅ NO memory issues

**Ожидаемое время**: 2-3 дня

---

### Группа 10: Config & Miscellaneous

**Цель**: Финальные конфиги и cleanup

**Файлы** (~20 файлов):
```
.cursor-settings.json
.cursor/worktrees.json
.vscode/settings.json
.python-version
update_api_key.py (удалить если устарел)
Прочие config файлы
```

**PR #10**: `chore: finalize configuration and cleanup`

**Критерии приёмки**:
- ✅ Все чистое и работает
- ✅ Нет лишних файлов
- ✅ CI проходит

**Ожидаемое время**: 1 день

---

## 📊 Timeline & Resources

### Оптимистичный сценарий

| PR# | Группа | Дней | Накопительно |
|-----|--------|------|--------------|
| 1 | CI/CD | 2 | 2 |
| 2 | Core Bayesian | 3 | 5 |
| 3 | Plugin + Memory fix | 3 | 8 |
| 4 | Nutrition Analyzer | 4 | 12 |
| 5 | Business Analyzers | 4 | 16 |
| 6 | API Integration | 4 | 20 |
| 7 | DB Migrations | 2 | 22 |
| 8 | Documentation | 1 | 23 |
| 9 | Tests | 3 | 26 |
| 10 | Config & Cleanup | 1 | 27 |

**Итого**: ~4 недели (27 дней)

### Реалистичный сценарий

С учётом:
- Code review (1-2 дня на PR)
- Фиксы замечаний
- Непредвиденные проблемы

**Итого**: ~6-8 недель

---

## 🎯 Критерии успеха

### Для каждого PR

1. ✅ **CI проходит** (все jobs зелёные)
2. ✅ **Coverage ≥ 97%** (diff-cover + общий)
3. ✅ **No breaking changes** (existing tests pass)
4. ✅ **Code review passed** (минимум 1 reviewer)
5. ✅ **Documentation updated**

### Финальный результат

1. ✅ **Все фичи из PR #266 внедрены**
2. ✅ **NO memory issues** (CI стабильно работает)
3. ✅ **Coverage ≥ 97%** maintained
4. ✅ **All tests pass** (локально и в CI)
5. ✅ **Documentation complete**

---

## 🔄 Альтернативный подход (НЕ рекомендуется)

### PLAN B: Emergency Fixes in PR #266

Если абсолютно необходимо вытянуть текущий PR:

1. **Drastically reduce test scope**:
```yaml
# .github/workflows/pr-tests.yml
pytest -m smoke --no-cov  # Отключить coverage полностью
```

2. **Rely on test-pr for full coverage**

**Риски**:
- ⚠️ PR всё равно слишком большой для review
- ⚠️ Сложно найти проблемы если что-то сломается
- ⚠️ Merge конфликты при откате

**Вердикт**: НЕ рекомендуется

---

## 🚀 Следующие шаги

### Immediate actions (сегодня)

1. ✅ **Обсудить план** с командой
2. ✅ **Закрыть PR #266** (создать issue для трекинга)
3. ✅ **Создать ветку** `feat/ci-cd-updates` от `main`
4. ✅ **Начать PR #1** (CI/CD updates)

### Tracking

**GitHub Project**: Создать доску "Bayesian Integration Rollout"

**Columns**:
- 📋 Planned
- 🔄 In Progress
- 👀 In Review
- ✅ Merged
- ❌ Blocked

**Issues**: Создать issue для каждого PR (1-10)

---

## 📝 Notes & Lessons Learned

### Проблемы PR #266

1. ❌ **Слишком большой** (368 файлов)
2. ❌ **Смешаны разные фичи** (CI, Bayesian, API, docs)
3. ❌ **Нет инкрементального тестирования**
4. ❌ **Memory issue не обнаружен до финальной стадии**

### Для будущих PR

1. ✅ **Маленькие PR** (20-50 файлов max)
2. ✅ **Одна фича на PR**
3. ✅ **Тестировать на каждом этапе**
4. ✅ **Memory profiling** для больших тестовых наборов
5. ✅ **Feature flags** для постепенного rollout

---

## 📚 Related Documentation

- [BAYESIAN_IMPLEMENTATION_PLAN.md](docs/BAYESIAN_IMPLEMENTATION_PLAN.md) - Полный план внедрения
- [BAYESIAN_EXPANSION_STRATEGY.md](docs/BAYESIAN_EXPANSION_STRATEGY.md) - Стратегия расширения
- [CI_CD_FIXES_SUMMARY.md](CI_CD_FIXES_SUMMARY.md) - История фиксов CI
- [ПАМЯТЬ_ИСПРАВЛЕНИЯ.md](ПАМЯТЬ_ИСПРАВЛЕНИЯ.md) - Memory issue fixes

---

**Status**: 📋 Awaiting approval
**Next review**: After team discussion
**Decision deadline**: 2025-11-28
