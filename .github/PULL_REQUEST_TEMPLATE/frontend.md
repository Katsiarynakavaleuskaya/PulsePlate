<!-- markdownlint-disable MD003 MD022 MD032 MD033 MD041 -->

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

## Out of scope

- Что намеренно не входит в этот PR / TODO.

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

<!-- phase2-pre-closeout: final-security-pending -->

### Fixed in Commit Mapping
- Pending final clean scan and the single mapping/closeout commit.
- URL→SHA and disposition details belong only in the canonical artifact.

## Deferred / Follow-ups
- [ ] Ledger item(s): <link or None>
- [ ] GitHub issue(s): <link> (if any)

👉 Доп. чек-листы: [docs/pr-checks.md](../../docs/pr-checks.md)

<!-- markdownlint-enable MD003 MD022 MD032 MD033 MD041 -->
