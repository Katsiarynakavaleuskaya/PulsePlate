# Figma AI Handoff Folder

Purpose: single Git folder for everything you pass to Figma AI.
(RU: единая папка для всех инструкций/индексов, которые передаются в Figma AI.)

## Start Here (Reading Order)

1. `docs/figma/README.md`
2. `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
3. `docs/figma/FIGMA_GIT_PACKS_INDEX.md`
4. `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
5. `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
6. `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
7. `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
8. `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
9. `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`
10. `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md`
11. `docs/figma/FIGMA_AI_INBOX_TEMPLATE.md`
12. `docs/figma/orchestration/README.md`

## Files

- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
  - Full runbook for where to read Git context, refresh protocol,
    conflict resolution, and output contract.
- `docs/figma/FIGMA_GIT_PACKS_INDEX.md`
  - Compact map: which project packs to read, when, and drift risk if skipped.
- `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
  - Main governance SoT for Home + Plate + Progress (Web + iOS).
  - Includes paste-ready rules block for Figma `guidelines/Guidelines.md`.
- `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
  - Make-vs-Git reconciliation audit with drift blocks and action queue.
- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
  - Canonical runbook for Code Connect bridge to existing site components.
- `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
  - Deterministic protocol to capture `figma.com/design` URL and P0 node IDs.
- `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
  - 23-row CTA mapping registry for candidate/blocked/active states.
- `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md`
  - What to verify before sending and after receiving outputs.
- `docs/figma/FIGMA_AI_INBOX_TEMPLATE.md`
  - Template for adding new requests in a stable format.
- `docs/figma/orchestration/README.md`
  - How to run Figma-focused multi-agent sessions with canonical constraints.

## Recommended workflow

1. Refresh Git context using `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`.
2. Reconcile Make updates with `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`.
3. Review bridge rules in `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`.
4. If Design URL/node IDs are missing, run
   `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`.
5. Update CTA map candidates in `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`.
6. Add request via `docs/figma/FIGMA_AI_INBOX_TEMPLATE.md`.
7. Align request with `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`.
8. Validate output via `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md`.
9. If session is complex, record decisions in `docs/figma/orchestration/sessions/`.

## Canonical project links

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`
- `docs/sora/PULSEPLATE_SORA_BUTTON_VARIANTS_HPP.md`
