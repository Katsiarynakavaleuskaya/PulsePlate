# Signal vs Noise Report Lane Premortem

Target PR: `docs(coaching): promote Signal vs Noise report lane after VIP identity loop`
Mode: `pr-premortem`
Packet: `artifacts/orchestration/task_packets/423d87f43f94.json`

## Frame

It is 6 months from now. This docs/governance lane failed because it created
confusing product truth for the CBT/FitChef wave. We are looking backward to
understand why.

## Summary

The lane reconciles the merged VIP Identity Loop Mapper runtime from PR #1870
and promotes Signal vs Noise as a weekly report/content lane.

Success means repo docs agree that PR #1870 is landed, Signal vs Noise remains
content/GTM only, and report promotion requires evidence, ownership, metrics,
check dates, and stop/continue rules.

## Findings And Dispositions

### 1. PR #1870 remains stale in repo truth

Failure story: The backlog keeps saying PR #1870 is open while API and contract
docs call the route current. Future agents cannot tell whether
`POST /api/v1/vip/fitchef/insight` is implemented or only planned, so they open
duplicate runtime work.

Disposition: FIXED
Evidence:
- `docs/roadmap/BACKLOG_LEDGER.md` marks PR #1870 landed via merge commit
  `7802ed25e99e0a4f346d14487270a037bb5ec97a`.
- `docs/contracts/API_CANONICAL_MAP.md` and
  `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` now state that the VIP
  Identity Loop Mapper route is implemented and OpenAPI-exposed.
- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md` reconciles the foundation
  contract to the same PR #1870 landed state.

### 2. Signal vs Noise becomes a hidden runtime lane

Failure story: A report/content idea is described as product capability. Later
implementation work adds routes, cache, GraphRAG, telemetry, frontend, or
automatic plan adaptation without the dedicated runtime gates.

Disposition: FIXED
Evidence:
- `docs/insights/SIGNAL_VS_NOISE_REPORT_LANE.md` defines the lane as
  report/content only and lists runtime, OpenAPI, DB, telemetry, frontend/iOS,
  Slack, billing, food-data, semantic cache, GraphRAG, and plan adaptation as
  out of scope.
- `docs/insights/CBT_COACHING_PRODUCT_WAVE.md` says Signal vs Noise report
  fields are GTM decision fields only unless a later reviewed runtime PR adds
  tested product telemetry.

### 3. External trend material becomes product truth

Failure story: Browser, Drive, PDF, or trend-report material is copied into
canonical docs as fact. Unsupported claims then become founder content or
product direction without source status, conflict checks, or validation plans.

Disposition: FIXED
Evidence:
- `docs/insights/SIGNAL_VS_NOISE_REPORT_LANE.md` requires source-register
  entries, claim type, support status, evidence mode, confidence, and validation
  plan before promotion.
- Unsupported or contradicted claims must be deferred or discarded.

### 4. Wellness boundary drifts into clinical framing

Failure story: Signal vs Noise copy positions CBT-inspired reflection as
therapy, treatment, diagnosis, crisis support, or medical advice. That creates
trust and compliance risk for a wellness-only product.

Disposition: FIXED
Evidence:
- `docs/insights/SIGNAL_VS_NOISE_REPORT_LANE.md` uses wellness, habit coaching,
  practical reflection, and small next step language and links the canonical
  wellness disclaimer without duplicating it.
- The lane explicitly forbids clinical, crisis, medical, diagnosis, treatment,
  and therapy claims.

## Decision

Proceed with changes. The coherent diff must still pass Experiment Runner
oracle review, changed-file validation, pre-commit, and post-open review gates
before readiness can be claimed.
