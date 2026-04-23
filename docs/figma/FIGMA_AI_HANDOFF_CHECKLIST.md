# Figma AI Handoff Checklist

## Before sending to Figma AI

- Scope is limited to Home/Plate/Progress or explicitly documented.
- Context refreshed via `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`.
- Git context snapshot is attached (context_version + changed packs).
- Make sync audit refreshed:
  `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`.
- Button IDs match matrix IDs from `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`.
- Brand lock is present: `#0F172A #339FFF #20C997 #FF5D5D(accent)`.
- Guardrail source:
  `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` (Section 8).
- Guardrails are included:
  no medical claims, no diagnostic framing, no copycat style.
- Requested states are explicit:
  default, interactive, disabled/locked, loading, error.

## After receiving from Figma AI

- Naming follows `PP/<Platform>/<Screen>/<Component>/<State>`.
- Visual output passes premium checklist:
  `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`.
- CTA hierarchy is clear and consistent (primary > secondary > utility).
- Accessibility baseline is preserved (contrast, focus, tap/click targets).
- For each CTA, handoff has `Exists/Missing/Implement Needed` note.
- Each touched CTA has a repo-native design review reference:
  Storybook story/MDX path and, when used, a Penpot page/frame reference.
- Optional Code Connect map status is recorded only when Code Connect is
  explicitly in scope:
  `candidate` / `blocked_by_design_url` / `blocked_by_node_id_capture` /
  `blocked_by_plan` / `stale` / `validated` / `active`.
- If optional status is `blocked_by_design_url` or `blocked_by_node_id_capture`,
  dependency tracking is updated via
  `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`.
- If optional status is `blocked_by_plan`, workspace-level blocker is recorded in
  `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md` and `docs/roadmap/BACKLOG_LEDGER.md`.
- If optional mapping is marked `active`, verification evidence from
  `get_code_connect_map` is attached.
- If conflicts were found, resolution is recorded in `docs/figma/orchestration/sessions/`.

## Handoff payload minimum

Canonical schema source:
`docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` (Section 9).

- `Button/CTA ID`
- `Screen + Platform`
- `Target state(s)`
- `Design Review Reference`
- `Prompt Stub ID`
- `Status` (`Implemented` / `Partial` / `Missing` / `Blocked by flag`)
- `Implement Needed`
- `context_version` (date + commit hash)

Optional only when Code Connect is part of the task:

- `Figma Node ID`
- `Code Connect Label` (`React` / `SwiftUI`)
- `Code Connect Map Status`
