<!-- markdownlint-disable MD003 MD022 MD032 MD033 MD041 -->

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

## Out of scope
- Что намеренно не входит в этот PR.

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

<!-- phase2-pre-closeout: final-security-pending -->

### Fixed in Commit Mapping
- Pending final clean scan and the single mapping/closeout commit.
- URL→SHA and disposition details belong only in the canonical artifact.

## Deferred / Follow-ups
- [ ] Ledger item(s): <link or None>
- [ ] GitHub issue(s): <link> (if any)

👉 Общие проверки: [docs/pr-checks.md](../../docs/pr-checks.md)

<!-- markdownlint-enable MD003 MD022 MD032 MD033 MD041 -->
