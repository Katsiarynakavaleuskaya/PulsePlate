# PR-XXX — Orchestration P2: Domain hints (links-only)

## Scope
- Docs-only, dev-only (no runtime/infra/product changes).
- Files touched:
  - `docs/orchestration/task_analysis.template.md`
  - `docs/audit/PR_XXX_DOMAIN_HINTS_AUDIT.md`
- No new templates. No new thresholds/quality-gate numbers. No policy duplication.

## Problem (Why)
Task Analysis is intentionally universal, but this repo has hard domain invariants (BMI engine, OpenAPI
determinism/import hygiene, thin-client policy). Without a small “zone hint”, agents/contributors must
manually map “area touched → relevant invariants”, which increases drift risk.

## Proposal (What)
Add a tiny **Domain hints (pick if relevant)** section to `task_analysis.template.md`:
- One-line reminders keyed by high-signal repo areas (`core/bmi/*`, `app/routers/*`, `frontend/`, `ios/`)
- **Links only** to canonical docs (e.g., `AGENTS.md`, `RUNBOOK_AGENT.md`, `docs/BMI_CANONICAL_HANDOFF.md`,
  `frontend/AGENTS.md`, `ios/AGENTS.md`)

This is a UX affordance, not a new rule system: hints must remain short and non-prescriptive.

## Non-goals (Explicit)
- No “how to fix” guidance, no troubleshooting, no checklists with thresholds.
- No rewriting definitions (task/coordinator-first/quality gates remain canonical in `AGENTS.md`).
- No expansion into other templates in this PR.

## Risks & Mitigations
- **Risk: Turning hints into an encyclopedia** → **Mitigation:** hard cap: 3–4 bullets, 1–2 lines each.
- **Risk: Canon drift via restated rules** → **Mitigation:** links-only, no restated definitions.
- **Risk: Scope creep into workflow/templates** → **Mitigation:** change only `task_analysis.template.md`.

## DoD
- `make verify` is green.
- Domain hints exist and are links-only, minimal, and clearly optional (“pick if relevant”).
- No thresholds/quality-gate numbers added; no duplicated canon text.
