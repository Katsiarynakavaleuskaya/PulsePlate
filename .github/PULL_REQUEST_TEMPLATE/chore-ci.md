---
name: Tooling / CI
about: Linting, formatting, workflows, build scripts
labels: [chore, ci]
---

# chore(frontend): <scope>

## Summary
- Что меняем (скрипты, конфиги, workflow) и зачем.

## Scope
- package.json / конфиги / workflows.
- Out of scope (если есть).

## Tests
- [ ] `npm ci`
- [ ] `npm run lint`
- [ ] `npm test -- --ci`
- [ ] `npm run build`
- Логи GitHub Actions приложены / проверены.

## Notes
- Кэш npm / Node version / matrix.
- Правила защиты ветки, требуемые статусы.

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping
- `<review-comment-url>` -> `<commit-sha>`
- No actionable review comments

👉 Общие проверки: [docs/pr-checks.md](../../docs/pr-checks.md)
