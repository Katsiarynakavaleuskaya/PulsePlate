<!-- markdownlint-disable MD013 -->
# Figma Implementation Runbook (Git Context, H+P+Pr)

**Date:** February 18, 2026
**Scope:** Home + Plate + Progress only (`H+P+Pr`), Web + iOS
**Language mode:** EN primary, RU notes for critical constraints

## 1) Purpose and Scope

This runbook tells Figma exactly where to read context in Git for implementation decisions,
how to refresh context, and how to avoid brand/design drift.

RU (critical): не расширять scope за пределы `Home + Plate + Progress` без явной задачи и записи в backlog.

## 2) Start Here (reading order)

Read in this order for every new Figma task:

1. `docs/figma/README.md`
2. `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
3. `docs/figma/FIGMA_GIT_PACKS_INDEX.md`
4. `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
5. `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
6. `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
7. `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
8. `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
9. `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
10. `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
11. `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
12. `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`

## 3) Git Packs to Read by Intent

### 3.1 Brand and visual rules

- `docs/design/`

Use when defining layout direction, hierarchy, quality level, accessibility, and premium visual tone.

### 3.2 Prompt safety and anti-drift

- `docs/sora/`

Use when generating prompt stubs, negative constraints, and style-lock clauses.

### 3.3 Figma handoff and execution operations

- `docs/figma/`

Use for runbooks, inbox contract, delivery checklist, and orchestration session artifacts.

### 3.4 Web token source of truth

- `frontend/src/styles/`
- `frontend/tailwind.config.ts`

Use for color/spacing/type/radius/shadow decisions on web parity frames.

### 3.5 iOS token source of truth

- `ios/PulsePlate/Assets.xcassets/`
- `ios/PulsePlate/Extensions/Color+Assets.swift`

Use for iOS color/material/state consistency.

### 3.6 Governance and rules

- `AGENTS.md`
- `frontend/AGENTS.md`
- `ios/AGENTS.md`

Use when conflicts appear or when acceptance criteria are unclear.

### 3.7 Code Connect and mapping bridge assets

- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
- `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
- `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`

Use when translating Figma nodes to existing site components and tracking map status.

## 4) Implementation Lookup Matrix

| Need | Read this first | Then validate against |
| --- | --- | --- |
| CTA behavior and states | `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md` | `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md` |
| Style and quality constraints | `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md` | `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md` |
| Prompt constraints and guardrails | `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md` | `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md` |
| Token values | `frontend/src/styles/tokens.css`, `frontend/src/styles/tokens.ts`, `ios/PulsePlate/Assets.xcassets/` | `ios/PulsePlate/Extensions/Color+Assets.swift` |
| Handoff payload requirements | `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md` | `docs/figma/FIGMA_AI_INBOX_TEMPLATE.md` |
| Make-vs-Git drift status | `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md` | `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md` |
| Need Design URL and node IDs for activation | `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md` | `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md` |
| Site connection via Code Connect | `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md` | `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md` |

## 5) Precedence Rules (Conflict Resolution)

If information conflicts:

1. CTA behavior: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md` is primary.
2. Visual quality: `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md` + `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md` are primary.
3. Prompt safety: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md` is primary.
4. Token values: code token sources are primary (`frontend/src/styles/*`, iOS assets and bridge).
5. Remaining conflict: follow `AGENTS.md` and record decision in `docs/figma/orchestration/sessions/...`.

## 6) Context Refresh Protocol

Run refresh before every Figma task, before PR review, and weekly.

### 6.1 Refresh commands

```bash
git diff --name-only origin/main...HEAD -- \
  docs/figma docs/design docs/sora \
  frontend/src/styles frontend/tailwind.config.ts \
  ios/PulsePlate/Assets.xcassets ios/PulsePlate/Extensions/Color+Assets.swift

git log --since="14 days ago" -- \
  docs/figma docs/design docs/sora \
  frontend/src/styles frontend/tailwind.config.ts \
  ios/PulsePlate/Assets.xcassets ios/PulsePlate/Extensions/Color+Assets.swift

rg -n "web.home|web.plate|web.progress|ios.home|ios.plate|ios.progress" \
  docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md
```

### 6.2 Refresh output contract

Attach this snapshot to request payload:

- `context_version`: date + commit hash
- changed files in tracked packs
- CTA rows impacted
- token files impacted (web/iOS)

### 6.3 Make sync loop (mandatory for current source mode)

When source mode is Make-only
(`docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`, `Source mode` field):

1. Run MCP `get_design_context` for Make file root:
   - Make file identifier from approved internal handoff (do not store raw key in repo docs)
   - `nodeId=0:1`
2. Review latest `guidelines/Guidelines.md`, `src/app/App.tsx`,
   `src/app/components/pp-button.tsx`, `src/styles/theme.css`.
3. Record findings in `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`.
4. Refresh CTA mapping status in
   `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`.

## 7) Hard Exclusions

- `docs/archive/**` is not source of truth.
- Ad-hoc notes without canonical links are advisory only.
- Out-of-scope files outside `H+P+Pr` are not used for implementation decisions in this stream.

## 8) Security and Safety

Use this canonical guardrail block in prompt-facing documents:

- no secrets, API keys, or internal URLs
- no medical claims
- no diagnostic framing
- no copycat style
- no manipulative fear/shame tone
- wellness-safe, trust-first language

All related docs under `docs/figma/` should reference this section instead of
creating alternative wording for the same rule set.

RU (critical): не включать в prompt служебные URL, токены или внутренние данные.

## 9) Output Contract for Figma

This is the canonical handoff schema for all Figma deliverables:

- `Button/CTA ID`
- `Platform`
- `Screen`
- `State set` (default, interactive, disabled/locked, loading, error)
- `Figma Node ID` (or `TBD`)
- `Prompt Stub ID`
- `Status` (`Implemented` / `Partial` / `Missing` / `Blocked by flag`)
- `Implement Needed`
- `context_version` (date + commit hash)

## 10) Orchestration Hook

Before any brainstorm session in `docs/figma/orchestration/`:

1. Run context refresh protocol first.
2. Capture `context_version` and changed-pack snapshot in session `01_TASK_ANALYSIS.md`.
3. Keep dialogue cap at 3 iterations (canonical orchestration rule).
4. Record final synthesis and forced-decision marker if needed.

## 11) Canonical References

- `docs/figma/FIGMA_GIT_PACKS_INDEX.md`
- `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
- `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
- `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
- `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `AGENTS.md`

## 12) Code Connect Bridge Flow (Activation)

Use this only when Design file URL/node IDs are available.

1. Validate candidate rows in `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`.
2. Run `get_code_connect_suggestions(fileKey, nodeId)`.
3. Confirm selected mappings via `send_code_connect_mappings(...)`.
4. If explicit mapping is needed, run `add_code_connect_map(...)`.
5. Verify via `get_code_connect_map(fileKey, nodeId)`.
6. Update `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`:
   set `Figma Node ID` cells and candidate status (`active`).
   If mapping affects CTA behavior surfaces, also sync corresponding
   `Figma Node ID` entries in
   `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`.

## 13) Blocker Protocol (No Design URL)

If Design URL/node IDs are missing:

1. Keep status `blocked_by_design_url` in candidate mapping table.
2. Do not fabricate file keys or node IDs.
3. Run `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md` to capture dependency.
4. Track blocker in `docs/roadmap/BACKLOG_LEDGER.md` with Owner/DoD/Target PR.
5. Continue Make sync audits and CTA mapping preparation until blocker closes.
<!-- markdownlint-enable MD013 -->
