# 🧾 PulsePlate — CONTEXT HANDOFF (после merge PR #558)

**Дата фиксации:** 2026-01-19
**Ветка:** `main`
**CI / diff-cover:** ✅ зелёные
**Текущая стадия:** **Post-remediation завершена → разрешён downstream (Web / iOS thin clients)**

---

## 0) Канонические правила проекта (НЕ обсуждаются)

1. **Audit-first**
   Любой PR: аудит → план → реализация → DoD.

2. **One BMI Engine (жёсткий инвариант)**
   ❌ Никакой BMI-математики вне `core/bmi/*`
   ✅ Клиенты и legacy — только через engine / shim.

3. **Downstream только после backend-стабилизации**
   ⛔️ Запрет был до PR-558
   ✅ После PR-558 — **снят**

4. **Coverage gate**
   - CI + diff-cover ≥97% — обязательны
   - Codecov patch coverage — **информативный**, не блокирующий

5. **Legacy = изоляция, не "красота"**
   BC важнее чистоты. Если нужен shim — он допустим.

---

## 1) Что ЗАКРЫТО (фактический статус)

### ✅ PR #555 — Router helpers cleanup

- Дедуп:
  - `_normalize_bool_flag`
  - `_build_soft_paywall_hook`
- Guards усилены
- Поведение RU/EN/ES синхронизировано

---

### ✅ PR #556 — Soft Paywall Contract (docs)

- `docs/contracts/soft_paywall.md` — **канонический контракт**
- Text-only, wellness-позиционирование
- `soft_paywall: null` when disabled
- Без импорта `core.bmi.*`
- AGENTS.md обновлён

---

### ✅ PR #557 — Legal / Compliance Pack (docs)

- Disclaimer / Terms / Privacy — **RU / EN / ES**
- Убраны любые регуляторные утверждения
- Актуализированы AI-провайдеры
- Исправлены RU формулировки

---

### ✅ PR #558 — **Post-Remediation Cleanup (ФАКТИЧЕСКИ ЗАКРЫТ)**

PR-558 оказался шире, чем планировалось — и это правильно.

#### Что реально сделано:

##### 1. Legacy `bmi_core.py`

- ❌ Удалять полностью **нельзя** (ломало BC)
- ✅ Создан **тонкий legacy-shim** `bmi_core.py`:
  - **Без BMI-математики**
  - Делегирует в `core/bmi/*`
  - Сохраняет ABI и позиционный порядок аргументов
  - Восстановлена BC для `auto_group(...)`
  - Исправлен критический баг с `athlete_bool`
  - Типизация `compute_wht_ratio(None, …)` приведена в норму

##### 2. Invariant enforcement

- One BMI Engine сохранён
- Нет хардкода порогов (`18.5 / 25 / 30`) вне core
- Visualization использует **только канонические константы**

##### 3. BMI visualization

- ❌ Удалён `legacy_labels`
- ✅ **Единый i18n-путь**
- Никогда не возвращает raw keys
- Safe fallback при отсутствии переводов
- RU/EN/ES консистентны
- Athlete text BC сохранён (`"спортсмен"`, `"athlete"`)

##### 4. Тесты и CI

- Устранены `ModuleNotFoundError`
- Diff-cover ≥97% (зелёный)
- Codecov patch ≈93% (принято как OK)
- Тесты детерминированы (без "или-или" логики)
- Исправлены логически неверные тесты (`_compute_wht_ratio`)

##### 5. Документация процесса

- AGENTS.md дополнен:
  - политика legacy-shim
  - запрет silent ABI-ломаний
  - coverage expectations

**Вывод:**
👉 **Post-remediation завершена полностью.**
👉 Backend стабилен, контракты зафиксированы, BC сохранён.
👉 **Downstream разрешён.**

---

## 2) Текущий канонический статус проекта

| Область                        | Статус          |
| ------------------------------ | --------------- |
| Backend BMI engine             | ✅ стабилен      |
| Contracts (API / Soft paywall) | ✅ зафиксированы |
| Legal / Compliance             | ✅ закрыто       |
| CI / diff-cover                | ✅ зелёные       |
| Legacy BC                      | ✅ сохранён      |
| Web / iOS                      | ⏳ **в очереди** |

---

## 3) ЧТО ДАЛЬШЕ (будущие PR, по порядку)

### 🚀 Следующий этап: **Downstream migration (thin clients)**

---

### 🔹 PR-559 — **iOS Thin Client (BMI)**

**Цель:**
Подключить iOS как **тонкий клиент**, без BMI-логики.

**Scope:**

- `APIClient.swift`
- POST `/api/v1/bmi/calculate`
- DTO:
  - `BMIRequest`
  - `BMIResponse`
- Error handling (RU/EN/ES)
- Отображение:
  - `category` (строка)
  - `group`
  - `visualization.available`
- ❌ Никакой BMI математики
- ❌ Никаких порогов

**DoD:**

- Компилируется
- Запрос/ответ соответствуют контракту
- UI — read-only интерпретация backend

---

### 🔹 PR-560 — **Web Thin Client (BMI)**

**Цель:**
Веб-клиент = mirror iOS.

**Scope:**

- React/Vite
- Тот же endpoint
- Генерация типов из OpenAPI (если принято)
- UI-i18n ≠ BMI-i18n

---

### 🔹 PR-561 — **Soft Paywall UI integration**

**Цель:**
Подключить уже зафиксированный контракт.

**Scope:**

- Показ текста / CTA
- Никакой бизнес-логики
- Никаких backend изменений

---

### 🔹 PR-562 (опционально, P1) — Codecov cosmetics

*Только если захочется "идеал"*

- Убрать оставшиеся partials
- Не блокирует roadmap

---

## 4) Канонический контракт `/api/v1/bmi/calculate`

### Endpoint

```
POST /api/v1/bmi/calculate
```

**Tier:** FREE (no API key required)

### Request Schema: `BMICalculateRequest`

```python
{
  "weight_kg": float,        # > 0, required
  "height_cm": float,        # > 0, required
  "age": int,                # 1-120, required
  "gender": str | None,      # "male" | "female" | None (normalized by engine)
  "pregnant": str | bool,    # "yes"/"no" | True/False, default: False
  "athlete": str | bool,     # "yes"/"no" | True/False, default: False
  "waist_cm": float | None,  # > 0, optional (enables WHtR)
  "lang": str | None         # "ru" | "en" | "es" | None, default: "en"
}
```

**Пример запроса:**

```json
{
  "weight_kg": 70.0,
  "height_cm": 175.0,
  "age": 30,
  "gender": "male",
  "pregnant": false,
  "athlete": false,
  "waist_cm": 85.0,
  "lang": "ru"
}
```

### Response Schema: `BMICalculateResponse`

```python
{
  "bmi": float,                                    # Calculated BMI value
  "category": str | None,                          # Localized category (None for pregnant/children)
  "group": str,                                    # "general" | "athlete" | "elderly" | "child" | "teen" | "too_young" | "pregnant"
  "group_display": str,                            # Localized display name
  "interpretation": str,                           # Localized interpretation text
  "wht_ratio": float | None,                      # Waist-to-Height Ratio (if waist_cm provided)
  "waist_risk": {                                  # Waist risk assessment (if waist_cm provided)
    "wht_ratio": float,
    "risk_level": str,                             # "low" | "moderate" | "high" | "very_high"
    "notes": list[str]
  } | None,
  "notes": list[str],                              # Aggregated notes (from waist_risk)
  "age_band": str,                                 # "too_young" | "child" | "teen" | "adult" | "elderly"
  "visualization": {                               # BMI scale visualization spec (v1)
    "kind": str,                                   # "bmi_scale_v1"
    "bmi": float,                                  # Rounded BMI (1 decimal)
    "min": float,
    "max": float,
    "ranges": [
      {
        "from": float,
        "to": float,
        "key": str                                  # i18n key (e.g., "bmi.underweight")
      }
    ],
    "marker": {"value": float}                      # Current BMI marker (must equal bmi)
  } | None,
  "interpretation_v1": {                           # Structured interpretation (v1)
    "goal_direction": str,                         # "maintain" | "increase" | "decrease"
    "target_range": {"min": float, "max": float},
    "risk_flags": list[str],                       # i18n keys
    "priority_notes": list[str],                   # i18n keys
    "disclaimers": list[str]                       # i18n keys
  } | None,
  "soft_paywall": {                                # Soft paywall hook (wellness positioning)
    "text": str,                                   # Localized text
    "cta": str                                     # Call-to-action text
  } | None                                         # null when disabled
}
```

**Пример ответа:**

```json
{
  "bmi": 22.86,
  "category": "normal",
  "group": "general",
  "group_display": "General",
  "interpretation": "Your BMI is within the normal range for your age group.",
  "wht_ratio": 0.49,
  "waist_risk": {
    "wht_ratio": 0.49,
    "risk_level": "low",
    "notes": []
  },
  "notes": [],
  "age_band": "adult",
  "visualization": {
    "kind": "bmi_scale_v1",
    "bmi": 22.9,
    "min": 0.0,
    "max": 60.0,
    "ranges": [
      {"key": "bmi.underweight", "from": 0, "to": 18.5},
      {"key": "bmi.normal", "from": 18.5, "to": 25.0},
      {"key": "bmi.overweight", "from": 25.0, "to": 30.0},
      {"key": "bmi.obesity", "from": 30.0, "to": 60.0}
    ],
    "marker": {"value": 22.9}
  },
  "interpretation_v1": {
    "goal_direction": "maintain",
    "target_range": {"min": 18.5, "max": 25.0},
    "risk_flags": [],
    "priority_notes": [],
    "disclaimers": ["bmi.interpretation.disclaimer.general"]
  },
  "soft_paywall": {
    "text": "Unlock advanced health insights with PRO",
    "cta": "Upgrade to PRO"
  }
}
```

### Error Responses

- **400 Bad Request:** Domain validation fails (BMI out of bounds, invalid parameters)
- **422 Unprocessable Entity:** Pydantic validation fails (invalid field types, missing required fields)
- **500 Internal Server Error:** Engine unavailable or other server errors
- **501 Not Implemented:** Engine not available (fallback case)

---

## 5) Пути iOS/Web клиентов в репо

### iOS

- **API Client:** `ios/PulsePlate/APIClient.swift` (или аналогичный)
- **Models:** `ios/PulsePlate/Models/BMI*.swift`
- **Views:** `ios/PulsePlate/Views/BMI*.swift`

### Web (Frontend)

- **API Client:** `frontend/src/api/bmi.ts` (или аналогичный)
- **Types:** `frontend/src/api/schema.ts` (генерируется из OpenAPI)
- **Components:** `frontend/src/components/bmi/*.tsx`

### OpenAPI Generation

- **Generator:** `scripts/generate_openapi.py`
- **Command:** `make openapi`
- **Output:** `frontend/src/api/openapi.json`, `frontend/src/api/schema.ts`

---

## 6) Что считать ЗАПРЕЩЁННЫМ дальше

- ❌ Любые изменения BMI-математики без нового аудита
- ❌ Вынесение логики в клиенты
- ❌ "Заодно поправим" в cleanup-PR
- ❌ Мок `__import__`
- ❌ Контракты "на глаз"

---

## 7) Старт нового диалогового окна (первое сообщение)

Рекомендуемый старт:

> **"Начинаем downstream migration. Дай канонический контракт `/api/v1/bmi/calculate` (request/response) и пути iOS/Web клиентов в репо — делаем audit-first план PR-559."**

---

## 8) Ссылки на канонические документы

- **AGENTS.md** — глобальные правила проекта
- **docs/contracts/soft_paywall.md** — контракт soft paywall
- **docs/contracts/PRODUCT_TIER_MAP.md** — карта product tiers
- **docs/audit/PR_A_CLEANUP_AUDIT.md** — audit PR-A (cleanup)
- **docs/audit/ROADMAP_POST_REMEDIATION.md** — roadmap после remediation
- **app/routers/bmi.py** — FREE tier endpoint (canonical)
- **app/schemas/bmi.py** — request/response schemas

---

## 9) Legacy Shim Policy (из PR-558)

**`bmi_core.py` (repo root):**

- ✅ **Тонкий legacy-shim** без BMI-математики
- ✅ Делегирует в `core/bmi/*`
- ✅ Сохраняет ABI (позиционный порядок аргументов)
- ✅ Coverage exclusion (`# pragma: no cover`) — по дизайну
- ⚠️ **Не удалять** до миграции всех callers

**Rationale:**
- BC важнее чистоты
- Все вычисления в `core/bmi/*` (≥97% coverage)
- Shim исключён из coverage по дизайну (legacy compatibility)

---

## 10) Coverage Expectations

- **Total coverage:** ≥97% (hard gate)
- **Diff-cover:** ≥97% (hard gate)
- **Codecov patch:** ≈93% (информативный, не блокирующий)
- **Legacy shim:** excluded by design (`# pragma: no cover`)

---

**Последнее обновление:** 2026-01-19
**Версия:** 1.0 (post PR-558)
