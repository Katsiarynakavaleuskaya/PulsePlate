---
name: General PR
about: Default template for most pull requests
title: ''
labels: []
---

## Summary
- Что изменилось?
- Почему? (ссылка на задачу / issue)

## Scope
- ✅ Ключевые изменения
- ⛔️ Out-of-scope / TODO (кратко)

## Testing
- [ ] Unit / logic
- [ ] Integration / e2e
- [ ] Manual / QA steps (укажи результат ниже)

```bash
# команды для локальной проверки
npm run lint && npm test && npm run build
# или Xcode build + нужные тесты
```

## Checklist
- [ ] Docs/README обновлены (если нужно)
- [ ] A11y / UX (контраст, клавиатура, VO)
- [ ] Security / privacy review (если применимо)
- [ ] Performance / monitoring учтены

<details>
<summary>Optional notes</summary>

### Accessibility
- Контраст ≥4.5:1, `aria-*` / VO-лейблы, touch ≥44×44pt.

### Security & Privacy
- Нет секретов в коде; личные данные не логируются.
- HealthKit/StoreKit — явные разрешения и copy в UI.

### Performance
- Веб: bundle/рендер/кэширование.
- iOS: размер билда, память, FPS (если релевантно).

### Marketing & GTM
- Тексты/локали (EN/RU/ES) готовы.
- События аналитики (paywall_*, purchase_*, и т.д.).

### Risks & Rollout
- Риски, миграции, Feature Flags, мониторинг после релиза.

### Decision Log
- Ключевые решения / компромиссы.

</details>

## Next Steps
- Что делать после мержа / связанные задачи.
