# Figma AI Inbox Template

Use this template for each new request you plan to pass from Git to Figma AI.

## Request Meta

- Date:
- Owner:
- Stream/PR:
- Priority: P0 / P1 / P2

## Git Context Snapshot (Required)

- Context version (date + commit hash):
- Context refresh runbook used: `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- Changed packs snapshot:
- Affected CTA IDs from matrix:
- Affected token sources (web/iOS):

## Scope

- Platform: Web / iOS / Both
- Screen: Home / Plate / Progress / Linked flow
- Button/CTA ID(s):

## What to produce

- Component/frame names required:
- Required states:
  default / hover-pressed / focus / disabled / loading / error
- Figma page target:
  `00_Foundation_Tokens` / `01_Components` / `10_iOS_Home` /
  `11_iOS_Plate` / `12_iOS_Progress` / `20_Web_Parity`

## Guardrails (must include)

- Guardrail source:
  `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` (Section 8).
- Palette lock: `#0F172A #339FFF #20C997 #FF5D5D(accent)`
- Wellness-only tone (not medical/diagnostic)
- Anti-drift: no generic AI slop, no neon drift, no copycat style

## Prompt Stub Binding

- Stub ID:
  `ICON_STUB_V1` / `CTA_PRIMARY_STUB_V1` / `CTA_SECONDARY_STUB_V1` /
  `CTA_DISABLED_STUB_V1` / `CTA_LOADING_STUB_V1` / `CTA_ERROR_STUB_V1`
- Notes:

## Expected handoff output

- Canonical field schema:
  `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` (Section 9).
- Figma Node ID(s):
- Mapping to matrix row(s):
- Status (`Implemented` / `Partial` / `Missing` / `Blocked by flag`):
- Implement Needed column update:
- QA evidence link(s):

## Orchestration (if task is complex)

- Session path: `docs/figma/orchestration/sessions/<date>_<name>/`
- `context_version` recorded in `01_TASK_ANALYSIS.md`
- Final synthesis includes forced-decision marker if needed
