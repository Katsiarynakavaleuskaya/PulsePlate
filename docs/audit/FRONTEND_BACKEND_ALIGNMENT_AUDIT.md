# Полный аудит соответствия фронтенда и бэкенда

**Дата:** 2026-01-09
**Версия:** 1.0
**Статус:** 🔴 Критические несоответствия обнаружены

---

## 📋 Executive Summary

### Критические проблемы (P0)
1. **Несоответствие endpoints**: Фронтенд использует `/api/v1/premium/*`, бэкенд мигрирует на `/api/v1/pro/*`
2. **Отсутствующие endpoints**: Фронтенд ожидает `/api/v1/premium/plan/week`, бэкенд предоставляет `/api/v1/pro/meal/weekly`
3. **Устаревшие типы**: OpenAPI схема не синхронизирована с актуальными бэкенд-моделями
4. **Отсутствие типизации**: Фронтенд использует ручные типы вместо OpenAPI-generated типов

### Средние проблемы (P1)
1. **Deprecated endpoints**: Бэкенд помечает `/api/v1/premium/*` как deprecated, но фронтенд всё ещё использует
2. **Несоответствие схем**: Типы `PlateApiResponse`, `TargetsApiResponse` не совпадают с бэкенд-схемами
3. **Отсутствие валидации**: Нет runtime-валидации ответов API через Zod/Pydantic

### Низкие проблемы (P2)
1. **Дублирование типов**: Ручные типы в `premium/types.ts` дублируют OpenAPI-схемы
2. **Устаревшие моки**: Моки в `mocks/` не соответствуют актуальным API-контрактам

---

## 🔍 Детальный анализ

### 1. Endpoints Mapping

#### ✅ Работающие endpoints

| Фронтенд | Бэкенд | Статус | Примечание |
|----------|--------|--------|------------|
| `/api/v1/premium/bmr` | `/api/v1/premium/bmr` | ✅ OK | Определён в `legacy_app.py:4150` |
| `/api/v1/premium/targets` | ❌ НЕТ | 🔴 **КРИТИЧНО** | Фронтенд ожидает, бэкенд не предоставляет |
| `/api/v1/premium/plate` | ❌ НЕТ | 🔴 **КРИТИЧНО** | Фронтенд ожидает, бэкенд не предоставляет |
| `/api/v1/premium/plan/week` | ❌ НЕТ | 🔴 **КРИТИЧНО** | Фронтенд ожидает, бэкенд предоставляет `/api/v1/pro/meal/weekly` |

#### 🔄 Deprecated endpoints (требуют миграции)

| Фронтенд | Бэкенд (новый) | Статус | Примечание |
|----------|----------------|--------|------------|
| `/api/v1/premium/plan/week` | `/api/v1/pro/meal/weekly` | ⚠️ **DEPRECATED** | Бэкенд помечает как deprecated, фронтенд не мигрирован |
| `/api/v1/premium/plan/week-flexible` | `/api/v1/pro/meal/weekly` | ⚠️ **DEPRECATED** | Уже deprecated в бэкенде |

#### ❌ Отсутствующие endpoints (бэкенд есть, фронтенд нет)

| Бэкенд | Фронтенд | Статус | Примечание |
|--------|----------|--------|------------|
| `/api/v1/pro/nutrition/targets` | ❌ НЕТ | ⚠️ **MISSING** | Бэкенд предоставляет, фронтенд не использует |
| `/api/v1/pro/nutrition/daily` | ❌ НЕТ | ⚠️ **MISSING** | Бэкенд предоставляет (Plate view), фронтенд не использует |
| `/api/v1/pro/meal/weekly` | ❌ НЕТ | ⚠️ **MISSING** | Бэкенд предоставляет, фронтенд использует старый endpoint |

---

### 2. Типы и схемы

#### Проблема: Дублирование типов

**Фронтенд:**
- `frontend/src/api/premium/types.ts` — ручные типы (BmrRequest, PlateRequest, TargetsRequest)
- `frontend/src/api/schema.ts` — OpenAPI-generated типы (не используются)

**Бэкенд:**
- `app/schemas/bmr.py` — BMRRequest, BMRResponse
- `app/schemas/vip.py` — WeeklyPlanRequest, WeekPlanResponse
- `app/routers/pro.py` — WeekPlanRequest, DailyNutritionResponse

**Несоответствия:**

1. **BMRRequest**:
   ```typescript
   // Фронтенд (premium/types.ts)
   type BmrRequest = {
     sex: 'male' | 'female';
     age: number;
     height_cm: number;
     weight_kg: number;
     activity: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';
     bodyfat?: number | null;
     lang?: SupportedPremiumLang | string;
   };
   ```
   ```python
   # Бэкенд (app/schemas/bmr.py)
   class BMRRequest(BaseModel):
       weight_kg: float = Field(..., gt=0)
       height_cm: float = Field(..., gt=0)
       age: int = Field(..., ge=0, le=120)
       sex: str = Field(..., pattern="^(male|female)$")
       activity: str = Field(..., pattern="^(sedentary|light|moderate|active|very_active)$")
       bodyfat: Optional[float] = Field(None, gt=0, le=60)
       lang: Language = "en"
   ```
   ✅ **Соответствует** (но фронтенд должен использовать OpenAPI-generated типы)

2. **PlateRequest/PlateApiResponse**:
   ```typescript
   // Фронтенд (premium/types.ts)
   type PlateApiResponse = {
     kcal: number;
     macros: Record<string, number>;
     portions: Portion;
     layout: LayoutItem[];
     meals: Meal[];
     day_micros?: Record<string, number>;
     meals_per_day: number;
   };
   ```
   ```python
   # Бэкенд (app/routers/pro.py)
   class DailyNutritionResponse(BaseModel):
       # ... (нужно проверить актуальную схему)
   ```
   ⚠️ **Требует проверки** — возможно несоответствие

3. **TargetsRequest/TargetsApiResponse**:
   ```typescript
   // Фронтенд (premium/types.ts)
   type TargetsApiResponse = {
     kcal_daily: number;
     macros: Record<string, number>;
     water_ml: number;
     priority_micros: Record<string, number>;
     activity_weekly: Record<string, number>;
     calculation_date: string;
     warnings: Array<Record<string, string>>;
   };
   ```
   ```python
   # Бэкенд (app/routers/pro.py)
   # Нужно проверить актуальную схему ответа
   ```
   ⚠️ **Требует проверки** — endpoint `/api/v1/premium/targets` отсутствует в бэкенде

4. **WeeklyPlanResponse**:
   ```typescript
   // Фронтенд (features/weekly-plan/model/types.ts)
   interface RawWeekPlanResponse {
     daily_menus: Array<Record<string, unknown>>;
     weekly_coverage: Record<string, unknown>;
     shopping_list: Record<string, unknown>;
     total_cost: number;
     adherence_score: number;
   }
   ```
   ```python
   # Бэкенд (app/schemas/vip.py)
   class WeekPlanResponse(BaseModel):
       # ... (нужно проверить актуальную схему)
   ```
   ⚠️ **Требует проверки** — возможно несоответствие структуры

---

### 3. OpenAPI Schema Sync

#### Проблема: Устаревшая OpenAPI схема

**Файл:** `frontend/src/api/openapi.json`

**Проблемы:**
1. Схема не обновляется автоматически при изменениях в бэкенде
2. Команда `npm run generate-types` генерирует типы из устаревшей схемы
3. Фронтенд не использует generated типы (`schema.ts`), предпочитая ручные типы

**Решение:**
- Настроить автоматическую генерацию OpenAPI из бэкенда
- Использовать generated типы вместо ручных
- Добавить CI-проверку синхронизации схем

---

### 4. API Client Issues

#### Проблема: Неправильные endpoints

**Файл:** `frontend/src/api/premium/weekly-plan.ts`
```typescript
export const getWeeklyPlan = createPremiumEndpoint<TargetsRequest, WeeklyMenuResponse>(
  '/api/v1/premium/plan/week'  // ❌ Устаревший endpoint
);
```

**Должно быть:**
```typescript
export const getWeeklyPlan = createPremiumEndpoint<WeekPlanRequest, WeekPlanResponse>(
  '/api/v1/pro/meal/weekly'  // ✅ Актуальный endpoint
);
```

**Файл:** `frontend/src/api/premium/targets.ts`
```typescript
export const getTargets = createPremiumEndpoint<TargetsRequest, TargetsApiResponse>(
  '/api/v1/premium/targets'  // ❌ Endpoint отсутствует в бэкенде
);
```

**Должно быть:**
```typescript
export const getTargets = createPremiumEndpoint<TargetsRequest, TargetsApiResponse>(
  '/api/v1/pro/nutrition/targets'  // ✅ Актуальный endpoint
);
```

**Файл:** `frontend/src/api/premium/plate.ts`
```typescript
export const getPlate = createPremiumEndpoint<PlateRequest, PlateApiResponse>(
  '/api/v1/premium/plate'  // ❌ Endpoint отсутствует в бэкенде
);
```

**Должно быть:**
```typescript
export const getPlate = createPremiumEndpoint<PlateRequest, PlateApiResponse>(
  '/api/v1/pro/nutrition/daily'  // ✅ Актуальный endpoint (GET, не POST!)
);
```

---

### 5. Adapter Issues

#### Проблема: Несоответствие структуры ответа

**Файл:** `frontend/src/features/weekly-plan/model/adapter.ts`

**Проблемы:**
1. Adapter ожидает `RawWeekPlanResponse` с полями `daily_menus`, `weekly_coverage`, `shopping_list`
2. Бэкенд может возвращать другую структуру (нужно проверить `WeekPlanResponse` в бэкенде)
3. Adapter использует `Record<string, unknown>` вместо строгих типов

**Решение:**
- Использовать OpenAPI-generated типы для `RawWeekPlanResponse`
- Добавить runtime-валидацию через Zod
- Обновить adapter под актуальную структуру бэкенда

---

## 🎯 План закрытия соответствия

### Phase 1: Критические исправления (P0) — 1-2 недели

#### 1.1 Миграция endpoints (3-5 дней)

**Задачи:**
- [ ] Обновить `frontend/src/api/premium/weekly-plan.ts`: `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`
- [ ] Обновить `frontend/src/api/premium/targets.ts`: `/api/v1/premium/targets` → `/api/v1/pro/nutrition/targets`
- [ ] Обновить `frontend/src/api/premium/plate.ts`: `/api/v1/premium/plate` → `/api/v1/pro/nutrition/daily` (изменить метод на GET)
- [ ] Обновить типы запросов/ответов под новые endpoints
- [ ] Обновить тесты под новые endpoints
- [ ] Обновить моки под новые endpoints

**Файлы для изменения:**
- `frontend/src/api/premium/weekly-plan.ts`
- `frontend/src/api/premium/targets.ts`
- `frontend/src/api/premium/plate.ts`
- `frontend/src/api/premium/types.ts`
- `frontend/src/mocks/handlers.ts`
- `frontend/src/api/__tests__/weekly-plan-integration.test.ts`
- `frontend/src/api/__tests__/targets-integration.test.ts`

**Проверка:**
```bash
cd frontend
npm run test
npm run build
```

#### 1.2 Синхронизация OpenAPI схемы (2-3 дня)

**Задачи:**
- [ ] Настроить автоматическую генерацию OpenAPI из бэкенда
- [ ] Обновить `frontend/src/api/openapi.json` из актуального бэкенда
- [ ] Регенерировать `frontend/src/api/schema.ts`: `npm run generate-types`
- [ ] Заменить ручные типы на OpenAPI-generated типы
- [ ] Обновить импорты во всех файлах

**Файлы для изменения:**
- `frontend/src/api/openapi.json` (обновить из бэкенда)
- `frontend/src/api/schema.ts` (регенерировать)
- `frontend/src/api/premium/types.ts` (использовать generated типы)
- `frontend/src/api/premium/bmr.ts`
- `frontend/src/api/premium/plate.ts`
- `frontend/src/api/premium/targets.ts`
- `frontend/src/api/premium/weekly-plan.ts`

**Проверка:**
```bash
cd frontend
npm run generate-types
npm run typecheck  # если есть
npm run test
```

#### 1.3 Исправление типов ответов (2-3 дня)

**Задачи:**
- [ ] Проверить актуальные схемы ответов в бэкенде:
  - `app/schemas/vip.py` → `WeekPlanResponse`
  - `app/routers/pro.py` → `DailyNutritionResponse`
  - `app/routers/pro.py` → ответ `estimate_targets_minimal()`
- [ ] Обновить типы в фронтенде под актуальные схемы
- [ ] Обновить adapter в `frontend/src/features/weekly-plan/model/adapter.ts`
- [ ] Добавить runtime-валидацию через Zod (опционально)

**Файлы для изменения:**
- `frontend/src/api/premium/types.ts`
- `frontend/src/features/weekly-plan/model/types.ts`
- `frontend/src/features/weekly-plan/model/adapter.ts`

**Проверка:**
```bash
cd frontend
npm run test
npm run build
```

---

### Phase 2: Улучшения (P1) — 1 неделя

#### 2.1 Runtime валидация (2-3 дня)

**Задачи:**
- [ ] Добавить Zod-схемы для всех API-ответов
- [ ] Интегрировать валидацию в `api/client.ts`
- [ ] Добавить логирование несоответствий в dev-режиме
- [ ] Обновить тесты

**Файлы для изменения:**
- `frontend/src/api/client.ts`
- `frontend/src/api/premium/types.ts` (добавить Zod-схемы)
- `frontend/src/api/__tests__/api-serialization.test.ts`

#### 2.2 Удаление deprecated endpoints (1-2 дня)

**Задачи:**
- [ ] Удалить использование `/api/v1/premium/plan/week-flexible` (если есть)
- [ ] Удалить использование `/api/v1/premium/plan/week` (после миграции)
- [ ] Обновить документацию

**Файлы для изменения:**
- `frontend/src/api/client.ts` (удалить mockUrl для deprecated endpoints)
- `frontend/src/mocks/handlers.ts` (удалить deprecated handlers)

#### 2.3 Обновление моков (1-2 дня)

**Задачи:**
- [ ] Обновить моки под актуальные API-контракты
- [ ] Убедиться, что моки соответствуют реальным ответам бэкенда
- [ ] Обновить тесты

**Файлы для изменения:**
- `frontend/src/mocks/handlers.ts`
- `frontend/src/mocks/server.ts`
- `frontend/public/mock/*.json` (если есть)

---

### Phase 3: Оптимизация (P2) — 1 неделя

#### 3.1 Рефакторинг типов (2-3 дня)

**Задачи:**
- [ ] Полностью перейти на OpenAPI-generated типы
- [ ] Удалить ручные типы из `premium/types.ts` (оставить только Zod-схемы)
- [ ] Обновить все импорты
- [ ] Добавить JSDoc-комментарии для generated типов

**Файлы для изменения:**
- `frontend/src/api/premium/types.ts`
- Все файлы, использующие ручные типы

#### 3.2 CI/CD интеграция (1-2 дня)

**Задачи:**
- [ ] Добавить CI-проверку синхронизации OpenAPI-схем
- [ ] Добавить автоматическую регенерацию типов при изменениях в бэкенде
- [ ] Добавить проверку типов в pre-commit hooks

**Файлы для изменения:**
- `.github/workflows/*.yml`
- `frontend/.husky/pre-commit` (если есть)

#### 3.3 Документация (1 день)

**Задачи:**
- [ ] Обновить `frontend/README.md` с инструкциями по работе с API
- [ ] Добавить документацию по миграции endpoints
- [ ] Обновить `frontend/AGENTS.md` с правилами работы с API

**Файлы для изменения:**
- `frontend/README.md`
- `frontend/AGENTS.md`

---

## 📊 Метрики успеха

### Критерии завершения Phase 1:
- ✅ Все endpoints мигрированы на `/api/v1/pro/*`
- ✅ OpenAPI-схема синхронизирована с бэкендом
- ✅ Все тесты проходят
- ✅ Build проходит без ошибок
- ✅ Типы соответствуют бэкенд-схемам

### Критерии завершения Phase 2:
- ✅ Runtime-валидация добавлена
- ✅ Deprecated endpoints удалены
- ✅ Моки обновлены

### Критерии завершения Phase 3:
- ✅ Полный переход на OpenAPI-generated типы
- ✅ CI-проверки настроены
- ✅ Документация обновлена

---

## 🔧 Технические детали

### Автоматическая генерация OpenAPI

## Вариант 1: Скрипт генерации

```bash
# В корне проекта
make openapi
cd frontend && npm run generate-types
```

## Вариант 2: CI/CD интеграция

```yaml
# .github/workflows/sync-openapi.yml
- name: Generate OpenAPI
  run: make openapi
- name: Generate Types
  run: |
    cd frontend && npm run generate-types
```

### Миграция типов

**До:**
```typescript
// premium/types.ts
export type BmrRequest = { ... };
export type BmrApiResponse = { ... };
```

**После:**
```typescript
// premium/types.ts
import type { components } from '../schema';

export type BmrRequest = components['schemas']['BMRRequest'];
export type BmrApiResponse = components['schemas']['BMRResponse'];
```

### Runtime валидация (Zod)

```typescript
import { z } from 'zod';

const BmrResponseSchema = z.object({
  bmr: z.object({
    mifflin: z.number(),
    harris: z.number(),
    katch: z.number().optional(),
  }),
  tdee: z.object({ ... }),
  // ...
});

export async function getBmr(body: BmrRequest): Promise<BmrApiResponse> {
  const response = await api('/api/v1/premium/bmr', { method: 'POST', body });
  return BmrResponseSchema.parse(response); // Runtime validation
}
```

---

## 🚨 Риски и митигация

### Риск 1: Breaking changes в бэкенде
**Митигация:** Использовать feature flags, версионирование API, backward compatibility

### Риск 2: Несоответствие типов в runtime
**Митигация:** Runtime-валидация через Zod, логирование несоответствий

### Риск 3: Регрессии после миграции
**Митигация:** Полное покрытие тестами, постепенная миграция, feature flags

---

## 📝 Чеклист для разработчика

### Перед началом работы:
- [ ] Прочитать этот документ полностью
- [ ] Проверить актуальные endpoints в бэкенде
- [ ] Обновить OpenAPI-схему
- [ ] Регенерировать типы

### Во время работы:
- [ ] Обновлять типы по мере изменения бэкенда
- [ ] Писать тесты для новых endpoints
- [ ] Обновлять моки
- [ ] Проверять типы в IDE

### После завершения:
- [ ] Запустить все тесты
- [ ] Проверить build
- [ ] Обновить документацию
- [ ] Создать PR с описанием изменений

---

## 📚 Ссылки

- [Backend API Documentation](./MOBILE_ENDPOINTS.md)
- [Frontend API Client](../frontend/src/api/client.ts)
- [OpenAPI Schema](../frontend/src/api/openapi.json)
- [Generated Types](../frontend/src/api/schema.ts)

---

**Автор:** AI Assistant
**Дата последнего обновления:** 2026-01-09
**Версия документа:** 1.0
