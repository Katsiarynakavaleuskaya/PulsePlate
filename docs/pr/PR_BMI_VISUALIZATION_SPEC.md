# PR: BMI Visualization via JSON Spec (v1)

## 🎯 Цель

Добавить визуализацию BMI через JSON spec в существующий endpoint `/api/v1/bmi/calculate`, чтобы frontend мог рендерить шкалу BMI без зависимости от base64 PNG.

## ✅ Что делаем

### Backend

1. **Схема ответа** (`app/schemas/bmi.py`)
   - Добавить `BMIScaleV1Spec` (Pydantic модель)
   - Добавить `visualization: BMIScaleV1Spec | None` в `BMICalculateResponse`

2. **Spec builder** (`app/services/bmi_visualization.py` - новый файл)
   - Функция `build_bmi_scale_v1(bmi: float) -> BMIScaleV1Spec`
   - **Важно**: это **API adapter**, а не domain logic (живёт в `app/services/`, не в `core/`)
   - Фиксированная шкала 0-60 (WHO standard thresholds)
   - i18n ключи: `bmi.underweight`, `bmi.normal`, `bmi.overweight`, `bmi.obesity`
   - Без использования `group` (group влияет только на `category`/`interpretation`, не на шкалу)

3. **Интеграция** (`app/routers/bmi.py`)
   - В `bmi_calculate_handler()` после создания `resp` добавить:

     ```python
     from app.services.bmi_visualization import build_bmi_scale_v1
     resp.visualization = build_bmi_scale_v1(result.bmi)
     ```

   - **Важно**: spec возвращается **всегда** (по умолчанию), без флага `include_chart`
   - `include_chart` остаётся **исключительно legacy-механизмом** в `legacy_app.py`

### Frontend

4. **i18n ключи** (`frontend/src/locales/{ru,en,es}.json`)
   - Добавить секцию `bmi` с ключами: `underweight`, `normal`, `overweight`, `obesity`

5. **Компонент** (`frontend/src/components/BmiScaleV1.tsx` - новый файл)
   - SVG-рендеринг шкалы с зонами и маркером
   - Использование i18n ключей из spec
   - Цвета и стили на фронте (не из API)

6. **Интеграция в UI** (если есть BMI страница/компонент)
   - Подключить `BmiScaleV1` для отображения `visualization` из ответа API

### Тесты

7. **Backend тесты** (`tests/test_bmi_visualization_spec.py` - новый файл)
   - `test_build_bmi_scale_v1()` - правильный spec для разных BMI значений
   - `test_ranges_monotonic()` - ranges последовательны (from < to, без разрывов)
   - `test_marker_value_equals_bmi()` - marker.value == bmi
   - `test_spec_in_response()` - `/api/v1/bmi/calculate` возвращает `visualization`

8. **Frontend тесты** (`frontend/src/components/__tests__/BmiScaleV1.test.tsx` - новый файл)
   - Snapshot тест для SVG
   - Проверка i18n ключей

## ❌ Чего НЕ делаем

1. **НЕ создаём новый endpoint** - используем существующий `/api/v1/bmi/calculate`
2. **НЕ добавляем цвета в API** - цвета живут на фронте
3. **НЕ используем `group` в spec builder** - thresholds фиксированы (0-60)
4. **НЕ добавляем анимации/кэширование** - это для следующих PR
5. **НЕ удаляем legacy base64** - он остаётся в `legacy_app.py`, **НЕ интегрируется** в `/api/v1/bmi/calculate`
6. **НЕ используем matplotlib в новом коде** - только JSON spec
7. **НЕ добавляем `dict[str, Any]`** - только Pydantic модели

## 🧠 Почему так

### Архитектурные принципы

- **Backend = смысл и границы** (числа, thresholds, semantic keys)
- **Frontend = визуальный язык** (SVG, цвета, layout, a11y)
- **Разделение ответственности**: spec builder в `app/services/` (адаптер), не в `core/` (domain) и не в router

### Философия проекта

- Следуем `app/AGENTS.md`: routers thin, бизнес-логика в `core/`, адаптеры в `app/services/`
- Pydantic v2 только (`model_validate`, `model_dump`)
- Типизация строгая (Pydantic модели, не `dict[str, Any]`)

### UX и производительность

- JSON spec легче base64 PNG (50-200KB → ~500 bytes)
- Не зависит от matplotlib/freetype в проде
- Легко тестируется (JSON snapshot)
- Переносимо (iOS, Gradio, другие клиенты)

### Legacy compatibility

- Не ломаем существующий контракт (`BMICalculateResponse` расширяем опциональным полем)
- Legacy base64 остаётся доступным через `legacy_app.py` (если требуется)
- **Чёткое разграничение**: base64 **не интегрируется** в новый endpoint `/api/v1/bmi/calculate`
- `include_chart` параметр **не используется** в новом endpoint (остаётся только в legacy)

## 📋 Чеклист реализации

- [ ] Backend: `BMIScaleV1Spec` модель в `app/schemas/bmi.py`
- [ ] Backend: `build_bmi_scale_v1()` в `app/services/bmi_visualization.py`
- [ ] Backend: интеграция в `bmi_calculate_handler()`
- [ ] Backend: тесты spec генерации
- [ ] Frontend: i18n ключи в локалях
- [ ] Frontend: компонент `BmiScaleV1.tsx`
- [ ] Frontend: snapshot тест
- [ ] Ручная проверка: curl `/api/v1/bmi/calculate` → проверка `visualization` в ответе
- [ ] Ручная проверка: frontend рендерит шкалу корректно

## 🔗 Связанные документы

- `app/AGENTS.md` - архитектурные инварианты
- `docs/pr/PR_BMI_VISUALIZATION_AUDIT.md` - анализ двух подходов (если создан)
- `bmi_visualization.py` - legacy base64 модуль (не трогаем)

## 📝 Примечания

- **Фиксированная шкала 0-60**: group-specific thresholds не используются в spec (group влияет только на `category`/`interpretation`)
- **i18n ключи**: формат `bmi.underweight` (flat structure в JSON локалей)
- **Опциональное поле**: `visualization: BMIScaleV1Spec | None` - фронт должен проверять наличие перед рендером
- **Spec builder**: `build_bmi_scale_v1` — это **API adapter** (не domain logic), живёт в `app/services/`, не в `core/`
- **Legacy base64**: остаётся **только** в `legacy_app.py`, не интегрируется в новый endpoint
