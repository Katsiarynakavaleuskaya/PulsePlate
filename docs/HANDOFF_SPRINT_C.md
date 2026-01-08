# 🧾 PulsePlate — CONTEXT HANDOFF (после PR-492, старт Sprint C)

**Дата:** 8 января 2026 (America/New_York)  
**Статус:** Backend стабилен, контракт BMI visualization закреплён docs+tests, начинаем подтягивать iOS/i18n  
**Фаза:** Cleanups + contract → i18n → iOS/Web bootstrap

---

## ✅ Что завершено

### 🔹 PR-490B — BMI Visualization (Group-Aware) ✅ Merged

**Что сделано:**
- Визуализация BMI с учётом групп: `adult` / `athlete` / `elderly`
- Границы **group-aware** (разные пороги по группам)
- Поле `visualization` **опционально**
- Graceful fallback: **`200 OK` + `"visualization": null`** если билдер падает

**Файлы:**
- `core/bmi/engine.py` — централизованные пороги (`_BMI_BREAKPOINTS`)
- `app/services/bmi_visualization.py` — builder использует core thresholds
- `app/routers/bmi.py` — endpoint возвращает visualization spec

**Статус:** ✅ Merged в main

---

### 🔹 PR-491 — Реорганизация тестов ✅ Merged

**Что сделано:**
- Перенос helper-тестов в корректные места (`test_bmi_engine_helpers.py`)
- **Prod-код не менялся**
- Упростили будущие PR и поддержку тестов

**Статус:** ✅ Merged в main

---

### 🔹 PR-487 — Security (urllib3) ✅ Merged

**Что сделано:**
- CVE закрыта после merge
- Code scanning alert исчез
- Тему urllib3 **закрыли**

**Статус:** ✅ Merged в main

---

### 🔹 PR-492 — BMI Visualization Contract (Docs + Tests) ✅ PUSH DONE

**Branch:** `docs/pr-492-bmi-visualization-contract`

**Содержимое:**

1. **`docs/bmi/visualization.md`**
   - Контракт `visualization` field
   - JSON-примеры (adult / athlete / elderly / null)
   - Правила `null` для child/teen/pregnant
   - Описан fallback behavior

2. **`tests/test_bmi_contract_visualization.py`**
   - 7 контрактных тестов
   - Float-safe (`pytest.approx`)
   - Group-aware ranges validation
   - Graceful fallback validation

**Важно:**
- ❌ **Нет изменений production-кода**
- ✅ Тесты проходят (7/7)
- ✅ Ruff/форматирование ок

**Статус:** PR открыт / готов к merge (**Squash and merge**)

**PR URL:** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/new/docs/pr-492-bmi-visualization-contract

---

## 🧱 Канонический контракт BMI (Source of Truth для iOS/Web)

### Endpoint

`POST /api/v1/bmi/calculate`

### Response Field

```json
{
  "visualization": "BMIScaleV1Spec | null"
}
```

### Когда `visualization = null`

Для групп:
- `too_young` (age < 12)
- `child` (age == 12)
- `teen` (age 13-19)
- `pregnant` (any age, if `pregnant=True`)

### Когда `visualization` присутствует

**Структура:**
```json
{
  "kind": "bmi_scale_v1",
  "bmi": 23.4,
  "min": 0.0,
  "max": 60.0,
  "ranges": [
    {"key": "bmi.underweight", "from": 0.0, "to": 18.5},
    {"key": "bmi.normal", "from": 18.5, "to": 25.0},
    {"key": "bmi.overweight", "from": 25.0, "to": 30.0},
    {"key": "bmi.obesity", "from": 30.0, "to": 60.0}
  ],
  "marker": {"value": 23.4}
}
```

**i18n ключи (только эти 4):**
- `bmi.underweight`
- `bmi.normal`
- `bmi.overweight`
- `bmi.obesity`

**Group-aware границы:**
- **Adult:** normal 18.5 → 25.0
- **Athlete:** normal 18.5 → 27.0
- **Elderly:** underweight 0 → 17.5, normal 17.5 → 26.0

**Fallback:**
- Если билдер упал → **`200 OK` и `visualization: null`** (не ломаем клиента)

**Документация:** `docs/bmi/visualization.md`

---

## 🚀 Sprint C.1 — i18n (BMI Visualization Keys) — READY

### Цель

Дать iOS/Web локализованные подписи для диапазонов BMI (ключи уже стабильны из PR-492).

### Ключи (из API)

Из `core/bmi/engine.py` → `get_bmi_visual_ranges()`:
- `bmi.underweight`
- `bmi.normal`
- `bmi.overweight`
- `bmi.obesity`

### Файлы (iOS)

- `ios/PulsePlate/en.lproj/Localizable.strings`
- `ios/PulsePlate/ru.lproj/Localizable.strings`
- `ios/PulsePlate/es.lproj/Localizable.strings`

### Переводы (согласованы с `core/i18n.py`)

**EN:**
- `"bmi.underweight" = "Underweight"`
- `"bmi.normal" = "Normal"`
- `"bmi.overweight" = "Overweight"`
- `"bmi.obesity" = "Obesity"`

**RU:**
- `"bmi.underweight" = "Недостаточная масса"` (совпадает с `core/i18n.py:13`)
- `"bmi.normal" = "Норма"` (совпадает с `core/i18n.py:14`)
- `"bmi.overweight" = "Избыточная масса"` (совпадает с `core/i18n.py:15`)
- `"bmi.obesity" = "Ожирение"` (общий термин, obesity_1/2/3 агрегируются)

**ES:**
- `"bmi.underweight" = "Bajo peso"`
- `"bmi.normal" = "Normal"`
- `"bmi.overweight" = "Sobrepeso"`
- `"bmi.obesity" = "Obesidad"`

### Ветка

```bash
feat/pr-c1-i18n-bmi-keys
```

### Коммит

```bash
feat(i18n): add BMI visualization range keys (RU/EN/ES)
```

### Scope

📌 **Мини-PR:** только iOS, без backend refactoring.

**Не делаем:**
- ❌ Backend i18n registry refactoring (отдельный PR)
- ❌ Изменения в `core/i18n.py`
- ❌ Другие i18n ключи (только 4 BMI range keys)

---

## 🔜 Что дальше (план спринтов)

### 🟡 Sprint C.2 — iOS BMI Bootstrap

**Цель:** Первый экран BMI в iOS приложении.

**Задачи:**
1. **Models:**
   - `BMICalculateRequest.swift`
   - `BMICalculateResponse.swift`
   - `BMIScaleV1Spec.swift`

2. **Service:**
   - `BMIService.swift` (API client для `/api/v1/bmi/calculate`)

3. **Screen:**
   - `BMICalculateScreen.swift` (базовый UI)

4. **Visualization Component:**
   - SwiftUI компонент для рендера scale + marker
   - Использование i18n ключей из Sprint C.1

**Без:**
- ❌ PRO/VIP логики (thin client)
- ❌ Сложной UI (базовый экран)

**Ветка:** `feat/pr-c2-ios-bmi-bootstrap`

---

### 🟡 Sprint C.3 — Web Thin Client (опционально)

**Цель:** Минимальный web-рендер контракта.

**Задачи:**
- QA-tool / demo
- Паритет iOS/Web по контракту

**Приоритет:** Низкий (можно отложить)

---

### 🟢 Sprint D — Backend i18n Alignment (критично)

**Цель:** Выровнять backend i18n с контрактом visualization.

**Проблемы:**
1. **Key mismatch:** Контракт использует `bmi.underweight` (точки), backend — `bmi_underweight` (подчёркивания)
2. **normalize_lang:** `ru`/`es` мапятся на `en`, конфликтует с продуктовой целью

**Задачи:**
1. Добавить dot-keys в `TRANSLATIONS` (backward compatible)
2. Исправить `normalize_lang`: `ru-RU` → `ru`, `es-ES` → `es`
3. Тесты на новые ключи и normalize_lang

**Приоритет:** После C.1/C.2 (отдельный PR, не блокируем iOS bootstrap)

**Документ:** `docs/pr/SPRINT_D_I18N_ALIGNMENT_PLAN.md`

---

## 🧠 Архитектурные инварианты (не ломать)

### One BMI Engine

- Вся математика только в `core/bmi/*`
- `app/`, iOS, Web = адаптеры/рендеры

### API Contract

- API возвращает **данные**, не UI
- `visualization` = контракт (данные), не "UI-логика"
- iOS/Web = **thin clients**

### PR Hygiene

- Маленькие PR; не смешиваем:
  - ❌ deps с фичами
  - ❌ docs/tests с prod-кодом
- Перед каждым PR:
  - **plan → audit → implementation → CI green → merge**
  - Коммиты атомарные, без "свалки"

### Test Coverage

- CI требует >=97% coverage
- Diff-cover проверяет изменённые строки
- Contract tests защищают API от регрессий

---

## ⚠️ Известные проблемы (Sprint D)

### A) Несовпадение ключей i18n

**Проблема:**
- Контракт visualization использует: `bmi.underweight`, `bmi.normal`, `bmi.overweight`, `bmi.obesity` (точки)
- Backend i18n (`core/i18n.py`) использует: `bmi_underweight`, `bmi_normal`, `bmi_overweight`, `bmi_obese_1/2/3` (подчёркивания)

**Impact:** iOS/Web получат `ranges[].key = "bmi.underweight"` и не найдут перевод в `TRANSLATIONS`.

**Решение:** Sprint D — добавить dot-keys в backend i18n (backward compatible, старые ключи оставляем).

**Документ:** `docs/pr/SPRINT_D_I18N_ALIGNMENT_PLAN.md`

### B) normalize_lang конфликтует с продуктовой целью

**Проблема:**
- Сейчас: `ru` → `en` (default), `es` → `en` (except MX)
- Продуктовая цель: RU/ES/EN локализация для iOS

**Impact:** iOS строки будут "мертвы", если backend всегда возвращает EN.

**Решение:** Sprint D — исправить `normalize_lang`: `ru-RU` → `ru`, `es-ES` → `es`.

**Документ:** `docs/pr/SPRINT_D_I18N_ALIGNMENT_PLAN.md`

### ⏰ Когда исправлять

**НЕ сейчас:**
- ❌ Sprint C.1 (iOS-only ключи) — не трогаем backend
- ❌ Sprint C.2 (iOS bootstrap) — не блокируем

**ПОСЛЕ C.1/C.2:**
- ✅ Sprint D — отдельный PR для backend i18n alignment

---

## 🧩 Итоговое состояние проекта

### Backend

- ✅ Стабилен
- ✅ BMI visualization group-aware
- ✅ Контракты закреплены тестами и доками
- ✅ Security чисто

### Documentation

- ✅ `docs/bmi/visualization.md` — контракт BMI visualization
- ✅ Contract tests — защита от регрессий

### Next Steps

1. **Sprint C.1:** i18n keys для BMI (iOS)
2. **Sprint C.2:** iOS BMI bootstrap (экран + API client)
3. **Sprint C.3:** Web thin client (опционально)
4. **Sprint D:** i18n audit (отдельный PR)

---

## ▶️ Старт нового диалога

**Фокус нового окна:**

> **Sprint C.1 → Sprint C.2 (iOS BMI)**

**В новом диалоге:**

- Быстро закрываем i18n PR (C.1)
- Затем пошагово собираем iOS BMI экран по контракту (C.2)
- Без спешки, но сразу "по-продуктовому"

---

## 📋 PR Templates (Copy-Paste Ready)

### PR-C1 Template

```markdown
## Summary

Add BMI visualization i18n keys to iOS localization files.

**Type:** i18n (iOS only)  
**Minimal scope:** Only 4 keys, no backend refactoring.

---

## What Changed

### Added

- BMI visualization keys to iOS `Localizable.strings`:
  - `bmi.underweight` (RU/EN/ES)
  - `bmi.normal` (RU/EN/ES)
  - `bmi.overweight` (RU/EN/ES)
  - `bmi.obesity` (RU/EN/ES)

### Changed

- `ios/PulsePlate/en.lproj/Localizable.strings`
- `ios/PulsePlate/ru.lproj/Localizable.strings`
- `ios/PulsePlate/es.lproj/Localizable.strings`

---

## Why This Change

1. **iOS needs localized labels** for BMI visualization ranges
2. **Keys match API contract** (from PR-492 documentation)
3. **Minimal scope** (only keys, no refactoring)

---

## Keys Added

| Key | EN | RU | ES |
|-----|----|----|----|
| `bmi.underweight` | Underweight | Недостаточная масса | Bajo peso |
| `bmi.normal` | Normal | Норма | Normal |
| `bmi.overweight` | Overweight | Избыточная масса | Sobrepeso |
| `bmi.obesity` | Obesity | Ожирение | Obesidad |

---

## Related

- Follow-up to PR-492 (BMI visualization contract)
- Enables Sprint C.2 (iOS BMI bootstrap)
```

### PR-C2 Template (Placeholder)

```markdown
## Summary

Bootstrap iOS BMI screen with API client and visualization component.

**Type:** Feature (iOS)  
**Scope:** Thin client, no backend changes.

---

## What Changed

### Added

- BMI models (BMICalculateRequest, BMICalculateResponse, BMIScaleV1Spec)
- BMIService (API client)
- BMICalculateScreen (basic UI)
- BMI visualization component (SwiftUI)

### Changed

- None (new files only)

---

## Why This Change

1. **iOS needs BMI feature** to match backend capabilities
2. **Uses documented contract** (from PR-492)
3. **Uses i18n keys** (from PR-C1)

---

## Related

- Follow-up to PR-492 (BMI visualization contract)
- Follow-up to PR-C1 (i18n keys)
```

---

## 🔗 Key Documents

- `docs/bmi/visualization.md` — BMI visualization contract
- `docs/pr/PR_492_PLAN.md` — PR-492 implementation plan
- `docs/pr/PR_C1_I18N_KEYS_READY.md` — Ready-to-use i18n strings
- `docs/audit/PROJECT_AUDIT_2026_Q1.md` — Full project audit
- `docs/roadmap/SPRINT_ROADMAP_2026_Q1.md` — Sprint roadmap

---

**Ready for Sprint C!** 🚀

