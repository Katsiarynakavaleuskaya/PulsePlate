# Figma Handoff Folder

Purpose: single Git folder for repo-native Figma handoff, reconciliation, and
evidence docs.
(RU: единая папка для repo-native инструкций, reconciliation-пакетов и evidence
доков для Figma-assisted работы.)

Current delivery model:

- repo code/docs/tests remain the source of truth
- Figma MCP, Make, internal bridge systems, web terminal, and Cursor terminal
  are auxiliary evidence tools only
- Code Connect is not required, not planned, and not gating for the current
  web/iOS reconciliation lane

Glossary:

- `repo-first lane` = the current web/iOS reconciliation lane governed by repo code/docs/tests, the authority packet, lane-specific reconciliation packets, inbox/checklist, and QA
- `historical Code Connect lane` = the earlier activation/mapping path kept only as historical/reference context for the current delivery model
- `reopened historical Code Connect lane` = a scoped exception where a future coordinator-owned packet explicitly says the historical Code Connect lane is active again for that task
- `canonical_execution` = the only execution lane for that surface
- `implementation_safe` = repo-subordinate visual/node reference only
- `reference_only` = comparison and provenance only
- `historical_reference_only` = prior blocker/audit evidence only
- `spec_index_only` = lookup/index surface only

## Start Here (Reading Order)

1. `docs/figma/README.md`
2. `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md`
3. `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
4. `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md`
5. `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md`
6. `docs/figma/FIGMA_GIT_PACKS_INDEX.md`
7. `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
8. `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
9. `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md`
10. `docs/figma/FIGMA_AI_INBOX_TEMPLATE.md`
11. `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`
12. `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
13. `docs/sora/BRAND_THROUGHPUT_METRICS_GTM_MATRIX.md`
14. `docs/figma/FIGMA_CLAWBOT_OPERATING_MODEL.md`
15. `docs/figma/SANDBOX_DESIGN_AGENT_SPEC.md`
16. `docs/figma/orchestration/README.md`
17. `docs/sora/prompts/hpp/MASTER_NANO_PROMPT_PACK.md`

Historical reference only for the current delivery model:

- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
- `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
- `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
- `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md`

## Files

- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
  - Full runbook for where to read Git context, refresh protocol,
    conflict resolution, and output contract.
- `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md`
  - Canonical cross-file packet for the current delivery model.
  - Locks web `v3`, iOS `v2`, Make, and spec/index authority and records the
    explicit Code Connect bypass policy.
- `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md`
  - Canonical file-specific reconciliation packet for `PulsePlate_v3` and the
    clean canonical Figma file used for `Foundations + Components + Welcome Gate`.
  - Defines source precedence, transfer contract, alignment matrix, blocker
    classes, clean-file page structure, and the advisory-only AI evidence policy.
- `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md`
  - Canonical iOS implementation-safe reconciliation packet for
    `AhyS6u4dZXMRHVUDO3Cfn6`.
  - Keeps iOS capture evidence repo-subordinate and separates it from web `v3`
    execution authority.
- `docs/figma/FIGMA_GIT_PACKS_INDEX.md`
  - Compact map: which project packs to read, when, and drift risk if skipped.
- `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
  - Governance guidance for Figma-assisted design work across Home + Plate + Progress.
  - Use as a reference index, not as product/runtime authority.
- `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
  - Make-vs-Git reconciliation audit with drift blocks, action queue, and
    supporting delta appendices used as evidence only.
  - `reference_only` for the current delivery model.
- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
  - `historical_reference_only` runbook for an out-of-scope Code Connect path.
- `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
  - `historical_reference_only` capture protocol from the earlier Code Connect lane.
- `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
  - `historical_reference_only` CTA mapping registry from the earlier Code Connect lane.
- `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md`
  - What to verify before sending and after receiving outputs.
- `docs/figma/FIGMA_AI_INBOX_TEMPLATE.md`
  - Template for adding new requests in a stable format.
- `docs/figma/FIGMA_CLAWBOT_OPERATING_MODEL.md`
  - Reference operating model for Make-vs-Design evidence capture and
    OpenClaw/Clawbat terminal workflow notes.
  - Not an authority source for the current delivery model.
- `docs/figma/SANDBOX_DESIGN_AGENT_SPEC.md`
  - P1 specification for sandbox design-agent contracts, safety gates, and DoD.
- `docs/figma/orchestration/README.md`
  - How to run Figma-focused multi-agent sessions with canonical constraints.
- `docs/sora/prompts/hpp/MASTER_NANO_PROMPT_PACK.md`
  - P2 prompt templates and controlled variations for Home/Plate/Progress assets.
- `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
  - Release-ready QA rubric (pass/fail) for prompt outputs.
- `docs/sora/BRAND_THROUGHPUT_METRICS_GTM_MATRIX.md`
  - Throughput measurement and GTM matrix for visual experiments.

## Recommended workflow

1. Refresh Git context using `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`.
2. Lock cross-file authority first with
   `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md`.
3. If the task is specifically about the clean web `v3`
   `Foundations + Components + Welcome Gate` execution lane, use
   `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md`.
4. If the task is specifically about the implementation-safe iOS `v2` lane,
   use `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md`.
5. Use `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md` and
   `docs/figma/FIGMA_CLAWBOT_OPERATING_MODEL.md` only as reference/evidence
   support. They do not define authority.
6. Add request via `docs/figma/FIGMA_AI_INBOX_TEMPLATE.md`.
7. Align request with `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`,
   treating Figma AI guidance as advisory only.
8. Validate output via `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md`.
9. Run QA pass/fail checks in `docs/sora/SORA_STYLE_QA_CHECKLIST.md`.
10. If session is complex, record decisions in
    `docs/figma/orchestration/sessions/`.

Code Connect is not part of the current recommended workflow for the
repo-first lane covered by this folder.
If a future task uses a reopened historical Code Connect lane under a
coordinator-owned packet, use the dedicated runbook and bridge docs for that
scoped task instead of treating this lane-scoped bypass as a repo-wide ban.

## Canonical project links

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`
- `docs/sora/PULSEPLATE_SORA_BUTTON_VARIANTS_HPP.md`
- `docs/design/PENPOT_STORYBOOK_BRIDGE.md`
