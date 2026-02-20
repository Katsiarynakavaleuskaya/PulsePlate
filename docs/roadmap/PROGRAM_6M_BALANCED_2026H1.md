# PulsePlate 6-Month Balanced Program (2026 H1)

## Goal

Deliver a balanced 6-month program across:

- Platform security and reliability
- Product growth and monetization
- Maintainability and modernization

## Strategic Direction

- Keep `OpenClaw` decommissioned.
- Build a vendor-independent Agent Control Plane over the existing stack (`FastAPI` + `web` + `iOS` + `MCP` adapters).
- Use policy-first automation: no privileged execution without policy checks and signed audit.

## Wave Plan

### Wave 1 (Day 0-30): Control and Visibility

Primary outcomes:

- Agent Control Plane MVP with deny-by-default policy gate
- Security hardening baseline (short-lived secrets, rotation playbooks)
- Growth telemetry canon and KPI dashboard spec

Delivery artifacts:

- `docs/architecture/ADR-003-agent-control-plane-mvp.md`
- `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
- `docs/analytics/ANALYTICS_INDEX.md`
- `docs/analytics/METRICS_CATALOG.md`
- `docs/analytics/EXPERIMENT_REGISTRY.md`

### Wave 2 (Day 31-90): Stabilization and Productization

Primary outcomes:

- Contract governance v2 for backend/web/iOS compatibility
- CI throughput and flake budget program
- Experimentation framework for onboarding/paywall conversion
- LLM/API cost governance rollout

Delivery artifacts:

- `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
- `docs/analytics/EXPERIMENT_REGISTRY.md`
- `docs/roadmap/BACKLOG_LEDGER.md` (tracked owner/DoD/target PR entries)

### Wave 3 (Day 91-180): Scale and Moat

Primary outcomes:

- RAG/Agent capability v2 with safety eval gates
- Reliability game days for degraded-mode confidence
- ASO/SEO + lifecycle growth scale-up

Delivery artifacts:

- `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- Guard/eval test rollout plan in `tests/` ownership tracks

## Priority Backlog Bands

- P0: Agent Control Plane MVP, security baseline, telemetry canon
- P1: Contract governance, CI throughput, experimentation, cost governance
- P2: RAG v2, large-scale safety evaluation, growth scale-up optimization

## KPI Targets (Program-level)

- Security: 100% privileged agent actions pass policy gate
- Reliability: p95/p99 and error budget tracked for key routes
- Delivery: reduced CI critical path and flaky test rate
- Growth: improved trial-to-paid and D30/D90 retention
- Cost: stable LLM cost per active user with anomaly alerts

## Governance

- Every initiative ships as scoped PR packets with DoD, rollback, and test plan.
- Deferred work is recorded only in `docs/roadmap/BACKLOG_LEDGER.md`.
- Merge readiness uses canonical quality gates (`make verify`, guard suites, pre-commit).
