# Title
<!-- Используй conventional commits: feat|fix|chore|docs|refactor|test|perf(scope): ... -->

## Summary
Коротко: что и зачем. Ссылка на задачу/issue.

## Plan / Scope
- [ ] Основные изменения (bullet list)
- [ ] Что НЕ входит в PR

## Changes
- Папки/файлы: перечисли ключевые.
- UI: скриншоты/видео (если есть).
- API/контракты: эндпоинты, схемы запрос/ответ.

## Accessibility (a11y)
- Контраст ≥4.5:1
- Навигация клавиатурой / VO-лейблы
- Размеры тача ≥44×44pt

## Tests
- [ ] Unit
- [ ] Integration/e2e
- [ ] Snapshot (если UI)
Команда локально:
```bash
npm run lint && npm test && npm run build
# или для iOS: Xcode build + StoreKitTest/UITests
```

## Security Notes
- Секреты отсутствуют в коде (используем .env.example)
- Личные данные не логируются
- Для HealthKit/StoreKit — раскрытие и явные разрешения

## Performance
- Оценка влияния (бандл/рендеры/память)
- Веб: tree-shaking/кэширование; iOS: измеримые регрессии

## Marketing & GTM
- Тексты/локали готовы (EN/RU/ES)
- События аналитики (например, paywall_*)

## Documentation
- README/Docs обновлены (если нужно)
- Комментарии в коде там, где нетривиальная логика

## QA Checklist
- Happy-path сценарии
- Ошибки/таймауты
- Моки/фоллбеки

## Risks & Rollout
- Риски/миграции/фичефлаги
- Мониторинг/алертинг после мержа

## Decision Log
Ключевые решения и почему.

## Next Actions
Следующие маленькие шаги после мержа.
