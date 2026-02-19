<!-- markdownlint-disable MD013 -->
# Figma Git Packs Index (Where to Read Context)

| Pack path | What Figma gets from it | When to read | Priority (P0/P1/P2) | Owner lane (Creative/Sora/FE/iOS/Coordinator) | Drift risk if skipped |
| --- | --- | --- | --- | --- | --- |
| `docs/figma/` | Operational handoff contracts, runbook, inbox/checklist, orchestration session evidence | Every task start and handoff | P0 | Coordinator | High: missing operational consistency |
| `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md` | Reconciled Make-vs-Git drift findings and required actions | Before every Figma sync cycle | P1 | Coordinator | Medium: hidden drift and inconsistent assumptions |
| `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md` | Code Connect activation flow, lifecycle, blocker protocol | Before any site-connection attempt | P1 | FE/iOS/Coordinator | High: incorrect mapping activation steps |
| `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md` | Exact protocol to capture `figma.com/design` URL and P0 node IDs | When status is `blocked_by_design_url` | P1 | Coordinator/Design | High: activation blocked indefinitely |
| `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md` | 23 CTA mapping readiness table for existing site surfaces | During mapping prep and activation | P1 | FE/iOS | High: missing CTA-to-component traceability |
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
| `docs/archive/` | Historical context only, never current SoT | Only when tracing historical rationale | P2 | Coordinator | Low for current implementation, high if mistaken for SoT |
<!-- markdownlint-enable MD013 -->
