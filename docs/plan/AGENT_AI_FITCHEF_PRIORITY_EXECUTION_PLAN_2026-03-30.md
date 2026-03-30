# Agent / AI / FitChef Priority Execution Plan (2026-03-30)

## Purpose

Turn the open-priority map into one canonical execution order that is small
enough to act on without pretending the whole backlog can land in one PR.

This document is a planning artifact only:

- it does not change runtime behavior
- it does not close backlog items
- it does not replace `docs/roadmap/BACKLOG_LEDGER.md`

The source of truth for status and DoD remains:

- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- `docs/orchestration/contracts/JUDGMENT_EVAL_CONTRACT.md`

---

## Executive Summary

The highest-value open work falls into four layers:

| Layer | Why it matters now | Recommended status |
| ----- | ------------------ | ------------------ |
| Bootstrap and routing | Specialist intent is still fragile at task start | Do now |
| AI reliability loop | Safety, eval, and quota gaps can silently drift | Do in parallel |
| FitChef bounded eval and coaching | Personal-agent expansion must stay gated by deterministic eval | Do after or alongside reliability |
| User-visible rollout and unified framework | Valuable, but depends on the first three layers | Defer until foundations stabilize |

The practical sequence is:

1. preserve requested specialist intent at bootstrap
2. harden deterministic routing and task classification
3. enforce AI reliability gates and offline replay
4. keep FitChef expansion inside bounded, structured, eval-first lanes
5. expose reliability state in product UX
6. only then widen brand rollout and unified coach integration

---

## Priority Classification

### Ready Now

These items are already well-defined enough to support an implementation PR with
bounded scope and deterministic DoD.

#### Orchestration and skills

- `P0 Requested-agent bootstrap override and advisory specialist contract`
- `P1 Skill-router parity with policy docs and requested-agent bundles`
- `P1 Coordinator automation PR2 - bootstrap engine hardening`
- `P1 Coordinator automation PR3 - skill routing and intent classifier`
- `P1 Privileged workflow security-review requirement for orchestration and release surfaces`

#### AI reliability and ML cycle

- `P1 LLM reliability and security CI gates`
- `P1 AI multi-agent contracts runtime follow-up`
- `P1 Extract AI runtime into a dedicated bounded context`
- `P1 AI reliability experimentation sublane for logic + philosophy offline replay`
- `P1 PRO monthly quota for LLM endpoints`
- `P1 vector_rag SQL assembly refactor`

#### FitChef bounded lanes

- `P1 FitChef-first judgment offline eval contract and replay pack`
- `P1 Distortion Simulator structured coaching lane`
- `P1 Identity Loop Mapper reflective coaching lane`
- `P1 Frontend parity for new AI-agent and LLM reliability features`

### Blocked Or Dependency-Gated

These are valid priorities, but they should not be taken first if the goal is
operational leverage.

- `P1 Agent knowledge library template packs`
  - useful after bootstrap and routing semantics stop drifting
- `P1 FitChef website brand rollout`
  - blocked by stable mascot canon and bounded runtime semantics
- `P1 FitChef Figma production sync`
  - blocked by stable repo-side consumers and governed brand rollout

### Defer

These are valuable but should remain later-wave work.

- `P2 Centralize bootstrap sync-policy constants`
- `P2 UnifiedAICoach`
- `P2 FitChef phase-2 and localization waves`

---

## Recommended Waves

### Wave 1 - Bootstrap Truth

**Goal:** make specialist intent survive task creation.

Scope:

- requested-agent preservation in `task_bootstrap`
- routable vs advisory specialist semantics
- deterministic tests for requested-agent behavior

Backlog anchors:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-requested-agent-bootstrap`
- `docs/roadmap/BACKLOG_LEDGER.md` entry `Skill-router parity with policy docs and requested-agent bundles`

Success criteria:

- requested agent slugs are preserved or rejected with explicit rationale
- non-routable specialists are not silently lost
- routing metadata explains why a bundle was selected

### Wave 2 - Deterministic Routing

**Goal:** keep bootstrap, intent classification, and skill selection explainable.

Scope:

- `automation_flags`, `pr_phase`, sync flags
- deterministic task-class classifier
- required / recommended / conditional / blocked skill outputs
- privileged-surface `security-auditor` routing

Backlog anchors:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-classify-ci-checks-as-hard-soft-external`
- `docs/roadmap/BACKLOG_LEDGER.md` entry `Coordinator automation PR3 - skill routing and intent classifier`
- `docs/roadmap/BACKLOG_LEDGER.md` entry `Privileged workflow security-review requirement for orchestration and release surfaces`

Success criteria:

- task packets carry stable orchestration metadata
- skill routing remains minimal, deterministic, and test-covered
- privileged workflow changes always route through the security review path

### Wave 3 - AI Reliability Loop

**Goal:** make AI quality measurable before product expansion.

Scope:

- CI gate bundle for retrieval, faithfulness, injection, and privacy
- offline replay / ablation for logic + philosophy
- PRO quota parity
- bounded-context cleanup in `core/ai/*`
- vector retrieval path hardening

Backlog anchors:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-llm-reliability-security-gates`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-reliability-experiment-sublane`

Success criteria:

- runtime and CI point to the same canonical AI gates
- logic and philosophy gains are tested offline before rollout
- quota and retrieval paths are no longer weak seams

### Wave 4 - FitChef Structured Expansion

**Goal:** expand the personal agent through bounded products, not generic chat.

Scope:

- close bounded FitChef judgment offline-eval lane
- keep structured coach contract frozen and additive
- ship Distortion Simulator before broader conversational widening
- ship Identity Loop Mapper as premium reflection tooling

Backlog anchors:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-umbrella-foundation`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-judgment-offline-eval`

Success criteria:

- FitChef remains request-scoped, wellness-only, and structured
- evaluation gates exist before new public runtime behavior
- coaching outputs expose `sources[]`, confidence, warnings, and transparency

### Wave 5 - Product Surface Rollout

**Goal:** let users see the quality work.

Scope:

- Web + iOS reliability state
- FitChef brand rollout
- governed Figma production sync

Backlog anchors:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-frontend-ai-parity`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-web-brand-rollout`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-figma-production-sync`

Success criteria:

- AI assistant states visibly differentiate validated / partial / fallback
- FitChef visual rollout follows canon rather than ad-hoc asset reuse
- brand rollout does not precede bounded runtime trust work

---

## Recommended Next PR Candidates

Choose exactly one depending on the goal of the next session:

### Candidate A - Orchestration First

Best if the main pain is coordinator quality.

In:

- requested-agent bootstrap
- skill-router parity
- task classifier foundation

Out:

- FitChef runtime
- frontend parity
- design rollout

### Candidate B - Reliability First

Best if the main pain is AI correctness and safe rollout.

In:

- reliability CI gates
- logic/philosophy replay packet
- PRO quota parity

Out:

- mascot rollout
- broad product UX

### Candidate C - FitChef First

Best if the immediate goal is the personal agent.

In:

- bounded FitChef judgment closeout
- structured coach runtime contract alignment
- Distortion Simulator planning or implementation slice

Out:

- broad brand rollout
- UnifiedAICoach integration

---

## Decision Rules

- If a task changes task bootstrap or skill routing, take `Wave 1` and `Wave 2`
  before product work.
- If a task widens any LLM or coach surface, require `Wave 3` artifacts first.
- If a task expands FitChef behavior, prefer structured coaching tools over open
  chat.
- If a task only changes user-facing AI messaging, it should still align with
  `Wave 3` reliability evidence and `Wave 5` parity rules.

---

## Recommended Default Sequence

1. `Requested-agent bootstrap`
2. `PR2 bootstrap hardening`
3. `Skill-router parity`
4. `PR3 intent classifier`
5. `LLM reliability CI gates`
6. `Logic/philosophy replay sublane`
7. `AI bounded-context cleanup`
8. `PRO quota parity`
9. `FitChef judgment offline eval closeout`
10. `Distortion Simulator`
11. `Identity Loop Mapper`
12. `Frontend AI reliability parity`
13. `FitChef website brand rollout`
14. `FitChef Figma production sync`
15. `UnifiedAICoach`

---

## Notes

- This plan intentionally prefers bounded, testable seams over broad roadmap
  aspirations.
- It treats FitChef as a structured personal agent, not an unbounded coaching
  chatbot.
- It keeps orchestration correctness, AI reliability, and product rollout in
  dependency order.
