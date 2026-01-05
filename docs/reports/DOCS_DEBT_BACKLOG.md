# Docs debt backlog

**Purpose:** Track documentation issues that are real debt but not worth blocking delivery.

**Rule:** Fix only when touching nearby docs or when it breaks navigation / ops safety.

---

## P0 — Fix ASAP (blocks usage or safety)

- [ ] Broken links in entrypoints (README, docs/README, START_HERE, RUNBOOK_AGENT)
- [ ] Deploy/runbook commands that are wrong for current main
- [ ] Policy contradictions (AGENTS/RUNBOOK conflict)

---

## P1 — Should fix soon (quality + maintainability)

- [ ] Markdownlint cleanup (MD040 fenced code language, MD036 emphasis-as-heading, etc.)
- [ ] Normalize naming (UPPER_SNAKE_CASE) for new docs only (no mass renames unless planned)
- [ ] Cross-links updated after moves (internal anchors)

---

## P2 — Nice to have (low risk)

- [ ] Style/grammar (LanguageTool)
- [ ] Translation gaps (RU/EN/ES consistency)
- [ ] Old reports archived under docs/archive/YYYY-MM-DD/

---

## Tracking

- Prefer GitHub Issues for items that need ownership/date.
- This file is a staging area; migrate to issues when it becomes actionable.

---

## Notes

- **Do not** migrate "thousands of cosmetic issues" here.
- Write only what either **breaks navigation**, **misleads users**, or **creates policy drift**.
