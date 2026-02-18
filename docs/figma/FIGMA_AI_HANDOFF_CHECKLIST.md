# Figma AI Handoff Checklist

## Before sending to Figma AI

- Scope is limited to Home/Plate/Progress or explicitly documented.
- Context refreshed via `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`.
- Git context snapshot is attached (context_version + changed packs).
- Button IDs match matrix IDs from `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`.
- Brand lock is present: `#0F172A #339FFF #20C997 #FF5D5D(accent)`.
- Guardrails are included: no medical claims, no diagnostic framing, no copycat style.
- Requested states are explicit: default, interactive, disabled/locked, loading, error.

## After receiving from Figma AI

- Naming follows `PP/<Platform>/<Screen>/<Component>/<State>`.
- Visual output passes premium checklist:
  `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`.
- CTA hierarchy is clear and consistent (primary > secondary > utility).
- Accessibility baseline is preserved (contrast, focus, tap/click targets).
- For each CTA, handoff has `Exists/Missing/Implement Needed` note.
- If conflicts were found, resolution is recorded in `docs/figma/orchestration/sessions/`.

## Handoff payload minimum

- `Button/CTA ID`
- `Screen + Platform`
- `Target state(s)`
- `Figma Node ID` (or `TBD`)
- `Prompt Stub ID`
- `Implement Needed`
- `context_version` (date + commit hash)
