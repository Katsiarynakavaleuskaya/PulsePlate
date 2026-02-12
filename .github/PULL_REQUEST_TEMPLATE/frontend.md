---
name: Frontend Feature
about: SPA / web UI changes
labels: [frontend, feat]
---

# feat(frontend): <scope>

## Summary

- Что меняем и зачем (ссылка на задачу).
- Связанные экраны/компоненты.

## Scope

- Основные файлы/папки.
- Out of scope / TODO.

## Acceptance Criteria

- Роуты / состояния / API вызовы.
- a11y: `role`, `aria-*`, контраст ≥4.5:1, клавиатура.
- MSW / fallback (если изменяли API).

## Tests

- [ ] `npm run lint`
- [ ] `npm test`
- [ ] `npm run build`
- [ ] Vitest / @testing-library / axe (укажи основные сценарии)

```bash
cd frontend
cp .env.example .env   # если нужен VITE_API_BASE
npm ci
npm run dev
```

## QA Notes

- Скриншоты / видео (если UI).
- Проверка ручных сценариев.

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping
- `<review-comment-url>` -> `<commit-sha>`
- No actionable review comments

👉 Доп. чек-листы: [docs/pr-checks.md](../../docs/pr-checks.md)
