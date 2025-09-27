---
name: General PR
about: Default template for most pull requests
labels: []
---

# Title
<!-- Conventional commit: feat|fix|chore|docs|refactor|test|perf(scope): ... -->

## Summary
- Что изменилось?
- Почему / ссылка на задачу.

## Scope & Files
- Основные изменения (файлы, модули).
- Out of scope / TODO (кратко).

## Acceptance Criteria
- Перечисли ключевые критерии завершенности.

## Tests
- [ ] Unit / logic
- [ ] Integration / e2e
- [ ] Manual / QA steps (ниже)

```bash
# команды для локальной проверки
npm run lint
npm test
npm run build
```

## QA Checklist
- [ ] Happy-path сценарии
- [ ] Ошибки / таймауты / фоллбек
- [ ] Доступность / UX проверены

## Risks & Next Steps
- Риски / фичефлаги / мониторинг
- Следующие шаги после мержа

<details>
<summary>Optional: a11y / Security / Performance / Marketing / Docs</summary>

См. [docs/pr-checks.md](../docs/pr-checks.md) — общие требования и подсказки.

</details>
