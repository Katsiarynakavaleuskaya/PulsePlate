# Design Runtime System Web+iOS PR-1 Missing Governed Primitives Packet

**Version:** 2026-04-23 (`America/New_York`)
**Branch:** `codex/design-missing-primitives-v1`
**PR:** `TBD (draft pending push)`
**Title:** `feat(frontend): add missing governed UI primitives v1`

## Summary

This packet is the branch-scoped field contract for `PR-1` of the design
runtime system web+iOS epic line.

`PR-0` already merged the series runbook and the coordinator-owned bootstrap
contract. This slice is the first executable runtime step: add the missing
governed web primitives from the canonical vocabulary without widening into
tokens expansion, iOS adoption, specialized-family normalization, or product
shell convergence.

Evidence:
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR0_BOOTSTRAP_PACKET_2026-04-22.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/ui_component_vocabulary.json`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`

## Scope

### IN
- add governed web primitives for:
  - `select`
  - `textarea`
  - `checkbox`
  - `radio-group`
  - `alert`
  - `dropdown-menu`
  - `tabs`
  - `tooltip`
- add colocated Storybook stories and targeted Vitest coverage for the new
  primitives
- surface the new primitives through the existing Storybook-first design-system
  overview/review lane
- keep implementation token-backed and aligned with the canonical UI vocabulary

### OUT
- `/tokens` authoring or generated token mirror changes
- iOS runtime or simulator work
- specialized family normalization for `badge`, `progress`, `hero`,
  `stats-card`, or `stepper/progress-indicator`
- product-shell convergence on `Home`, `Plate`, `Progress`, `Weekly Plan`,
  `Profile`, or `Paywall`
- backend, OpenAPI, billing, entitlement, provider, or deploy changes
- `figma-manifest` hardening or Figma mutation authority

## Files

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR1_MISSING_GOVERNED_PRIMITIVES_PACKET_2026-04-23.md`
- `docs/orchestration/AGENTS.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `frontend/src/components/ui/**`
- `frontend/src/components/design-system/**`
- `docs/review/PR_<N>_FIXED_MAPPING.md`

## Role Order

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. reviewer `architecture-specialist`
6. post-open mandatory `qa-engineer-agent -> bug-hunter`

This order is fixed for the lane unless a later packet explicitly updates it.

## Implementation Contract

- `select` stays a semantic native `<select>` in this slice; no combobox or
  searchable menu contract is introduced.
- `textarea` aligns with the current input/form-field token contract and stays
  multiline-only.
- `checkbox` and `radio-group` preserve semantic input/fieldset structure and
  keyboard accessibility.
- `alert` is an inline status/banner surface, not a modal/system confirmation.
- `dropdown-menu` and `tabs` reuse the existing `@headlessui/react` dependency.
- `tooltip` stays short, non-interactive, and supportive only; it must not hide
  critical instructions.
- Storybook remains review-only; it does not become an authoring lane.

## Evidence Rules

- Web evidence for this slice is Storybook-first plus targeted component tests.
- Product routes remain downstream consumers only and are not review canon for
  `PR-1`.
- iOS is out of scope for this slice.
- Figma remains secondary/read-only for this lane; no Figma metadata activation
  is required for `PR-1`.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `cd frontend && npm run build`
- targeted Vitest coverage for the new primitives
- targeted accessibility assertions through the existing `jest-axe` harness
- `make verify` before any merge-ready claim on the latest head

## Bootstrap Path Drift

The merged docs still reference `scripts/orchestration/task_bootstrap.py`, but
that file is absent on the current `main` head. This slice records the drift as
documentation-only evidence and uses the live replacement seam
`scripts/orchestration/route_with_telemetry.py` together with the merged
runbook/packet contract for coordinator routing. `PR-1` must not widen into a
bootstrap-framework repair; any repo-wide reconciliation of stale
`task_bootstrap.py` references belongs in a separate follow-up lane.

## DoD

- all eight missing governed primitives exist in `frontend/src/components/ui/`
- the new primitives are exported from the shared UI barrel
- stories exist for every new primitive and are visible through the current
  design-system review lane
- targeted tests cover semantic behavior and keyboard/a11y-critical states
- the slice introduces no token-authoring, iOS, or product-shell ownership
  drift
- the lane remains coordinator-owned and current-head merge governance can be
  applied without revising packet scope
