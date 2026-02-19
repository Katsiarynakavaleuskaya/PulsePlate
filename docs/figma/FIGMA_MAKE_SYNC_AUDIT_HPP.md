<!-- markdownlint-disable MD013 -->
# Figma Make Sync Audit (H+P+Pr)

**Date:** February 18, 2026
**Scope:** Home + Plate + Progress (Web + iOS) and linked CTA flows
**Source mode:** Make-only (`MrztJU3CQtxhADBbtAsWJ6`) until Design URL is provided
**Context version:** 2026-02-18 / commit `162ad6ef`

## 1) Purpose

This audit reconciles current Figma Make updates with Git source-of-truth artifacts and records implementation blockers for Code Connect activation.

Primary SoT references:

- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `frontend/src/config/routes.ts:23`
- `frontend/src/pages/Home.tsx:34`
- `ios/PulsePlate/Views/HomeView.swift:57`

## 2) Baseline Snapshot (Evidence)

- Figma MCP auth confirms active Pro/Full seat (captured via MCP `whoami`).
- Active Make file pointer exists in backlog: `docs/roadmap/BACKLOG_LEDGER.md:1643`.
- Current Make file contains local docs + generated UI scaffolding and guideline pack (observed via MCP `get_design_context(fileKey=MrztJU3CQtxhADBbtAsWJ6, nodeId=0:1)`).
- Project CTA behavior SoT remains matrix-driven: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`.

## 3) Aligned

1. Scope lock is consistent with H+P+Pr governance.
Evidence: `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md:40`, `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md:5`
2. Naming contract is aligned to `PP/<Platform>/<Screen>/<Component>/<State>`.
Evidence: `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md:19`, `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md:74`
3. CTA registry list in governance matches matrix coverage expectations.
Evidence: `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md:139`, `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`
4. Safety framing remains wellness-first and no-diagnostic in canonical Git docs.
Evidence: `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md:129`, `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:317`

## 4) Conflicts

### 4.1 Palette Governance Conflict (Gold treatment)

- Make guideline snapshot includes Gold `#D4AF37` as canonical palette member.
- Git anti-drift references treat purple/gold drift as forbidden unless explicitly constrained to contextual accents.
Evidence: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:154`, `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:324`, `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md:63`

Risk: visual drift between Make-driven assets and in-product style lock.

### 4.2 Accessibility Target Size Conflict (Web)

- Make guideline snapshot references web minimum target of 44px.
- Project visual system lock for this stream sets web minimum to 48x48 CSS px.
Evidence: `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md:104`, `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md:111`

Risk: inconsistent component sizing and QA ambiguity for tap/click comfort.

### 4.3 Architecture Divergence (Make shell vs runtime site)

- Make `App.tsx` uses view toggles and localStorage bootstrap flow not present in canonical route/runtime architecture.
- Production web runtime uses route registry + auth wrappers + tab bar contract.
Evidence: `frontend/src/App.tsx:1`, `frontend/src/config/routes.ts:23`, `frontend/src/pages/Home.tsx:34`, `frontend/src/pages/Plate.tsx:37`

Risk: generated components map to non-canonical entry points.

## 5) Missing for Implementation

1. No Design file URL or node IDs for node-level Code Connect.
2. `Figma Node ID` still `TBD` across matrix rows.
Evidence: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`
3. No repository Code Connect mapping registry for 23 CTA IDs.
4. No status lifecycle tracking (`candidate -> validated -> active`) in current handoff contract.

## 6) Action Required

| Priority | Item | Owner | DoD | Target PR |
| --- | --- | --- | --- | --- |
| P0 | Resolve web target-size conflict (44 vs 48) by declaring one canonical value in figma docs and Make sync contracts | Coordinator + Accessibility | One value in all figma docs; conflict note closed in this audit | Docs PR (this stream) |
| P0 | Introduce Code Connect bridge runbook with blocker protocol for missing Design URL | Coordinator + FE | `FIGMA_CODE_CONNECT_BRIDGE_HPP.md` merged and linked from runbook/governance | Docs PR (this stream) |
| P1 | Create 23-CTA mapping candidate registry for existing site surfaces | FE + iOS + Design | Every CTA row has surface path, status, and gap note | Docs PR (this stream) |
| P1 | Add Code Connect map status requirement into handoff checklist | Coordinator | Checklist includes mapping status verification gates | Docs PR (this stream) |
| P2 | Activate node-level mappings after Design URL available | Design + FE + iOS | P0 CTA nodes mapped and verified with `get_code_connect_map` | Follow-up mapping PR |

## 7) Blockers

### Blocker B1 — Missing Design URL + node IDs

- Description: Code Connect activation cannot proceed past candidate stage without Design file key/node IDs.
- Tracking: add backlog dependency item in `docs/roadmap/BACKLOG_LEDGER.md`.
- Temporary mode: Make-only reconciliation + candidate mapping only.

## 8) Decision Log

- 2026-02-18: Locked source mode to Make-only until Design URL is provided.
- 2026-02-18: Locked integration direction to Code Connect bridge (not embed).
- 2026-02-18: Locked requirement that all 23 CTA IDs must be represented in mapping candidates.
<!-- markdownlint-enable MD013 -->
