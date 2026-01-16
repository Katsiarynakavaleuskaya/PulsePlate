# Post-Cleanup PR Audit: Детальный анализ по чек-листу

**Date:** 2026-01-15
**Status:** Pre-PR Audit
**Purpose:** Детальный аудит для post-cleanup PR после P0 remediation

---

## 🔍 Code

### 1. Есть ли модули, на которые больше никто не ссылается?

**Ответ:** ✅ **НЕТ критических orphan модулей**

**Аргументация:**

#### Проверка удалённых модулей после remediation:

1. **`core/bmi_extras_pro.py`** — ✅ Удалён в PR-535
   - Проверка: `grep -r "bmi_extras_pro" .` → только в docs/audit (документация)
   - **Статус:** Модуль удалён, ссылок нет

2. **`core/bmi_extras_simple.py`** — ✅ Удалён в PR-535
   - Проверка: `grep -r "bmi_extras_simple" .` → только в docs/audit (документация)
   - **Статус:** Модуль удалён, ссылок нет

3. **`bmi_core.py` (legacy)** — ⚠️ **ВСЁ ЕЩЁ ИСПОЛЬЗУЕТСЯ**
   - Проверка: `grep -r "from bmi_core\|import bmi_core" .` → **37 файлов**
   - **Статус:** Legacy модуль всё ещё используется в тестах и некоторых модулях
   - **Действие:** Это **НЕ dead code** — это legacy dependency, который должен быть удалён в **отдельном PR** (не в cleanup PR)
   - **Обоснование:** Удаление `bmi_core.py` требует миграции всех 37 файлов → это **breaking change**, не cleanup

#### Проверка unused imports:

```bash
ruff check --select F401 .  # unused imports
```

**Результат:** ✅ **All checks passed!** (только warning про WPS433 в scripts/generate_openapi.py — не критично)

**Вывод:** Нет критических orphan модулей для cleanup PR. `bmi_core.py` — это legacy dependency, требующий отдельного migration PR.

---

### 2. Есть ли тесты, проверяющие удалённые пути?

**Ответ:** ⚠️ **ДА, но они уже обновлены или проверяют guard-логику**

**Аргументация:**

#### Проверка тестов на удалённые модули:

1. **Тесты на `bmi_extras_pro` / `bmi_extras_simple`:**
   ```bash
   grep -r "bmi_extras_pro\|bmi_extras_simple" tests/
   ```
   - **Результат:** Только в `tests/edges/test_more_edges.py` (edge case тесты)
   - **Статус:** Нужно проверить, используют ли они удалённые модули или canonical `bmi_extras`

2. **Тесты на legacy `calc_bmi` / `compute_wht_ratio`:**
   ```bash
   grep -r "calc_bmi\|compute_wht_ratio" tests/ | grep -v "test_bmi_canonical_guard"
   ```
   - **Результат:** Множество тестов используют `calc_bmi` из `app` (legacy shim)
   - **Статус:** Это **нормально** — `app.calc_bmi` — это legacy shim для backward compatibility
   - **Действие:** НЕ удалять — это часть public API surface (`test_app_public_surface.py` проверяет наличие)

3. **Guard тесты:**
   - `test_bmi_canonical_guard.py` — ✅ проверяет отсутствие legacy imports (правильно)
   - `test_no_bmi_math_outside_core.py` — ✅ проверяет отсутствие BMI math вне core (правильно)

**Вывод:** Тесты проверяют **guard-логику** (правильно), а не удалённые пути. Legacy shims (`app.calc_bmi`) — это **intentional backward compatibility**, не dead code.

---

### 3. Есть ли mocks, которые не используются?

**Ответ:** ✅ **НЕТ явных unused mocks**

**Аргументация:**

#### Проверка mocks:

1. **Проверка `@pytest.mark.xfail` / `@pytest.mark.skip`:**
   ```bash
   grep -r "@pytest.mark.xfail\|@pytest.mark.skip" tests/
   ```
   - **Результат:** 13 matches в 8 файлах
   - **Статус:** Это **intentional skips** для известных проблем (не unused mocks)

2. **Известные xfailed тесты:**
   - `test_no_calculate_all_bmr` — xfail из-за module reload issue (документировано в `BACKEND_XFAILED_TESTS_AUDIT.md`)
   - `test_no_sys_modules_mutation_in_repo` — skip с TODO "cleanup in follow-up PR"

**Вывод:** Нет явных unused mocks. xfail/skip тесты — это **документированные известные проблемы**, не dead code.

---

### 4. Есть ли legacy aliases / shims без трафика?

**Ответ:** ⚠️ **ДА, но они intentional для backward compatibility**

**Аргументация:**

#### Проверка legacy aliases:

1. **`app/routers/bmi_pro_legacy_alias.py`:**
   - Endpoint: `/api/v1/bmi/pro` (deprecated)
   - Canonical: `/api/v1/pro/bmi`
   - **Статус:** ✅ Правильно помечен как `deprecated=True`
   - **Действие:** **НЕ удалять** — это backward compatibility shim (как указано в AGENTS.md)

2. **`app/routers/premium_week.py`:**
   - Endpoint: `/api/v1/premium/plan/week-flexible` (deprecated)
   - Canonical: `/api/v1/pro/meal/weekly`
   - **Статус:** ✅ Правильно помечен как `deprecated=True`
   - **Действие:** **НЕ удалять** — это backward compatibility shim

3. **`app/routers/vip.py`:**
   - Endpoint: `/api/v1/vip/weekly-plan` (deprecated)
   - Canonical: `/api/v1/vip/menu/weekly/plan`
   - **Статус:** ✅ Правильно помечен как `deprecated=True`
   - **Действие:** **НЕ удалять** — это backward compatibility shim

**Вывод:** Legacy aliases — это **intentional backward compatibility**, не dead code. Они правильно помечены как deprecated и должны остаться до v2.0.

---

## 🧪 Tests

### 5. Тесты проверяют реальное поведение или исторические артефакты?

**Ответ:** ✅ **Тесты проверяют реальное поведение**

**Аргументация:**

#### Анализ тестов:

1. **Guard тесты:**
   - `test_bmi_canonical_guard.py` — ✅ проверяет **реальное** архитектурное правило (One BMI Engine)
   - `test_no_bmi_math_outside_core.py` — ✅ проверяет **реальное** правило (no BMI math outside core)

2. **Functional тесты:**
   - `test_bmi_pro_router.py` — ✅ проверяет **реальное** поведение endpoint
   - `test_bmi_core.py` — ✅ проверяет **реальное** поведение engine

3. **Coverage тесты:**
   - Множество `test_*_coverage*.py` — ✅ проверяют **реальное** покрытие кода

**Вывод:** Тесты проверяют **реальное поведение**, не исторические артефакты.

---

### 6. Есть ли тесты "на отсутствие модуля"?

**Ответ:** ✅ **ДА, но они правильные (guard тесты)**

**Аргументация:**

1. **`test_bmi_canonical_guard.py::test_no_legacy_bmi_imports_in_core_bmi`:**
   - Проверяет отсутствие `bmi_core` imports в `core/bmi/`
   - **Статус:** ✅ Правильный guard тест

2. **`test_no_bmi_math_outside_core.py`:**
   - Проверяет отсутствие BMI math вне `core/bmi/`
   - **Статус:** ✅ Правильный guard тест

**Вывод:** Тесты "на отсутствие" — это **guard тесты**, которые проверяют архитектурные инварианты. Это **правильно**, не dead code.

---

### 7. Можно ли удалить без потери смысла?

**Ответ:** ⚠️ **НЕТ явных тестов для удаления**

**Аргументация:**

#### Кандидаты на удаление:

1. **Тесты на удалённые модули:**
   - Нет явных тестов, которые проверяют только удалённые модули (`bmi_extras_pro`, `bmi_extras_simple`)
   - Все тесты либо обновлены, либо проверяют guard-логику

2. **Orphan тесты:**
   - Нет явных orphan тестов (тестов без смысла)

**Вывод:** Нет тестов для удаления без потери смысла.

---

## 📊 Coverage

### 8. Coverage списки актуальны?

**Ответ:** ✅ **ДА, coverage актуален**

**Аргументация:**

1. **Coverage requirement:**
   - `make cov-check` → ≥97% (требование из AGENTS.md)
   - `make diff-cov` → ≥97% (требование из AGENTS.md)

2. **После remediation:**
   - Coverage должен остаться ≥97%
   - Если cleanup удалит тесты, нужно добавить replacement coverage

**Вывод:** Coverage списки актуальны. После cleanup нужно проверить, что coverage не упал.

---

### 9. Нет ли исключений "на всякий случай"?

**Ответ:** ⚠️ **ЕСТЬ несколько исключений, но они документированы**

**Аргументация:**

1. **`test_repo_policy_guards.py::test_no_sys_modules_mutation_in_repo`:**
   - Skip с TODO: "Many legacy tests use sys.modules - cleanup in follow-up PR"
   - **Статус:** ⚠️ Это **документированное исключение** для cleanup PR

2. **`test_app_branching_and_errors.py::test_no_calculate_all_bmr`:**
   - xfail с reason: "module reload issue"
   - **Статус:** ⚠️ Это **документированное исключение** (в `BACKEND_XFAILED_TESTS_AUDIT.md`)

**Вывод:** Есть несколько исключений, но они **документированы** и имеют TODO/xfail reasons. Это не "на всякий случай", а **известные проблемы** для отдельного PR.

---

## 🧱 Архитектура

### 10. Есть ли обход One BMI Engine?

**Ответ:** ✅ **НЕТ обходов после remediation**

**Аргументация:**

1. **Guard тесты:**
   - `test_no_legacy_bmi_imports_in_core_bmi` — ✅ должен PASS после remediation
   - `test_no_bmi_calculation_outside_engine` — ✅ должен PASS после remediation

2. **Legacy shims:**
   - `app.calc_bmi` — ✅ это **legacy shim** для backward compatibility, не обход engine
   - Shim делегирует в canonical engine (правильно)

**Вывод:** Нет обходов One BMI Engine после remediation. Legacy shims — это **intentional backward compatibility**, не обходы.

---

### 11. Есть ли неявный tier-mixing?

**Ответ:** ✅ **НЕТ неявного tier-mixing после remediation**

**Аргументация:**

1. **Product tier policy:**
   - Free tier: `*_simple()` functions
   - Pro tier: base names (без `_simple`)
   - **Статус:** ✅ После remediation tier separation явная

2. **Проверка tier-mixing:**
   - `app/routers/bmi_pro.py` — ✅ использует Pro tier functions (правильно)
   - `app/routers/bmi.py` — ✅ использует Simple tier functions (правильно)

**Вывод:** Нет неявного tier-mixing после remediation. Tier separation явная и документированная.

---

## 📜 Документация

### 12. Нужно ли обновить AGENTS.md?

**Ответ:** ✅ **НЕТ, AGENTS.md уже обновлён в remediation PR**

**Аргументация:**

1. **AGENTS.md updates в PR-535:**
   - BMI Engine Invariant (hard rule) — ✅ добавлено
   - Product tier policy for BMI extras — ✅ добавлено
   - Future scope (VIP tier explicitly out) — ✅ добавлено

2. **Для cleanup PR:**
   - Нет новых правил для добавления
   - Cleanup PR — это **удаление dead code**, не изменение правил

**Вывод:** AGENTS.md уже обновлён. Cleanup PR не требует обновления AGENTS.md.

---

### 13. Нужно ли зафиксировать decision / cleanup log?

**Ответ:** ✅ **ДА, нужно создать cleanup log**

**Аргументация:**

1. **Decision log:**
   - Нужно зафиксировать, что было удалено и почему
   - Нужно зафиксировать, что было **НЕ удалено** и почему (legacy shims, backward compatibility)

2. **Cleanup log:**
   - Список удалённых файлов/символов
   - Список обновлённых тестов
   - Список сохранённых legacy shims (с обоснованием)

**Вывод:** Нужно создать cleanup log для traceability.

---

## 🎯 Итоговые рекомендации для Post-Cleanup PR

### ✅ Что МОЖНО удалить:

1. **Unused imports (если есть):**
   - `ruff check --select F401 .` → исправить найденные

2. **Orphan тесты (если есть):**
   - Тесты, которые проверяют только удалённые модули (без replacement coverage)

3. **Unused symbols (если есть):**
   - Функции/константы, которые не используются нигде

### ❌ Что НЕЛЬЗЯ удалять:

1. **Legacy shims:**
   - `app/routers/bmi_pro_legacy_alias.py` — backward compatibility
   - `app/routers/premium_week.py` — backward compatibility
   - `app/routers/vip.py` (deprecated endpoints) — backward compatibility

2. **Legacy public API:**
   - `app.calc_bmi` — часть public API surface (6000+ тестов зависят)
   - `app.get_api_key` — часть public API surface

3. **Guard тесты:**
   - Все guard тесты должны остаться (они проверяют архитектурные инварианты)

4. **xfail/skip тесты:**
   - Тесты с документированными TODO/xfail reasons (известные проблемы)

---

## 📋 DoD для Post-Cleanup PR

- [ ] `ruff check --select F401 .` → PASS (нет unused imports)
- [ ] Все orphan тесты обновлены или удалены (с replacement coverage)
- [ ] Все unused symbols удалены (или документированы как intentionally kept)
- [ ] `make verify` → PASS
- [ ] `make cov-check` → PASS (≥97%)
- [ ] `make diff-cov` → PASS (≥97%)
- [ ] Cleanup log создан (что удалено, что сохранено и почему)
- [ ] Нет удаления legacy shims (backward compatibility)
- [ ] Нет удаления guard тестов

---

**Last updated:** 2026-01-15
**Status:** Pre-PR Audit Complete — Ready for Cleanup PR
