# ADR: Penpot + Storybook Fallback Bridge Seam (2026-03-07)

- Status: Accepted (temporary seam)
- Date: 2026-03-07
- Owner: @katsiaryna_kavaleuskaya

## Context

PulsePlate already has repo-native review sources of truth for web UI:

- `frontend/.storybook/`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/tokens.ts`
- CTA behavior contracts in `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`

Figma Code Connect is currently non-canonical for this workflow because the
workspace is blocked by plan/seat and the critical CTA node captures are still
incomplete or stale. Review and handoff still need a low-cost design surface
that does not replace repo truth or delay web delivery.

## Decision

Use a temporary `Penpot + Storybook` bridge seam for design review and handoff:

1. Storybook remains the canonical web review surface.
2. Repo tokens remain the canonical runtime style source.
3. Penpot is allowed only as an optional inspect/layout/reference layer.
4. Code Connect stays optional and non-blocking until the activation blockers
   are cleared.

## Exit Criteria

Remove the fallback seam only when ALL are true:

1. `get_code_connect_suggestions(...)` is no longer blocked by plan/seat.
2. Current CTA node IDs are re-captured under
   `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`.
3. Critical mapping rows advance out of `blocked_by_node_id_capture`,
   `blocked_by_plan`, and `stale`.
4. `get_code_connect_map(...)` returns expected active mappings for the pilot
   CTA set.
5. `Design Review Reference` backfill is complete for the active handoff rows.

## Backlog Links (SoT)

- `docs/roadmap/BACKLOG_LEDGER.md`:
  - `Penpot + Storybook fallback bridge for design handoff`
  - `Design file URL + node IDs required for Code Connect activation (H+P+Pr)`

## Consequences

- Positive: design review can continue without Organization/Enterprise upgrade.
- Positive: repo-native Storybook/tokens stay authoritative.
- Negative: Penpot is an explicit temporary seam and adds one more docs surface
  that must be retired when Code Connect becomes activation-ready.
