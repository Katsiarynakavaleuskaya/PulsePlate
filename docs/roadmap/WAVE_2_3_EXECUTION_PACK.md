# Wave 2-3 Execution Pack (Day 31-180)

## Scope

Execution plan for:

- `wf2-contract-ci`
- `wf2-growth-experiments`
- `wf3-rag-safety-scale`

## Wave 2 (Day 31-90)

### 1) Contract Governance v2

Deliverables:

- OpenAPI diff classification (`breaking`, `risky`, `safe`)
- CDC checklist for backend/web/iOS changes
- Contract review checkpoint in PR process

KPIs:

- Contract-related rollback incidents = 0
- OpenAPI drift incidents detected pre-merge = 100%

### 2) CI Throughput and Flake Budget

Deliverables:

- CI critical-path baseline and target (minutes)
- Flake budget policy (owner + weekly burn-down)
- Retry policy only for known flaky classes with evidence

KPIs:

- Median CI time reduced against baseline
- Flaky failure rate trend down over 8 weeks

### 3) Growth Experimentation Framework

Deliverables:

- Feature-flagged experiment template
- Experiment registry lifecycle (planned -> running -> decision -> promoted)
- Guardrail metrics (retention/churn/cost) for every A/B test

KPIs:

- Time to decision per experiment reduced
- Experiment stop/go decisions documented with evidence

## Wave 3 (Day 91-180)

### 1) RAG/Agent Capability v2

Deliverables:

- Retrieval quality and rerank policy
- Citation contract for generated outputs
- Offline eval harness for precision/grounding checks

KPIs:

- Citation coverage target met on benchmark set
- Hallucination risk trend down release-over-release

### 2) Safety Evals at Scale

Deliverables:

- Red-team prompt suite (jailbreak/policy-bypass)
- Regression gate in CI for high-risk scenarios
- Incident playbook linkage to failing eval classes

KPIs:

- Pre-release high-severity safety failures = 0
- Mean remediation time for failed eval class reduced

### 3) Reliability Game Days

Deliverables:

- Scheduled drills for quota, rate-limit, DB fallback, tool outage
- Recovery runbook updates with evidence anchors

KPIs:

- MTTR during drills within target
- Actionable follow-ups tracked in ledger with owners

## Ownership Map

- Architecture + Backend: contract governance, RAG v2
- DevEx + QA: CI throughput, flake budget, reliability drills
- Product + Growth + Data: experimentation and conversion loops
- Security + AI: safety eval gate and incident readiness
