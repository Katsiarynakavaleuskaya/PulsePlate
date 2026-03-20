# Judgment Adjudication Sub-Lane Protocol

<!-- markdownlint-disable MD013 -->

**Purpose:** Define a verification-first sub-lane for judgment-capable agents that must distinguish supported claims from plausible but weak or contradictory outputs.

**Status:** Canonical for internal `judgment_adjudication` work. Dev-only until promoted through the normal repo and rollout gates. The dev-only boundary and no-runtime-impact rule are governed by `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:5-9` and `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:63-76`; remaining exit-criteria hardening for this temporary seam is tracked in `docs/roadmap/BACKLOG_LEDGER.md:7196-7208`.

**Anti-drift rule:** This document extends existing orchestration governance. It does not create a new autonomy layer, replace coordinator-first routing, or weaken experimentation limits; governed sub-lane limits and forbidden overrides are defined in `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:24-56`.

---

## Canonical hierarchy

**Authoritative umbrella:** `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`

**Related canonical sources:**

- `docs/orchestration/workflow.md`
- `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
- `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`
- `docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md`
- `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md`
- `docs/memory/kpp_knowledge_promotion_pipeline.md`

When a rule conflicts, the umbrella experimentation protocol wins. Coordinator-first task analysis and role assignment stay canonical per `docs/orchestration/workflow.md:43-58` and `docs/orchestration/workflow.md:190-201`, while the runtime packet bridge that materializes primary/secondary/reviewer roles is implemented in `scripts/orchestration/task_bootstrap.py:119-134` and `scripts/orchestration/task_bootstrap.py:380-460`.

---

## 1. What this sub-lane is

`judgment_adjudication` is a governed internal sub-lane for responses that must be:

- evidence-aware
- contradiction-checked
- uncertainty-calibrated
- safe to promote, defer, or discard

Canonical flow:

```text
propose
 -> skeptic pass
 -> contradiction check
 -> uncertainty split
 -> calibrated decision
 -> promote/defer/discard
```

This lane strengthens correctness. It does not add broader runtime autonomy.

---

## 2. Activation criteria

Use this sub-lane when the coordinator needs one or more of:

- explicit separation between supported and speculative claims
- a skeptic/verifier pass before an internal recommendation is accepted
- deterministic contradiction handling
- confidence broken into narrower uncertainty dimensions
- promotion discipline for FitChef or other judgment-capable lanes

Do not use it for:

- simple implementation tasks
- ordinary docs sync
- public heavy-runtime feature rollout without prior offline eval

---

## 3. Shared claim taxonomy

All judgment-capable agents must classify claims using exactly one of:

- `fact`
- `source_grounded_summary`
- `inference`
- `recommendation`
- `speculation`
- `emotional_framing`

Rule:

- If classification is ambiguous and no stronger deterministic marker wins, degrade toward `speculation`, not `fact`.
- Heuristic precedence should be documented in code so `recommendation` or `source_grounded_summary` promotion is explicit rather than accidental.

Implementation source: `core/judgment.py:32-61` exports the canonical taxonomy constants and `core/judgment.py:123-175` normalizes claim parsing / classification.

---

## 4. Shared claim-to-evidence record

Every adjudicated claim must serialize to:

- `claim_type`
- `support_status`
- `source_ids`
- `evidence_mode`
- `conflict_flag`

Semantics:

- `support_status` captures whether the claim is supported, partial, unsupported, or contradicted.
- `evidence_mode` captures whether support is direct, synthesized, heuristic, or absent.
- `conflict_flag` must be true when the claim conflicts with retrieved evidence, other claims, or a known safety boundary.

Implementation source: `core/judgment.py:62-75` defines the shared record fields and `core/judgment.py:178-224` enforces the canonical builder invariants for `support_status`, `source_ids`, `evidence_mode`, and `conflict_flag`.

---

## 5. Role mapping

Coordinator remains the only decision authority.

| Role | Canonical agents | Responsibility |
|---|---|---|
| Proposer | routed primary agent | Produce the initial answer or hypothesis bundle |
| Skeptic | `logic-agent`, `philosophy-agent`, `security-auditor` | Reject shallow certainty, unsupported escalation, and contradiction drift |
| Verifier | `data-scientist-agent`, `qa-engineer-agent`, `bayesian-uq-agent` | Check claim structure, evidence linkage, and uncertainty semantics |
| Decision owner | `agent-coordinator` | Promote, defer, or discard based on bounded evidence |

Rule:

- Advisory agents may inform this lane, but only explicit routed roles may produce runnable adjudication output.

Coordinator-only decision authority is enforced by `docs/orchestration/workflow.md:47-58` and `docs/orchestration/workflow.md:194-201`; routed primary/secondary/reviewer ownership is serialized in `scripts/orchestration/task_bootstrap.py:380-460`.

---

## 6. Output contract

Each adjudication result must include:

- the normalized claim set
- the claim-to-evidence records
- uncertainty split
- calibrated decision
- promotion rationale

The calibrated decision must be one of:

- `promote`
- `defer`
- `discard`

Promotion default:

- `defer` if evidence is partial but safe
- `discard` if contradiction or safety failure is present

Implementation source: `core/judgment.py:53-61` exports the canonical promotion labels, and this protocol owns the current governance semantics until a promoted runtime contract exists.

---

## 7. Stop conditions

Stop immediately when:

- a medical or therapist-like boundary is crossed
- contradiction remains unresolved
- evidence linkage is missing for material claims
- uncertainty cannot be expressed without fabricated precision
- the task would require a new public heavy LLM surface

The dev-only/public-runtime boundary is governed by `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:70-76` and `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:140-146`.

---

## 8. Rollout order

Wave order for this sub-lane:

1. docs and shared deterministic contracts
2. offline eval fixtures and replay packs
3. hidden internal pilot only
4. coordinator packet wiring
5. bounded FitChef adoption

This list is the activation order, not the implementation order: `decision_contract`,
`judgment_budget`, and `result_adjudication` are already wired into coordinator task
bootstrap packets in `scripts/orchestration/task_bootstrap.py:409-458`, while
coordinator packet wiring remains gated for enablement after offline eval and the
hidden pilot.

Public heavy-runtime exposure is out of scope until the hidden pilot and offline evals prove value.
