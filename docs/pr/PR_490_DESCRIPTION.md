# PR #490: feat(web+bmi): add BMI visualization JSON spec v1 (SVG-ready)

## Summary

Добавляем **JSON spec визуализации BMI** в существующий endpoint **`/api/v1/bmi/calculate`**:
`visualization.kind = "bmi_scale_v1"`, чтобы Web (и позже iOS) могли рендерить **SVG шкалу BMI** без base64 PNG и без matplotlib.

* **Backend** отдаёт *семантику и границы* (числа, диапазоны, i18n keys)
* **Frontend** отвечает за *визуальный язык* (SVG, цвета, layout, a11y)
* **Legacy base64** не трогаем: остаётся в `legacy_app.py` как fallback для legacy-пути

## Scope (What we do)

### Backend

* Добавляем `BMIScaleV1Spec` (Pydantic) + поле `visualization: BMIScaleV1Spec | None` в `BMICalculateResponse`
* Добавляем builder `build_bmi_scale_v1(bmi: float) -> BMIScaleV1Spec` в `app/services/`
* Интегрируем builder в `bmi_calculate_handler()` для `/api/v1/bmi/calculate`
* Добавляем тесты: spec builder + наличие поля в ответе endpoint

### Frontend (можно в этом PR или отдельным follow-up — см. ниже)

* Добавляем i18n ключи `bmi.underweight|normal|overweight|obesity`
* Добавляем компонент `BmiScaleV1.tsx` (SVG)
* Подключаем компонент на экран результата
* Snapshot/unit тесты

## Non-goals (What we do NOT do)

* Не создаём v2 endpoint / новые маршруты
* Не добавляем `color` в API (цвета и дизайн — только frontend)
* Не используем `group` в spec builder (шкала фиксирована)
* Не добавляем matplotlib/base64 в новый endpoint
* Не делаем анимации/кэширование/темизацию (отложено)

## API Contract (v1)

`visualization` — **опционально**, но мы добавляем его в новый endpoint как spec:

```json
"visualization": {
  "kind": "bmi_scale_v1",
  "bmi": 23.4,
  "min": 0,
  "max": 60,
  "ranges": [
    {"key": "bmi.underweight", "from": 0, "to": 18.5},
    {"key": "bmi.normal", "from": 18.5, "to": 25},
    {"key": "bmi.overweight", "from": 25, "to": 30},
    {"key": "bmi.obesity", "from": 30, "to": 60}
  ],
  "marker": { "value": 23.4 }
}
```

## Security Notes

* Не добавляем base64 PNG в новый endpoint → меньше payload и меньше риск DoS/latency.
* Не раскрываем детали ошибок; используем текущий error-envelope/masking (не менять).
* Цвета/стили не уходят в API → контракт остаётся стабильным.

## Marketing & GTM (коротко)

* Улучшаем perceived quality на сайте ("у нас есть визуализация BMI")
* База для iOS и Gradio демо без тяжёлых зависимостей

## Decision Log

* **Решение:** JSON spec (`bmi_scale_v1`) — основной формат; SVG рендер на фронте.
* **Причина:** стабильность, переносимость, лёгкий payload, тестируемость.
* **Legacy:** base64 остаётся только в legacy path (не трогаем).

## Next Actions

1. Сделать backend часть + тесты (должно пройти CI)
2. Если успеваем — фронт (компонент + i18n + интеграция)
3. Если фронт не успеваем — отдельный follow-up PR "web BMI scale UI v1"

## Related Documents

* `docs/pr/PR_BMI_VISUALIZATION_SPEC.md` - детальная спецификация
* `app/AGENTS.md` - архитектурные инварианты
