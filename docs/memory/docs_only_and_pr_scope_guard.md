# Memory Capsule: Docs-only PR rule + PR scope guard

**Topic:** Keeping documentation PRs safe and reviewable
**Type:** Hard rules + commands
**Last updated:** 8 February 2026

---

## What

A docs-only PR is strictly limited to documentation files and must not change runtime behavior, CI, or configuration.

This is enforced by policy and an early CI scope guard.

---

## Why

Docs PRs should be:

- low-risk (no runtime regressions)
- fast to review
- deterministic in CI

Mixing runtime/config/code into docs PRs repeatedly caused failures and accidental behavior changes.

---

## Invariants (SoT)

- CI PR scope guard overview: `AGENTS.md:279`
- Docs-only PR Rule (mandatory): `AGENTS.md:744`, `AGENTS.md:746`
- Forbidden in docs-only PRs: `AGENTS.md:757`, `AGENTS.md:758`, `AGENTS.md:760`
- Special note (do not touch `legacy_app.py` in docs-only): `AGENTS.md:776`, `AGENTS.md:778`

---

## Commands (before push)

- Docs-only enforcement check (must be empty output):

```bash
git diff --name-only origin/main...HEAD \
  | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$"
```

---

## Links (canonical)

- `AGENTS.md` → “Docs-only PR Rule (Mandatory)”
- `docs/policy/PR_SCOPE_RULES.md`
- `docs/policy/PR_SCOPE_GUARD_CI_SETUP.md`
