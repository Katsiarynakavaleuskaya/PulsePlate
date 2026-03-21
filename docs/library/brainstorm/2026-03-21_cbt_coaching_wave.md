# Brainstorm: CBT Coaching Wave

Date: 2026-03-21
Coordinator: `agent-coordinator`
Status: promoted to docs-first SoT lane

## Routing Card

- Decision question:
  Which article ideas should become the next governed PulsePlate product wave without
  breaking the current FitChef/CBT canon or widening into regulated health/therapy?
- Success criteria:
  - pick one umbrella topic instead of a scattered idea list
  - preserve live `/api/v1/insight/fitchef*` canon
  - keep the wave wellness-only, non-clinical, and request-scoped
  - define measurable product hypotheses
  - split now vs later work into explicit follow-up lanes
- Constraints:
  - docs-first promotion in a dedicated worktree
  - no runtime route migration in this lane
  - no therapy/diagnosis/treatment framing
  - no new hidden memory or autonomous multi-tool behavior
- Primary agents:
  - `agent-coordinator`
  - `wellness-analyst-agent`
  - `cbt-psychologist-agent`
  - `ai-innovation-specialist`
  - `marketing-strategist`
  - `business-strategist-agent`
  - `data-scientist-agent`
- Advisory agents:
  - `architecture-specialist`
  - `philosophy-agent`
  - `logic-agent`
  - `qa-engineer-agent`
  - `bug-hunter`
- Tracks to run in parallel:
  - product scope and ethics
  - CBT taxonomy and safety
  - GTM/report lane
  - metrics and experiment design
- Formal reviewer(s):
  - `architecture-specialist`
  - `qa-engineer-agent`
  - `bug-hunter`

## Current repo state

- Existing CBT knowledge and distortion taxonomy already exist in:
  - `docs/cbt/cognitive_restructuring.md`
  - `docs/cbt/thought_records.md`
  - `docs/psychology/motivation_theories.md`
- Existing coaching runtime and live mascot routes already exist in:
  - `app/services/fitchef_runtime.py`
  - `app/routers/fitchef_insight.py`
  - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
- Existing future structured coach route family is already contract-frozen in:
  - `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
- Existing analytics and experiment governance already exist in:
  - `docs/analytics/METRICS_CATALOG.md`
  - `docs/analytics/EXPERIMENT_REGISTRY.md`
  - `docs/analytics/DASHBOARD_BASELINE_REQUIREMENTS.md`
  - `docs/analytics/EXPERIMENTATION_FRAMEWORK.md`

## Candidate ideas from the article

| Idea | Repo fit now | Decision |
| --- | --- | --- |
| Cognitive Distortions Simulator | Very high: directly extends CBT knowledge + structured coach surfaces | Promote now |
| Identity & Behavior Mapping | Very high: strong continuation of reflection/slip-support flows | Promote now |
| Signal vs Noise | High as content/GTM/research lane, weak as runtime lane | Promote now as report lane only |
| Build Your Own Framework | Very high: creates reusable FitChef/PulsePlate coaching IP | Promote now |
| Micro-SaaS in 7 Days | Useful only as delivery mindset for one narrow structured feature | Reframe, not a standalone product |
| Movement Intelligence Library | Interesting but creates a new data/product domain | Defer |
| Personal Experiment Dashboard | Valuable later, but analytics foundation exists already and user-facing layer is not the first bottleneck | Defer |
| Future-of/Redesign/Reverse-engineering essays | Useful for thought leadership, not first product wave | Defer |

## Synthesis

The repo already has enough foundation to justify one clear umbrella topic:

**PulsePlate CBT Coaching Wave**

This wave should stay:

- text-only
- request-scoped
- wellness-only
- additive to the live mascot canon
- measurable through the existing analytics framework

## Canonical decision

Promote these four pillars:

1. `Distortion Simulator`
2. `Identity Loop Mapper`
3. `Signal vs Noise Reports`
4. `FitChef Coaching Framework`

## Now vs later

### Do now

- promote one SoT document that explains the wave
- bind the wave to FitChef structured-coach contracts and tier map
- define coaching metrics and one umbrella experiment row
- add explicit backlog follow-ups for runtime and report lanes

### Do later

- PRO runtime for Distortion Simulator
- VIP runtime for Identity Loop Mapper
- report/content lane for Signal vs Noise
- any movement/performance-specific product expansion

## Promotion target

- Primary SoT target: `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
- Secondary targets:
  - `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
  - `docs/contracts/PRODUCT_TIER_MAP.md`
  - `docs/analytics/*`
  - `docs/roadmap/BACKLOG_LEDGER.md`
