# Agent Experimentation Protocol (Governed, bounded, KPP-only)

<!-- markdownlint-disable MD013 -->

**Purpose:** Define the canonical, dev-only workflow for fixed-budget agent experimentation loops.

**Status:** Canonical (PR1 governance foundation). No runtime impact.

**Hard rule:** This protocol governs experimentation loops only. It does not authorize autonomous runtime changes, autonomous merges, or hidden memory.

---

## Canonical references (single source of truth)

- Coordinator-first workflow: `docs/orchestration/workflow.md`
- Context loading: `docs/orchestration/AGENT_CONTEXT_MAP.md`
- Skill selection: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- Reflection and KPP promotion: `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
- Canonical memory policy: `docs/memory/kpp_knowledge_promotion_pipeline.md`
- Quality gates and repo hard rules: `AGENTS.md`
- Operational checks: `RUNBOOK_AGENT.md`

This file is the single source of truth for:

- mutable vs immutable experimentation surfaces,
- inner-loop budgets,
- candidate-loop lifecycle,
- experiment failure classes,
- promotion boundaries for experiment results.

Other docs must link here instead of restating these rules.

---

## 1. Scope and non-goals

### In scope

- Dev-only agent experimentation loops for bounded optimization or evaluation tasks.
- Fixed-budget candidate runs against immutable evaluation oracles.
- Experiment charters, result packets, and KPP-compliant promotion decisions.
- First-wave experimentation for `LLM/RAG reliability`, then later `CV` evaluation and other approved research lanes.

### Out of scope

- Runtime autonomy in production or staging.
- Autonomous push, merge, PR merge-readiness claims, or thread resolution.
- Hidden long-term agent memory.
- Changing public contracts, policy docs, secrets/config, or evaluation oracles inside the candidate loop.

---

## 2. Core model: immutable oracles vs mutable candidate surfaces

### Immutable evaluation oracles

Evaluation oracles define whether a candidate is better, worse, or invalid. They are read-only during the candidate loop.

Examples:

- benchmark harnesses under `scripts/benchmarks/`
- deterministic test files under `tests/`
- fixture datasets, manifests, checksums, and golden outputs
- policy and governance docs used as gates
- review / merge-readiness artifacts

### Mutable candidate surfaces

Candidate surfaces are the only files a future experiment runner may modify inside the inner loop.

First-wave allowlist:

- `core/insight/*`
- `core/rag/*`
- approved prompt/program docs explicitly named in the experiment charter

Rule:

- If a surface is not explicitly listed in the experiment charter, it is immutable for that experiment.

### Forbidden autonomous mutation surfaces

The candidate loop must never mutate:

- `AGENTS.md`, scoped `AGENTS.md`, `RUNBOOK_AGENT.md`
- `docs/orchestration/*` policy and governance SoT files
- `docs/review/PR_*_FIXED_MAPPING.md`
- `docs/contracts/*` unless a human opens an explicit follow-up PR for contract changes
- `docs/security/*`, `docs/compliance/*`, `docs/legal/*`
- benchmark harnesses, tests, fixtures, manifests, or expected outputs used as evaluation oracles
- secrets/config surfaces such as `.env*`, deployment secrets, compose env files, CI auth config
- public runtime configuration or release packaging files

Interpretation:

- The candidate may optimize implementation under test.
- The candidate may not rewrite the exam.

---

## 3. Execution environment and isolation

### Shared worktree safety

- Candidate experiments must not run in a dirty shared worktree.
- Candidate experiments must use an isolated scratch branch or temporary checkout.
- Do not use tracked `worktrees/` paths or commit local/dev artifacts forbidden by root `AGENTS.md`.

### Security constraints

- No hidden memory or silent canonical learning.
- No plaintext secret persistence.
- External or retrieved content remains untrusted.
- Any non-zero provider or network budget is `review-required`, not `auto-safe`.

### Human review gate

- An experiment result may produce a patch, diff, or PR packet proposal.
- It may never self-merge, self-resolve review threads, or claim merge readiness without the normal repo gates.

---

## 4. Experiment lifecycle

Every experimentation cycle follows this order:

```text
charter
 -> bootstrap
 -> candidate run
 -> oracle evaluation
 -> promote or discard
```

### Step 1: Charter

The coordinator creates an experiment charter before any candidate run.

Required fields:

- decision question
- mutable candidate surface
- immutable oracle list
- metrics and negative controls
- budgets and stop conditions
- promotion target if successful

### Step 2: Bootstrap

Bootstrap prepares:

- experiment ID
- isolated execution location
- selected agents and reviewer
- recommended skills
- exact command set for candidate evaluation

### Step 3: Candidate run

The candidate change is applied only to the allowlisted mutable surface and evaluated against immutable oracles.

### Step 4: Oracle evaluation

The experiment is accepted for promotion only if:

- all required oracle commands pass,
- the metric delta is positive or the acceptance threshold is met,
- no guard or policy violation occurred,
- no forbidden surface was mutated.

### Step 5: Promote or discard

- Winning candidates are promoted through KPP into exactly one durable destination.
- Rejected candidates are discarded, with failure reason recorded in the result packet.

---

## 5. Hard budgets

The coordinator must declare numeric budgets in the charter. If a budget is omitted, the defaults below apply.

| Budget | Default | Hard cap | Notes |
|---|---:|---:|---|
| Wall-clock per candidate cycle | 300 seconds | 600 seconds | Timeout beyond cap = failure |
| Automatic retries | 1 | 2 | Infra-only retries; never retry metric regressions as success strategy |
| Changed files per candidate | 3 | 5 | More requires explicit human approval |
| Provider/network calls | 0 | 20 | Any non-zero budget is `review-required` |
| Benchmark scripts per candidate | 1 | 2 | Keep the oracle small and deterministic |
| Targeted test commands per candidate | 2 | 3 | `make verify` is promotion-stage, not inner-loop |

Additional rules:

- `make verify` is forbidden inside the inner loop unless the charter explicitly marks the cycle as promotion-stage validation.
- Candidate loops must prefer deterministic local tests and benchmark scripts over broad suites.
- Budget breaches must be recorded as explicit failure classes, not ignored.

---

## 6. Metrics and negative controls

Every experiment charter must define:

- primary success metric,
- baseline or current reference,
- acceptance threshold,
- at least 2 negative controls,
- rollback-safe interpretation.

Examples of acceptable metrics:

- benchmark latency or p95 delta,
- retrieval quality score,
- contradiction count,
- verification rate,
- provider call count,
- token-savings estimate.

Negative controls must prove the candidate is not “winning” by:

- mutating the oracle,
- narrowing the test scope,
- bypassing guards,
- reducing work by disabling the feature under evaluation.

---

## 7. Failure classes

Every rejected run must map to one primary failure class.

| Failure class | Meaning | Default action |
|---|---|---|
| `timeout` | Candidate exceeded wall-clock budget | discard candidate |
| `oom` | Candidate exhausted memory or process limits | discard candidate |
| `metric_regression` | Primary metric degraded or failed threshold | discard candidate |
| `guard_failure` | Tests, policy guards, or safety checks failed | discard candidate |
| `policy_violation` | Forbidden surface changed or disallowed action attempted | stop cycle and escalate |
| `unchanged_result` | Candidate produced no meaningful improvement | discard candidate |
| `infra_flake` | Transient execution issue without code signal | retry within retry budget only |

Rule:

- A policy violation is not retryable as an automatic success path.

---

## 8. Promotion and memory

### KPP-only learning

Agents do not learn canonically from experiment history unless the result is promoted through KPP.

### Exactly one promotion destination

If a candidate wins, the coordinator promotes it into exactly one destination:

- PR packet or implementation PR
- audit/report artifact
- guard/test addition proposal
- backlog entry
- memory capsule under `docs/memory/`

### Promotion requirements

- winner includes reproducible evidence,
- winner references the immutable oracle that accepted it,
- deferred follow-ups go to `docs/roadmap/BACKLOG_LEDGER.md`,
- promotion decisions are emitted through `scripts/orchestration/experiment_promote.py`,
- no duplicate canonical policy wording across multiple docs.

---

## 9. Sequencing for the current program

Accepted sequence for this initiative:

1. PR1: governance foundation
2. PR2: deterministic bootstrap tooling
3. PR3: runner MVP
4. PR4: promotion automation + telemetry
5. PR5: CV docs/eval lane
6. PR6: first applied `LLM/RAG reliability` optimization PR

Interpretation:

- PR1 is docs/process only.
- PR2-PR4 remain orchestration/tooling scoped.
- PR5 is contract/eval only for CV, not runtime integration.
- PR6 is the first human-reviewed optimization PR generated through the governed lane.

---

## 10. Completion gate for an experimentation cycle

An experimentation cycle is complete only when all are true:

- charter exists,
- mutable surface is explicitly allowlisted,
- immutable oracle list is explicit,
- budgets are explicit,
- result packet records metric outcome and failure class,
- promotion decision is explicit,
- if deferred, the ledger entry exists,
- if promoted, the destination artifact is unique and evidence-backed.

---

## Related documents

- `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
- `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
- `docs/memory/kpp_knowledge_promotion_pipeline.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
