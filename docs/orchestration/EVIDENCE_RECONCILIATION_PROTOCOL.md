# Evidence Reconciliation Protocol

<!-- markdownlint-disable MD013 -->

**Purpose:** Define how internal agents reconcile claims, retrieved evidence, and contradictions before a recommendation is treated as promotable.

**Status:** Canonical for governed judgment work. Internal-first and additive to existing research / experimentation protocols. Shared enums and normalization helpers live in `core/judgment.py:32-75` and `core/judgment.py:178-264`; any remaining evidence-anchor follow-up for this dev-only seam is tracked in `docs/roadmap/BACKLOG_LEDGER.md:7196-7208`.

---

## Canonical references

- `docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md`
- `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`
- `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`

Coordinator-first lifecycle stays canonical per `docs/orchestration/workflow.md:43-58`, while dev-only experimentation limits and promotion boundaries are governed by `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:5-9` and `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:190-220`.

---

## 1. Reconciliation goal

The system must prefer:

- factually supported claims
- explicit uncertainty
- visible contradiction handling

The system must reject:

- popularity-based certainty without support
- unsupported escalation
- silent contradiction smoothing

---

## 2. Required reconciliation sequence

For each material claim:

```text
extract claim
 -> classify claim_type
 -> attach source_ids
 -> assign support_status
 -> detect conflicts
 -> calibrate uncertainty
 -> keep/rewrite/drop
```

---

## 3. Support status contract

Allowed `support_status` values:

- `supported`
- `partially_supported`
- `unsupported`
- `contradicted`

Rules:

- `supported` requires at least one non-conflicting source or deterministic verifier signal.
- `partially_supported` is allowed only when the response language is correspondingly downgraded.
- `unsupported` claims must not be phrased as settled facts.
- `contradicted` claims must be rewritten or removed.

Implementation source: `core/judgment.py:40-52` exports the canonical `support_status` values and `core/judgment.py:178-224` enforces supported / contradicted record invariants.

---

## 4. Evidence mode contract

Allowed `evidence_mode` values:

- `direct_source`
- `cross_source_synthesis`
- `deterministic_verifier`
- `heuristic`
- `none`

Rules:

- `heuristic` and `none` may not back strong factual wording.
- `deterministic_verifier` may upgrade mathematical or rule-checkable logic, but it does not justify medical, emotional, or normative overreach.

Implementation source: `core/judgment.py:46-52` exports canonical `evidence_mode` values and `core/judgment.py:190-215` enforces the evidence-mode/source linkage rules.

---

## 5. Contradiction handling

Contradiction checks must cover:

- claim vs source conflict
- claim vs claim conflict
- claim vs policy boundary conflict

Implementation note:

- Lightweight deterministic helpers may act as lexical or structural prefilters only.
- Full reconciliation still requires the wider adjudication flow, not one helper in isolation.

Implementation source: lexical contradiction prefilters live in `core/judgment.py:97-110` and `core/judgment.py:227-233`, while canonical record-level conflict handling stays in `core/judgment.py:178-224`.

Required behavior:

- if conflict is recoverable, downgrade and qualify
- if conflict is material, discard the claim
- if conflict affects the core answer, return `defer` or `discard`

Never hide contradiction by averaging or blending incompatible claims.

---

## 6. Uncertainty split

Judgment-capable outputs should avoid one undifferentiated confidence number internally.

Required internal uncertainty dimensions:

- `retrieval_confidence`
- `evidence_coverage`
- `contradiction_risk`
- `actionability_confidence`
- `personalization_conflict`

Rule:

- Low confidence in one dimension must not be masked by high confidence in another.

Implementation source: `core/judgment.py:69-75` defines the uncertainty fields and `core/judgment.py:236-264` clamps each internal probability dimension.

---

## 7. Decision rule

Promotion guidance:

- `promote` only when material claims are supported, contradiction risk is controlled, and the answer remains within safety boundaries
- `defer` when the answer is safe but materially under-supported
- `discard` when the answer is contradicted, unsafe, or overconfident

Implementation source: `core/judgment.py:53-61` exports the canonical promotion labels; the current promote/defer/discard decision semantics remain governance-owned under `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:190-220` until a promoted runtime contract is approved.

---

## 8. Creative-research interaction

`creative_research` remains the proving ground for verifier-backed judgment.

Discovery-grade candidates must add:

- `alternative_explanations`
- `counterevidence`
- `stopping_rule`
- `decision_rule`
- `minimum_observation`

These fields are required to make reconciliation scientific instead of decorative.
