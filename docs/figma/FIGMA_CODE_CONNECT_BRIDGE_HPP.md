<!-- markdownlint-disable MD013 -->
# Figma Code Connect Bridge Runbook (H+P+Pr)

**Date:** February 18, 2026
**Scope:** Bridge Figma to existing PulsePlate site for H+P+Pr CTA surfaces
**Mode:** Make-first reconciliation + Design-file activation when URL is available

## 1) Purpose

Define a deterministic, secure, and conflict-safe flow for connecting Figma components to real frontend/iOS code via Code Connect.

## 2) Preconditions

1. Figma MCP authenticated (`whoami` success).
2. Canonical behavior/style/prompt SoT reviewed:
   - `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
   - `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
   - `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
   - `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
3. Mapping candidates prepared in:
   - `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
4. Design file key + node IDs available for activation
   (capture protocol: `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`).

## 3) Canonical Tool Flow

### 3.1 Candidate stage (no Design URL)

- Build mapping candidates only (status `blocked_by_design_url`).
- Do not attempt final Code Connect submission.
- Do not use Make file key as Design key surrogate.

### 3.2 Activation stage (Design URL available)

1. Use `get_code_connect_suggestions(fileKey, nodeId)`.
2. Review with candidate registry and send approved mappings via `send_code_connect_mappings(...)`.
3. If direct explicit map needed, use `add_code_connect_map(...)`.
4. Verify result via `get_code_connect_map(fileKey, nodeId)`.
5. Reflect mapping status in docs and matrix `Figma Node ID` fields.

## 4) Label Policy

- Web mapping label: `React` (required for current site bridge).
- iOS mapping label: reserve `SwiftUI` lane (activation after Design nodes are available).
- Do not mix web/iOS labels on one mapping record.

## 5) Mapping Lifecycle

| Status | Meaning | Exit Criteria |
| --- | --- | --- |
| `candidate` | Proposed map exists in registry | Ready for node-level validation |
| `blocked_by_design_url` | No design file key/node ID yet | Design URL and node IDs provided |
| `validated` | Node-level match confirmed in Figma + site component | Passed consistency review |
| `active` | Code Connect map persisted and verified | `get_code_connect_map` returns expected map |
| `stale` | Component API or design changed, map requires refresh | Re-validated and re-activated |

## 6) Conflict Precedence (Non-negotiable)

1. CTA behavior: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
2. Visual quality: `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md` + `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
3. Prompt safety: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
4. Token SoT: `frontend/src/styles/tokens.css`, `frontend/src/styles/tokens.ts`, `ios/PulsePlate/Assets.xcassets/`, `ios/PulsePlate/Extensions/Color+Assets.swift`
5. Global policy: `AGENTS.md` + scoped AGENTS docs

If unresolved, record decision in:
`docs/figma/orchestration/sessions/<date>_figma_sync_hpp/03_SYNTHESIS_DECISION.md`

## 7) Security Rules

- No secrets, API keys, internal URLs, or private identifiers in mapping payloads or prompts.
- No medical claims/diagnostic framing in prompts attached to mapping records.
- Keep anti-copycat and anti-drift constraints active.
- Do not map to experimental non-canonical components that bypass existing route/auth contracts.

## 8) Blocker Protocol

### B1: Design file URL/node IDs missing

- Record blocker in backlog with Owner/DoD/Target PR.
- Keep all rows in candidate registry as `blocked_by_design_url`.
- Continue Make sync audits and CTA readiness updates without fake node IDs.
- Run capture protocol:
  `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`.

### B2: Component mismatch

- Mark row `stale`.
- Add refactor note in mapping candidates file.
- Resolve in runtime PR before re-activation.

## 9) Evidence Contract

Every activated mapping must include:

- `Button/CTA ID`
- `fileKey`
- `nodeId`
- `codeConnectName`
- `codeConnectSrc`
- `label`
- verification timestamp + commit hash

Store evidence links in:
`docs/figma/orchestration/sessions/<date>_figma_sync_hpp/04_DOD_CHECK.md`

## 10) Acceptance Criteria

1. All 23 CTA IDs exist in candidate registry.
2. No row has empty `Existing Site Surface` or `Gap/Refactor Needed`.
3. Blocker handling is explicit; no placeholder fake node IDs.
4. Activation flow is decision-complete and tool-specific.
<!-- markdownlint-enable MD013 -->
