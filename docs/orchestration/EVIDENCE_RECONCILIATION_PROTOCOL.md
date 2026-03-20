# Evidence Reconciliation Protocol

<!-- markdownlint-disable MD013 -->

**Purpose:** Define how internal agents reconcile claims, retrieved evidence, and contradictions before a recommendation is treated as promotable.

**Status:** Canonical for governed judgment work. Internal-first and additive to existing research / experimentation protocols.

---

## Canonical references

- `docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md`
- `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`
- `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`

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

---

## 5. Contradiction handling

Contradiction checks must cover:

- claim vs source conflict
- claim vs claim conflict
- claim vs policy boundary conflict

Implementation note:

- Lightweight deterministic helpers may act as lexical or structural prefilters only.
- Full reconciliation still requires the wider adjudication flow, not one helper in isolation.

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

---

## 7. Decision rule

Promotion guidance:

- `promote` only when material claims are supported, contradiction risk is controlled, and the answer remains within safety boundaries
- `defer` when the answer is safe but materially under-supported
- `discard` when the answer is contradicted, unsafe, or overconfident

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
