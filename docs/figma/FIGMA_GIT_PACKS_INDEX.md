<!-- markdownlint-disable MD013 -->
# Figma Git Packs Index (Where to Read Context)

| Pack path | What Figma gets from it | When to read | Priority (P0/P1/P2) | Owner lane (Creative/Sora/FE/iOS/Coordinator) | Drift risk if skipped |
| --- | --- | --- | --- | --- | --- |
| `docs/figma/README.md` | Current repo-first delivery model and lane reading order | Every task start | P0 | Coordinator | High: wrong lane assumptions from the first step |
| `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` | Authority lock, source precedence, explicit Code Connect bypass | Every task start before tooling choices | P0 | Coordinator | High: split authority and accidental tool promotion |
| `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` | Active context refresh, handoff, QA path, and current repo-first workflow | Every active task and every handoff | P0 | Coordinator | High: stale execution flow and weak handoff discipline |
| `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md` | File-specific execution lane and transfer contract for clean web `v3` | When the task targets `PulsePlate_v3` or clean design-system execution | P0 | FE/Coordinator | High: wrong file authority or wrong clean-file assumptions |
| `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md` | Implementation-safe reconciliation packet for the current iOS `v2` lane | When the task targets the iOS implementation-safe surface | P0 | iOS/Coordinator | High: missing iOS lane boundaries and wrong authority assumptions |
| `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md` | Make-vs-Git drift findings and reference evidence for the current lane | Before reconciling Make output or citing design drift | P1 | Coordinator | Medium: hidden drift or stale reference evidence |
| `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md` | Stable request/handoff verification fields | Before sending requests and before accepting outputs | P0 | Coordinator | High: incomplete handoff payloads and unverifiable outputs |
| `docs/figma/FIGMA_AI_INBOX_TEMPLATE.md` | Repo-first request intake structure | When creating or updating a design request | P0 | Coordinator | Medium: ad-hoc requests and inconsistent evidence capture |
| `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md` | Button IDs, CTA behavior, status, missing/implement-needed fields | Any CTA/frame/button work | P0 | Creative | High: wrong flows and wrong CTA states |
| `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` | Variant system (V1/V2/V3), placement zones, trend/forecast rationale, per-CTA visual mapping | Button styling, prompt generation, visual QA alignment | P1 | Creative/Sora | Medium: inconsistent variants and weak trend justification |
| `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md` | Visual DNA, accessibility and anti-drift rules | Any style/layout decision | P0 | Creative | High: brand drift and inconsistent quality |
| `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md` | Pass/fail quality gate before acceptance | Before sign-off | P0 | Coordinator | High: no deterministic quality gate |
| `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md` | Prompt style lock, negative guardrails, anti-drift constraints | Any prompt stub or visual generation step | P0 | Sora | High: unsafe or off-brand prompts |
| `frontend/src/styles/tokens.css` | Web semantic tokens and CSS variables | Web parity and component state styling | P0 | FE | High: ad-hoc colors/spacing |
| `frontend/src/styles/tokens.ts` | Typed web token map for design decisions | Web parity and implementation alignment | P0 | FE | High: token mismatch between design/code |
| `ios/PulsePlate/Assets.xcassets/` | iOS color assets and platform palette mapping | iOS visual decisions | P0 | iOS | High: iOS color inconsistency |
| `ios/PulsePlate/Extensions/Color+Assets.swift` | Runtime bridge from semantic names to iOS colors | iOS state and semantic color mapping | P0 | iOS | High: wrong semantic color behavior |
| `frontend/tailwind.config.ts` | Tailwind mapping to token aliases | Web class-level style parity checks | P1 | FE | Medium: partial style divergence |
| `AGENTS.md` | Global policy, invariants, conflict resolution | When conflict or ambiguity appears | P1 | Coordinator | Medium: policy drift |
| `frontend/AGENTS.md` | Frontend scope constraints and thin-client policy | Web-focused tasks | P1 | FE | Medium: implementation mismatch |
| `ios/AGENTS.md` | iOS scope constraints and thin-client policy | iOS-focused tasks | P1 | iOS | Medium: implementation mismatch |
| `docs/orchestration/workflow.md` | Canonical pre-flight and orchestration lifecycle | Multi-agent sessions and synchronization | P1 | Coordinator | Medium: unstable process execution |
| `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md` | 3-iteration dialogue cap rules | Brainstorm sessions | P1 | Coordinator | Medium: endless discussions |
| `docs/figma/FIGMA_CLAWBOT_OPERATING_MODEL.md` | Auxiliary tooling/evidence notes for Make-vs-design capture workflows | Only after the core repo-first docs are already fixed for the task | P2 | Coordinator | Low for the current lane; high only if mistaken for current authority |
| `docs/figma/SANDBOX_DESIGN_AGENT_SPEC.md` | Auxiliary sandbox-agent constraints for optional design-agent experimentation | Only after the core repo-first docs are already fixed for the task | P2 | Coordinator | Low for the current lane; high only if mistaken for current authority |
| `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md` | Historical Code Connect activation flow and blocker history for the old lane | Only when a future coordinator-owned packet explicitly reopens the historical Code Connect path | P2 | Coordinator | Low for the current lane; high only if the historical lane is reopened |
| `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md` | Historical Design URL/node-ID capture protocol | Only when a future coordinator-owned packet explicitly reopens the historical Code Connect path | P2 | Coordinator/Design | Low for the current lane; high only if the historical lane is reopened |
| `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md` | Historical CTA mapping registry from the old activation lane | Only when a future coordinator-owned packet explicitly reopens the historical Code Connect path | P2 | FE/iOS | Low for the current lane; high only if the historical lane is reopened |
| `docs/archive/` | Historical context only, never current SoT | Only when tracing historical rationale | P2 | Coordinator | Low for current implementation, high if mistaken for SoT |
<!-- markdownlint-enable MD013 -->
