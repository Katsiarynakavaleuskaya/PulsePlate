# PR-XXX — Priority Mapping (P0-A / P0-B / P1) — links-only

## Scope
- Docs-only, dev-only.
- Touch files:
  - `docs/orchestration/task_analysis.template.md`
  - `docs/audit/PR_XXX_PRIORITY_MAPPING_AUDIT.md`
- No runtime changes (`app/`, `core/`, `ios/`, `frontend/` untouched).
- No new definitions, thresholds, or examples.

## Problem
Task Analysis captures technical priority (P0/P1/P2), but does not explicitly map tasks to the existing
business/release readiness tracks (P0-A / P0-B / P1) defined canonically elsewhere. This can obscure
whether a task unblocks product correctness, release readiness, or is purely incremental.

## Proposal
Add a single, links-only field to the Task Analysis template:
- **Priority track (P0-A / P0-B / P1)**
- Link to the canonical definition (do not re-define meanings inside the template)

## Non-goals
- Do not explain what P0-A / P0-B / P1 mean in the template.
- Do not change workflow or other orchestration templates.
- Do not introduce numeric gates or release criteria here.

## DoD
- Exactly one new field added to `docs/orchestration/task_analysis.template.md`.
- Field is links-only (no definitions, no examples).
- `pre-commit run --all-files` and `make verify` are green.
