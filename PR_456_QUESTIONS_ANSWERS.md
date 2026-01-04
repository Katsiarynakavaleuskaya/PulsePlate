# PR-456 — Questions & Answers (Audit Results)

**Цель PR-456:** убрать остатки доменной логики/дублирования из `app/*` и `legacy_app.py`, оставить **тонкий прокси** к `core/bmi/engine.py`, при этом **ничего не сломать** в API, i18n и тестах.

**GitHub PR:** (будет создан после PR-455 merge)

---

## 1) Scope Guard

### Вопросы

**Q: Какие эндпоинты/роуты входят в PR-456?**

**A:** 
- ✅ `/api/v1/bmi/calculate` — уже shim (PR-454), но нужно проверить, что нет остатков логики
- 🔄 `/api/v1/bmi` — **legacy endpoint** (`bmi_endpoint_v1` в `legacy_app.py:2139`), использует `bmi_core` напрямую
- 🔄 `/bmi` — **legacy endpoint** (если существует, нужно найти)

**Q: Есть ли "внутренние" legacy endpoints, которые продолжают дергать `bmi_core` напрямую?**

**A:** 
- ✅ **ДА**: `legacy_app.py:2139` (`bmi_endpoint_v1`) использует `bmi_core.bmi_category` (строка 67)
- ✅ **ДА**: `legacy_app.py:1547` (`calc_bmi`) — локальная функция, дублирует `core/bmi/engine._compute_bmi`
- ⚠️ **ПОТЕНЦИАЛЬНО**: `legacy_app.py:2099` содержит `healthy_bmi = {"min": 18.5, "max": 24.9}` — порог в legacy

### Риски

- ✅ **Scope creep**: PR-456 должен быть **только про Free BMI** (`/api/v1/bmi/calculate` и `/api/v1/bmi`). PRO endpoints (`/api/v1/bmi/pro`) — отдельно.
- ✅ **Контракты**: Не менять DTO/ошибки без явной необходимости.

---

## 2) Где ещё живёт BMI-логика вне `core/bmi/*` (карта зачистки)

### Вопросы

**Q: Какие файлы содержат BMI thresholds/WHtR/auto_group/normalize?**

**A:**

#### BMI Thresholds:
- ❌ `legacy_app.py:2099`: `healthy_bmi = {"min": 18.5, "max": 24.9}` — **удалить или заменить на engine**
- ✅ `bmi_visualization.py` — в whitelist (visualization only)
- ✅ `app/routers/bmi_pro.py` — в whitelist (PRO endpoint, отдельно)

#### WHtR вычисления:
- ❌ `app/routers/bmi_pro.py:50`: `v_whtr = wht_ratio(req.waist_cm, req.height_cm)` — PRO endpoint, не трогаем в PR-456
- ✅ `core/bmi/risk.py` — каноническое место ✅

#### auto_group logic:
- ❌ `legacy_app.py:2139-2192` (`bmi_endpoint_v1`): использует `bmi_core.auto_group` — **заменить на engine**
- ✅ `core/bmi/engine.py` — каноническое место ✅

#### normalize_gender/lang/bool:
- ✅ `app/routers/bmi.py:67-83` (`_get_lang_from_request`): **дублирует** `core.i18n.normalize_lang` — **удалить, использовать engine**
- ✅ `app/routers/bmi.py:48-64` (`_normalize_bool_flag`): уже импортируется из engine (PR-455) ✅
- ❌ `legacy_app.py:2180-2187`: локальная логика `is_athlete` — **дублирует** `_normalize_bool_flag` — **заменить на engine**

### Риски

- ⚠️ **Скрытая логика**: `legacy_app.py:2180-2187` содержит `if athlete.lower() in {"спортсмен", "да", "yes", "y", "athlete"}` — это дубликат нормализации
- ⚠️ **Guard false positives**: docstrings/комментарии могут триггерить guard, но уже настроены исключения

---

## 3) Router responsibilities (канон)

### Вопросы

**Q: Что *точно* остается в router?**

**A:**
- ✅ **Request parsing/validation**: Pydantic делает автоматически, router только передаёт
- ❌ **normalize bool/lang**: `_get_lang_from_request` — **дублирует** `core.i18n.normalize_lang` → **удалить, использовать engine**
- ✅ **Mapping исключений → error envelope + i18n**: остаётся (это адаптер-слой)

**Q: Что *точно* уходит в engine?**

**A:**
- ✅ Всё доменное: группировка/категории/интерпретация/waist risk — уже в engine ✅

### Риски

- ⚠️ **Импорт приватных функций**: `from core.bmi.engine import _normalize_bool_flag` — временно OK, но TODO(PR-456) уже есть
- ✅ **Решение**: Либо сделать публичные `core/bmi/normalize.py`, либо оставить до следующего PR, но **зафиксировать в документации**

---

## 4) Error handling & i18n (самое опасное место)

### Вопросы

**Q: Какие ошибки выбрасывает engine?**

**A:**
- `ValueError("weight_kg must be positive")`
- `ValueError("height_cm must be positive")`
- `ValueError("age must be between 1 and 120")`
- `ValueError("BMI out of valid range (10-100)")`
- `NotImplementedError` (если engine stub, но уже реализован)

**Q: Какие i18n ключи использует router?**

**A:**
- `t(lang, "bmi_engine_unavailable")` — 501
- `t(lang, "bmi_invalid_parameters")` — 400
- `t(lang, "bmi_calculation_failed")` — 500

**Q: Есть ли отличия в error envelope между legacy и новым?**

**A:**
- ✅ **Новый**: FastAPI HTTPException → `{"detail": "..."}`
- ⚠️ **Legacy**: Нужно проверить, есть ли обёртка (скорее всего тоже FastAPI)

### Риски

- ✅ **Двойная локализация**: Нет — engine не локализует, только router
- ✅ **Утечки `str(e)`**: Нет — в router используется `t(lang, key)`, не `str(e)`
- ⚠️ **HTTP status codes**: Legacy может использовать другие коды — нужно проверить parity

**Правило:**
- ✅ Engine: короткие `ValueError("...")` (без i18n) — **соблюдается**
- ✅ Router: переводит в user-facing i18n + envelope, без утечек — **соблюдается**

---

## 5) Backward compatibility: поля ответа

### Вопросы

**Q: Какие поля ответа обязаны быть всегда?**

**A:**
- ✅ `category`: `None` для `too_young/child/teen/pregnant` (канон) — **уже реализовано в engine**
- ✅ `waist_risk`: `None` если `waist_cm` не предоставлен — **уже реализовано**
- ✅ `notes`: `tuple[str, ...]` (может быть пустым) — **уже реализовано**
- ✅ `interpretation`: всегда строка (может быть пустой) — **уже реализовано**

**Q: Есть ли клиенты, которые полагаются на старое поведение?**

**A:**
- ⚠️ **Неизвестно** — нужно проверить iOS/web клиенты, но по логике shim должен сохранять контракт

### Риски

- ⚠️ **Тихое изменение**: `group_display` — сейчас таблица в engine, но может измениться на i18n в будущем
- ✅ **Решение**: Golden parity tests зафиксируют поведение

---

## 6) Legacy cleanup strategy

### Вопросы

**Q: Что делаем с `legacy_app.py`?**

**A:**
- ✅ `/api/v1/bmi/calculate` — уже shim (PR-454) ✅
- 🔄 `/api/v1/bmi` (`bmi_endpoint_v1`) — **превратить в shim** (вызывать `bmi_calculate_handler`)
- ❓ `/bmi` — проверить, существует ли, если да — тоже shim

**Q: Есть ли import cycles?**

**A:**
- ✅ **Нет**: `legacy_app.py` использует `from app.routers.bmi import bmi_calculate_handler` (локальный импорт) — безопасно
- ✅ **Нет**: `app/routers/bmi.py` импортирует из `core/bmi/engine` — безопасно

### Риски

- ✅ **Import cycles**: Нет риска — локальные импорты в legacy
- ⚠️ **Удаление кода**: `legacy_app.py:1547` (`calc_bmi`) — проверить, используется ли где-то ещё

---

## 7) Tests impact (минимум для зелёного PR)

### Вопросы

**Q: Какие тесты завязаны на legacy behavior?**

**A:**
- ✅ `tests/test_bmi_endpoint_diff_coverage.py:67-79`: проверяет `_get_lang_from_request` — **нужно обновить** (удалить тест или заменить на engine)
- ✅ `tests/test_bmi_endpoint_diff_coverage.py:41-50`: проверяет `_normalize_bool_flag` — **уже обновлено** (использует engine)
- ✅ `tests/test_app_bmi_v1.py`: проверяет `/api/v1/bmi` endpoint — **нужно обновить** (ожидать shim behavior)
- ⚠️ `tests/test_bmi_calculate_endpoint.py`: проверяет `/api/v1/bmi/calculate` — **уже обновлено** (shim работает)

**Q: Где нужно заменить проверки "legacy logic" на "engine result"?**

**A:**
- ❌ `tests/test_bmi_endpoint_diff_coverage.py:56-66` — тест `_get_lang_from_request` → **удалить** (функция будет удалена)
- ❌ `tests/test_app_bmi_v1.py` — обновить ожидания (shim должен возвращать engine result)

### Риски

- ⚠️ **Хрупкие тесты**: Тесты на точные строки ошибок могут сломаться, если изменится i18n
- ✅ **Решение**: Использовать i18n ключи, а не точные строки

---

## 8) Guard-test false positives

### Вопросы

**Q: Whitelist уже расширен — всё ли там действительно временно?**

**A:**
- ✅ `bmi_visualization.py` — **временно** (PR-456 cleanup)
- ✅ `app/routers/bmi_pro.py` — **временно** (PRO endpoint, отдельный PR)
- ✅ `core/nutrition_bayesian_analyzer.py` — **постоянно** (использует BMI для контекста, не core logic)
- ✅ `legacy_app.py` — **временно** (до PR-456 cleanup)

**Q: Есть ли ещё папки типа `.tox`, `.mypy_cache`?**

**A:**
- ✅ `.venv/`, `.venv-ci/` — уже в whitelist ✅
- ⚠️ `.tox/`, `.mypy_cache/`, `__pycache__/` — **добавить в whitelist** (build artifacts)

### Риски

- ⚠️ **Guard начнет падать на мусоре**: Если структура окружения изменится, guard может поймать артефакты
- ✅ **Решение**: Расширить whitelist для build artifacts

---

## 9) Security / Compliance

### Вопросы

**Q: Нет ли новых мест, где exception detail утекает в response?**

**A:**
- ✅ **Нет**: Router использует `t(lang, key)`, не `str(e)` ✅
- ✅ **Нет**: Engine выбрасывает короткие `ValueError`, не детальные сообщения ✅

**Q: Логи: не пишем PII (weight/waist) в error logs?**

**A:**
- ⚠️ **Проверить**: `legacy_app.py:2178-2191` содержит логирование `group_category` и `athlete` — **OK** (не PII)
- ✅ **Решение**: Убедиться, что в router нет логирования PII

### Риски

- ✅ **Regression**: Нет риска — текущая реализация безопасна
- ⚠️ **Непреднамеренное логирование**: Проверить, что router не логирует входные параметры

---

## 10) Definition of Done для PR-456

### Должно быть

- ✅ Router BMI = **тонкий**, без доменной логики и без дублирующих helper'ов
- ✅ Legacy BMI paths = shim/proxy или не используются
- ✅ Golden parity + guard остаются зелёными
- ✅ CI зелёный, coverage ≥ порога
- ✅ Документация: короткий PR-456 handoff (что удалили/что стало источником истины)

---

## Мини "проблемы, которые почти наверняка всплывут"

1. ✅ **Отличия в текстах ошибок (i18n ключи)** — уже зафиксировано, используется `t(lang, key)`
2. ⚠️ **Где-то остался "маленький if athlete:" в router/legacy** — `legacy_app.py:2180-2187` содержит дубликат
3. ⚠️ **Один endpoint тест проверяет старое поведение legacy** — `tests/test_app_bmi_v1.py` нужно обновить
4. ✅ **Guard внезапно поймает пороги в неожиданном файле** — уже настроены исключения

---

## Рекомендации для PR-456

### Приоритет 1 (обязательно)
1. Удалить `_get_lang_from_request` из router, использовать `core.i18n.normalize_lang`
2. Превратить `legacy_app.py:bmi_endpoint_v1` в shim
3. Удалить дубликат `is_athlete` логики из `legacy_app.py:2180-2187`
4. Обновить тесты (`test_bmi_endpoint_diff_coverage.py`, `test_app_bmi_v1.py`)

### Приоритет 2 (желательно)
5. Удалить `legacy_app.py:1547` (`calc_bmi`) если не используется
6. Удалить `legacy_app.py:2099` (`healthy_bmi` threshold) если не используется
7. Расширить whitelist guard для build artifacts (`.tox/`, `.mypy_cache/`)

### Приоритет 3 (опционально)
8. Создать публичный `core/bmi/normalize.py` для нормализации (убрать `_` префиксы)
9. Документировать расхождения legacy vs engine (если есть)

---

## Next Steps

1. Создать **PR-456 Cursor TODO Checklist** (6 атомарных коммитов)
2. Начать с Commit 1: удаление `_get_lang_from_request` из router
3. Commit 2: превращение `bmi_endpoint_v1` в shim
4. Commit 3: удаление дубликатов из legacy
5. Commit 4: обновление тестов
6. Commit 5: cleanup (удаление неиспользуемого кода)
7. Commit 6: документация

