# Docs debt backlog

**Purpose:** Track documentation issues that are real debt but not worth blocking delivery.

**Rule:** Fix only when touching nearby docs or when it breaks navigation / ops safety.

---

## Classification tags

* **DOCS-BLOCKER** — ломает понимание / вводит в ошибку / конфликтует с текущим каноном (чинить первыми)
* **DOCS-STALE** — устарело, но не опасно (переносить в архив или помечать как устаревшее)
* **DOCS-STYLE** — косметика (не трогать, если не трогаем файл)

---

## P0 — Fix ASAP (blocks usage or safety) [DOCS-BLOCKER]

- [ ] Broken links in entrypoints (README, docs/README, START_HERE, RUNBOOK_AGENT)
- [ ] Deploy/runbook commands that are wrong for current main
- [ ] Policy contradictions (AGENTS/RUNBOOK conflict)

---

## P1 — Should fix soon (quality + maintainability) [DOCS-STALE]

- [ ] Markdownlint cleanup (MD040 fenced code language, MD036 emphasis-as-heading, etc.)
- [ ] Normalize naming (UPPER_SNAKE_CASE) for new docs only (no mass renames unless planned)
- [ ] Cross-links updated after moves (internal anchors)

---

## P2 — Nice to have (low risk) [DOCS-STYLE]

- [ ] Style/grammar (LanguageTool)
- [ ] Translation gaps (RU/EN/ES consistency)
- [ ] Old reports archived under docs/archive/YYYY-MM-DD/

---

## Top-10 stale docs (highest risk / most misleading)

**Risk note:** Don't trust stale docs — follow `docs/README.md` and canonical sources (`docs/runbooks/`, `docs/policy/`, `docs/deploy/`).

1. [ ] `docs/START_HERE_RU.md` — add status header + canonical links
2. [ ] `docs/deploy/SOLO.md` — verify commands match current main
3. [ ] `docs/runbooks/TESTING_BEST_PRACTICES.md` — sync with current test patterns
4. [ ] `docs/runbooks/PROJECT_UPDATES.md` — mark as historical or archive
5. [ ] `docs/reports/PROGRESS_LOG.md` — move to archive or mark stale
6. [ ] `docs/specs/PREMIUM_TARGETS_EXAMPLES.md` — verify API contract matches current
7. [ ] `docs/pr/PR-*_DESCRIPTION.md` (old PR docs) — archive or consolidate
8. [ ] `docs/runbooks/CRON.md` — verify cron syntax matches deployment
9. [ ] `docs/deploy/DOMAIN.md` — verify DNS/domain setup matches current infra
10. [ ] `docs/runbooks/LOCALE_TESTS.md` — sync with current i18n patterns

**Action:** Add status headers to stale docs (see pattern below) instead of rewriting.

---

## Status header pattern (for stale docs)

Add to top of stale documents:

```markdown
> **Status:** stale (kept for historical context)
> **Canonical:** `docs/runbooks/RUNBOOK_AGENT.md`, `docs/policy/*`
> **Last verified:** YYYY-MM-DD (or "unknown")
```

---

## Plan: Docs Cleanup Sprint (after PR-457)

**PR-1 (minimal, no content rewrites):**
- [ ] Add status headers to top-10 stale docs
- [ ] Move completely obsolete/duplicate docs to `docs/archive/YYYY-MM-DD/`
- [ ] Update `docs/README.md` with clear "start here" navigation

**PR-2 (content, separate):**
- [ ] Rewrite 3–5 most critical starter docs (`docs/START_HERE_RU.md`, etc.)
- [ ] Sync deploy docs with current infrastructure
- [ ] Consolidate old PR documentation

---

## Tracking

- Prefer GitHub Issues for items that need ownership/date.
- This file is a staging area; migrate to issues when it becomes actionable.

---

## Notes

- **Do not** migrate "thousands of cosmetic issues" here.
- Write only what either **breaks navigation**, **misleads users**, or **creates policy drift**.
- **Docs improve from pain** — canonical docs (deploy/runbook/agents) are strong because they come from real incidents. Starter docs can be marked stale rather than rewritten immediately.
