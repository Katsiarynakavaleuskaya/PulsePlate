# PR-490A: Review Checklist для Специалиста 2

## 🎯 Цель review

Проверить, что PR-490A **не сломал legacy**, **не добавил тяжёлое**, и **не испортил UX-следующий шаг** (PR-490B).

---

## ✅ Обязательные проверки (10 пунктов)

### 1. Legacy не тронут

- [ ] `legacy_app.py` не изменён
- [ ] `bmi_visualization.py` (корневой) не изменён
- [ ] `include_chart` параметр не используется в новом endpoint
- [ ] Base64 generation не добавлен в `/api/v1/bmi/calculate`

**Почему важно:** Legacy должен работать независимо от нового spec.

---

### 2. Alias "from" работает корректно

- [ ] В `app/routers/bmi.py` используется `resp.model_dump(by_alias=True)`
- [ ] В тесте проверяется, что JSON содержит `"from"` (не `"from_"`)
- [ ] В тесте проверяется, что JSON **не содержит** `"from_"`

**Почему важно:** Frontend ожидает `"from"` в JSON, не `"from_"`.

**Как проверить:**
```bash
curl -X POST http://localhost:8000/api/v1/bmi/calculate \
  -H "Content-Type: application/json" \
  -d '{"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "male", "lang": "en"}' \
  | jq '.visualization.ranges[0]'
```

Должно быть:
```json
{
  "key": "bmi.underweight",
  "from": 0,
  "to": 18.5
}
```

**НЕ должно быть:**
```json
{
  "key": "bmi.underweight",
  "from_": 0,
  "to": 18.5
}
```

---

### 3. Request payload в тесте соответствует реальному контракту

- [ ] Тест использует `"gender"` (не `"sex"`)
- [ ] Тест использует поля из `BMICalculateRequest` schema
- [ ] Тест проходит с реальным endpoint

**Почему важно:** Неправильный payload → тест падает или не тестирует реальный путь.

**Как проверить:**
- Открыть `app/schemas/bmi.py` → `BMICalculateRequest`
- Сравнить с тестовым payload в `test_bmi_calculate_returns_visualization()`

---

### 4. Импорт app в тесте каноничный

- [ ] Используется `from app import app` (как в других тестах проекта)
- [ ] НЕ используется `__import__("app", fromlist=["app"])` или другие хаки

**Почему важно:** Неканоничный импорт может сломаться при рефакторинге.

**Как проверить:**
```bash
grep -r "from app import app" tests/ | head -5
```

Должен быть такой же паттерн.

---

### 5. Нет цветов в API

- [ ] В `BMIScaleV1Spec` нет поля `color` или `colors`
- [ ] В `build_bmi_scale_v1()` нет цветов
- [ ] В тестах нет проверок цветов

**Почему важно:** Цвета = дизайн = frontend concern. API с цветами = vendor lock.

---

### 6. Нет matplotlib/base64 в новом endpoint

- [ ] `app/services/bmi_visualization.py` не импортирует matplotlib
- [ ] `build_bmi_scale_v1()` не генерит base64
- [ ] В router нет вызовов `generate_bmi_visualization()` (legacy функция)

**Почему важно:** Base64 = тяжёлый payload, matplotlib = зависимость, latency.

---

### 7. Payload size разумный

- [ ] JSON spec ~500 bytes (не 50-200KB как base64)
- [ ] В тесте можно проверить размер ответа (опционально)

**Почему важно:** Большой payload = latency, плохой UX на мобильных.

**Как проверить:**
```bash
curl -X POST http://localhost:8000/api/v1/bmi/calculate \
  -H "Content-Type: application/json" \
  -d '{"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "male", "lang": "en"}' \
  | jq '.visualization' | wc -c
```

Должно быть ~200-500 bytes, не 50KB+.

---

### 8. Builder fail-safe для edge cases

- [ ] Тест на edge cases (0.0, 60.0, очень маленькие значения)
- [ ] `round()` не падает на нормальных float значениях
- [ ] Нет проверок на `nan`/`inf` (если upstream гарантирует float)

**Почему важно:** Edge cases могут сломать endpoint в проде.

**Опционально:** Если upstream (BMI engine) может вернуть `nan`/`inf`, добавить guard в builder.

---

### 9. Coverage не упало

- [ ] `pytest --cov` показывает coverage ≥97%
- [ ] Новые файлы покрыты тестами
- [ ] Существующие тесты не сломались

**Почему важно:** Проект требует 97% coverage.

---

### 10. Graceful поведение при ошибках

- [ ] Если `build_bmi_scale_v1()` падает, endpoint не падает (опционально: возвращает `visualization: None`)
- [ ] Тесты не падают при отсутствии visualization (если это допустимо)

**Почему важно:** Ошибка в builder не должна ломать весь endpoint.

**Текущий план:** Builder всегда возвращает spec (нет ошибок), но можно добавить try/except в router для безопасности.

---

## 🚫 Что НЕ проверяем (не scope PR-490A)

- ❌ Frontend компонент (это PR-490B)
- ❌ i18n ключи на фронте (это PR-490B)
- ❌ SVG рендеринг (это PR-490B)
- ❌ UX/дизайн (это PR-490B)
- ❌ Анимации/кэширование (отложено)

---

## 📝 Формат review комментариев

Если находишь проблему:

```
❌ [Проверка #X] Проблема: ...

Ожидалось: ...
Фактически: ...

Как исправить: ...
```

Если всё ок:

```
✅ [Проверка #X] OK: ...
```

---

## ⚡ Быстрая проверка (5 минут)

Если нет времени на полный review, проверь минимум:

1. ✅ Legacy не тронут (`legacy_app.py` не изменён)
2. ✅ `by_alias=True` в `model_dump()` (проверка alias "from")
3. ✅ Нет цветов в API
4. ✅ Нет matplotlib/base64
5. ✅ Тесты проходят

---

## 🔗 Связанные документы

- `docs/pr/PR_490A_BACKEND_ONLY.md` - полный план PR-490A
- `docs/pr/PR_BMI_VISUALIZATION_SPEC.md` - спецификация
- `app/AGENTS.md` - архитектурные инварианты

