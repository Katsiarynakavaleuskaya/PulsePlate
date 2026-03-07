# ADR: Penpot + Storybook Fallback Bridge Seam (2026-03-07)

- Status: Accepted (temporary seam)
- Date: 2026-03-07
- Owner: @katsiaryna_kavaleuskaya

## Context

PulsePlate already has repo-native review sources of truth for web UI:

- `frontend/.storybook/` (`frontend/.storybook/main.ts:4`)
- `frontend/src/styles/tokens.css` (`frontend/src/styles/tokens.css:8`)
- `frontend/src/styles/tokens.ts` (`frontend/src/styles/tokens.ts:12`)
- CTA behavior contracts in `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
  (`docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`)

Figma Code Connect is currently non-canonical for this workflow because the
workspace is blocked by plan/seat and the critical CTA node captures are still
incomplete or stale. Review and handoff still need a low-cost design surface
that does not replace repo truth or delay web delivery (`docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:3`, `docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:6`, `docs/roadmap/BACKLOG_LEDGER.md:2996`, `docs/roadmap/BACKLOG_LEDGER.md:3023`).

## Decision

Use a temporary `Penpot + Storybook` bridge seam for design review and handoff:

1. Storybook remains the canonical web review surface.
   (`frontend/.storybook/main.ts:4`, `frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx:7`)
2. Repo tokens remain the canonical runtime style source.
   (`frontend/src/styles/tokens.css:8`, `frontend/src/styles/tokens.ts:12`)
3. Penpot is allowed only as an optional inspect/layout/reference layer.
   (`docs/design/PENPOT_STORYBOOK_BRIDGE.md:76`)
4. Code Connect stays optional and non-blocking until the activation blockers
   are cleared (`docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md:24`,
   `docs/roadmap/BACKLOG_LEDGER.md:2996`, `docs/roadmap/BACKLOG_LEDGER.md:3023`).

## Exit Criteria

Remove the fallback seam only when ALL are true:

1. `get_code_connect_suggestions(...)` is no longer blocked by plan/seat.
   (`docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:6`)
2. Current CTA node IDs are re-captured under
   `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
   (`docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:107`).
3. Critical mapping rows advance out of `blocked_by_node_id_capture`,
   `blocked_by_plan`, and `stale`
   (`docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md:65`,
   `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md:69`).
4. `get_code_connect_map(...)` returns expected active mappings for the pilot
   CTA set (`docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md:68`).
5. `Design Review Reference` backfill is complete for the active handoff rows.
   (`docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:61`)

## Backlog Links (SoT)

- `docs/roadmap/BACKLOG_LEDGER.md`:
  - `Penpot + Storybook fallback bridge for design handoff`
    (`docs/roadmap/BACKLOG_LEDGER.md:3023`)
  - `Design file URL + node IDs required for Code Connect activation (H+P+Pr)`
    (`docs/roadmap/BACKLOG_LEDGER.md:2996`)

## Consequences

- Positive: design review can continue without Organization/Enterprise upgrade.
- Positive: repo-native Storybook/tokens stay authoritative.
- Negative: Penpot is an explicit temporary seam and adds one more docs surface
  that must be retired when Code Connect becomes activation-ready.
