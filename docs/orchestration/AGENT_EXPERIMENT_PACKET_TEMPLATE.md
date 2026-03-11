# Agent Experiment Packet Template

<!-- markdownlint-disable MD013 -->

Use this template for governed experiment charters and result packets.

Canonical protocol: `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`

---

## Experiment Header

- **Experiment ID:** `EXP-TBD`
- **Stage:** `charter` | `candidate_run` | `result`
- **Owner:** `@owner`
- **Primary agent:** `agent-coordinator`
- **Reviewer:** `architecture-specialist`
- **Related PR / backlog:** `PR-TBD` / `docs/roadmap/BACKLOG_LEDGER.md`

## Decision Question

One sentence describing the optimization or evaluation question.

## Candidate Mutable Surface

- Allowed paths:
  - `path/one`
  - `path/two`
- Forbidden paths for this cycle:
  - `path/immutable/oracle`
  - `path/policy/or/contracts`

## Immutable Oracle List

- Oracle 1:
  - command: `...`
  - expected signal: `...`
- Oracle 2:
  - command: `...`
  - expected signal: `...`

## Budgets and Stop Conditions

- Wall-clock budget:
- Retry budget:
- Max changed files:
- Provider/network budget:
- Benchmark/test budget:
- Stop condition:

## Metrics

- Primary metric:
- Baseline:
- Acceptance threshold:
- Secondary metrics:

## Negative Controls

- Negative control 1:
- Negative control 2:

## Result Summary

- Outcome: `promote` | `discard` | `defer`
- Metric delta:
- Failure class:
- Notes:

## Promotion Target

Choose exactly one:

- PR packet / implementation PR
- audit artifact
- guard/test proposal
- backlog entry
- memory capsule

## Evidence

- Commands run:
- Raw output summary:
- File references:

## Deferred Follow-up Block

- Backlog item:
- Owner:
- Priority:
- Reason for deferral:
- Relevant links:
- Target PR:
- DoD:

---

## Creative Research Extension (`task_class=creative_research`)

- **Phase:** `divergence` | `convergence` | `verification`
- **Valid output class:** `mechanistic_hypothesis` | `experimental_proposal` | `anomaly_explanation_candidate` | `creative_ideation`

### Hypothesis Contract

- `claim`:
- `mechanism`:
- `evidence_needed`:
- `falsifier`:
- `confidence`:
- `known_risks`:
- `wellness_boundary`:
- `promotion_decision`:

### Scorecard Contract

- `originality`:
- `flexibility`:
- `mechanism_specificity`:
- `groundedness`:
- `falsifiability`:
- `wellness_safety`:
- `hallucination_risk`:
- `promotion_decision`:

### Next PR Packet

- `next_pr_scope`:
- `candidate_paths`:
- `required_tests`:
- `required_docs`:
- `quality_gates`:
- `human_review_required`:
