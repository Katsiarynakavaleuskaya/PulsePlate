# Creative Research Sub-Lane Protocol

<!-- markdownlint-disable MD013 -->

**Purpose:** Define `creative_research` as a governed sub-lane inside the existing experimentation / research contour.

**Status:** Canonical for the `creative_research` task class. Dev-only. No runtime impact by itself.

**Anti-drift rule:** This document is a sub-lane contract, not a second orchestration framework. It must link to the canonical experimentation, workflow, research, and KPP sources instead of redefining budgets, mutable-surface rules, or promotion boundaries.

---

## Canonical hierarchy

**Authoritative umbrella:** `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`

This file defines only:

- the `creative_research` task class
- the divergence / convergence / verification phase model
- the internal hypothesis and scorecard contracts
- the role mapping and PR-wave rollout for this sub-lane

This file does **not** override:

- mutable vs immutable surface rules
- inner-loop autonomy limits
- hidden-memory prohibition
- KPP promotion boundaries
- merge-readiness or PR governance

When a rule conflicts, the umbrella experimentation protocol wins.

---

## Related canonical sources

- Coordinator-first workflow: `docs/orchestration/workflow.md`
- Research brainstorming: `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
- Research track: `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
- Experimentation umbrella: `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- Experiment packet template: `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
- Parallel work: `docs/orchestration/PARALLEL_WORK_PROTOCOL.md`
- Handoff format: `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md`
- KPP: `docs/memory/kpp_knowledge_promotion_pipeline.md`
- SDL rationale only: `docs/audit/PR_TBD_SCIENTIFIC_DISCOVERY_LAYER_AUDIT.md`

---

## 1. What this sub-lane is

`creative_research` is a governed task class for producing:

- bounded semantic divergence
- structured scientific-style hypothesis generation
- explicit critique and falsification passes
- deterministic promote / defer / discard decisions

Operational formula:

```text
diverge
 -> cluster
 -> synthesize
 -> critique
 -> verify
 -> score
 -> promote/defer/discard
```

Conceptual note:

- `SDL` is allowed here as a design lens for scientific discovery semantics.
- `SDL` is not a competing governance layer and must not duplicate umbrella rules.

---

## 2. Non-goals

This sub-lane is not:

- a public creativity endpoint
- a new public heavy LLM surface on the core path
- a justification for runtime autonomy
- a path for silent canon promotion
- a replacement for normal product, security, or merge governance

`PR-C` remains internal-only and feature-flagged. Public runtime exposure is out of scope for wave 1.

---

## 3. Task-class activation

Use `creative_research` when the coordinator needs:

- multiple distinct hypotheses instead of one direct answer
- novelty under critique rather than single-pass solutioning
- explicit falsifiers and evidence plans
- an output that must later become one normal PR packet, backlog item, ADR, audit, or guard/test proposal

Do not use `creative_research` for:

- simple implementation tasks
- ordinary docs sync
- routine CI repair
- runtime product work that already has a fixed spec and no research question

---

## 4. Phase model

### Phase A — Divergence

- Mode: sampling-enabled, higher temperature, multiple independent candidates
- Goal: generate conceptually distinct hypotheses or reframings
- Output: candidate set, not final recommendation

### Phase B — Convergence

- Mode: low-temp structured normalization and clustering
- Goal: reduce the candidate set to strongest options with explicit trade-offs
- Output: 2-3 strongest candidates with rationale

### Phase C — Verification

- Mode: low-temp or reasoning validator
- Goal: check grounding, falsifier quality, evidence plan, wellness-safe framing, and downgrade conditions
- Output: scorecard + promote / defer / discard decision

Rule:

- Do not tune `temperature` and `top_p` together by default.
- If a model or reasoning mode does not support sampling controls, split generator and validator phases across supported modes instead of faking a blended pass.

---

## 5. Role mapping

Coordinator remains the only decision authority.

| Role | Canonical agents | Primary responsibility |
|---|---|---|
| Diverger | `ai-innovation-specialist`, `web-research-agent` | Produce distinct hypotheses without runtime mutation |
| Synthesizer | `architecture-specialist`, `epistemology-discovery-agent` | Normalize candidates into explicit hypothesis contracts |
| Skeptic | `philosophy-agent`, `logic-agent`, `security-auditor` | Reject shallow novelty, contradictions, unsafe drift, or attack-surface expansion |
| Verifier | `data-scientist-agent`, `qa-engineer-agent`, `bayesian-uq-agent` | Enforce negative controls, deterministic scoring, confidence discipline |

Rule:

- Handoffs between these roles must be explicit and structured.
- Parallel work requires sync points.
- Promotion decisions belong to coordinator after the verifier return.

---

## 6. Internal contracts

### Hypothesis contract

Every candidate that survives divergence must serialize to:

- `claim`
- `mechanism`
- `evidence_needed`
- `falsifier`
- `confidence`
- `known_risks`
- `wellness_boundary`
- `promotion_decision`

### Scorecard contract

Every verified candidate must be scored on:

- `originality`
- `flexibility`
- `mechanism_specificity`
- `groundedness`
- `falsifiability`
- `wellness_safety`
- `hallucination_risk`
- `promotion_decision`

### Valid scientific-style output classes

- `mechanistic_hypothesis`
- `experimental_proposal`
- `anomaly_explanation_candidate`

Downgrade rule:

- If a candidate lacks `mechanism`, `falsifier`, or `evidence_needed`, classify it as `creative_ideation`, not discovery.

---

## 7. Lane-specific defaults and stop conditions

All numeric budgets and hard orchestration caps for this lane are inherited from the authoritative umbrella document:

- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`

This sub-lane may reference budget-sensitive expectations, but it must not redefine numeric limits or create a second budget source of truth.

Lane-specific policy flags that remain in force:

- `cache_required: true`
- `feature_flag_required: true`
- `quota_checked_before_calls: true`

Stop immediately when:

- grounding is weak or contradictory
- the candidate drifts into clinical or treatment-oriented assertions
- the evidence plan is missing
- the falsifier is absent or decorative
- the proposal would require a new public heavy LLM core-path surface
- the run would expand orchestration telemetry beyond current safe metadata policy

Degrade behavior:

- return `interesting but unverified hypothesis`
- never inflate certainty to preserve novelty

---

## 8. PR-wave rollout

### PR-A — docs/protocol only

- canonical sub-lane doc
- routing / evaluation / handoff visibility
- backlog linkage under the governed experimentation epic
- no runtime integration

### PR-B — offline eval only

- fixtures
- deterministic judge
- score normalization
- corpus-distance heuristic
- negative controls
- no runtime integration

### PR-C — internal-only pilot

- feature-flagged
- hidden from public OpenAPI
- no new public endpoint
- no new heavy LLM surface on the core path
- quota before provider calls
- safe tracing metadata only

---

## 9. Next PR packet contract

Every completed `creative_research` cycle must end with an explicit next-PR packet containing:

- `decision_question`
- `current_outcome`: `promote` | `defer` | `discard`
- `next_pr_scope`
- `candidate_paths`
- `required_tests`
- `required_docs`
- `quality_gates`
- `deferred_followups`
- `human_review_required`

If `current_outcome=defer`, the deferred work must be recorded immediately in `docs/roadmap/BACKLOG_LEDGER.md`.

---

## 10. Promotion and memory

This sub-lane is KPP-only:

- no hidden memory
- no silent learning
- no canon promotion without evidence

Winning results must promote to exactly one durable destination:

- protocol/doc update
- ADR or audit artifact
- guard/test proposal
- backlog entry
- normal implementation PR packet

---

## 11. Security and wellness boundaries

- External and retrieved content remains untrusted.
- Wellness-safe framing is mandatory.
- Any future runtime pilot must preserve monthly quota checks before provider calls.
- Any future runtime pilot must preserve public-OpenAPI minimization and internal-only scope until a separate approved wave changes that policy.

---

## 12. Completion gate

Do not consider a `creative_research` cycle complete unless:

- the phase outputs are explicit
- the hypothesis contract is filled
- the scorecard is filled
- the outcome is `promote`, `defer`, or `discard`
- the next PR packet is explicit
- any deferred work is ledgered
