# AI Output Contracts (Draft, Docs-only)

**Status:** Draft contracts for future implementation PRs
**Last updated:** 8 February 2026 (PR #691)

---

## Contract A1) Reasoning & Logic (draft)

### Definition

Reasoning & Logic defines contractual behavior of AI systems when producing nutrition and wellness advice.
The system must apply structured logical operations and rule constraints to generate consistent, traceable recommendations.

### Contract (MVP)

- **Rule-based constraints** (deterministic): allergies/preferences/goals must be satisfied.
- **Symbolic-neural hybrid**: LLM may propose, but deterministic domain logic must validate critical computations.
- **Forbidden**: medical diagnosis/treatment claims.
- **MVP decision:** post-generation validation (generate → validate → correct/degrade).

### Required disclaimer (wellness-only)

Use the canonical disclaimer: `docs/safety/WELLNESS_DISCLAIMER_CANONICAL.md`.

### Acceptance criteria (future tests)

1. Allergy constraint enforced (e.g., peanuts never appear if forbidden).
2. Target ranges enforced (e.g., caloric totals within allowed tolerance).
3. Forbidden phrases (“cures”, “treats”, “diagnoses”) are blocked or downgraded with disclaimer.

---

## Contract A2) Uncertainty / Bayesian-UQ (draft)

### Definition

Uncertainty Quantification (UQ) requires AI outputs to expose confidence scores / uncertainty ranges and to degrade safely under low confidence.

### Contract (MVP)

- Every predictive/inferential output includes **confidence** (score + bucket).
- Low confidence triggers: clarifying questions, softer language, explicit disclaimers.
- Do not mislabel heuristics as “Bayesian” unless posterior-based methods exist.
- PR5 note: the offline `photo -> food` CV lane uses **qualitative buckets only**
  (`high | medium | low | unknown`) per
  `docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md`.

### Suggested schema (illustrative)

```json
{
  "confidence": 0.72,
  "confidence_bucket": "medium",
  "uncertainty": {
    "lower": 0.61,
    "upper": 0.82,
    "confidence_level": "p95"
  },
  "warning": null
}
```

### Acceptance criteria (future tests)

1. Confidence exists and is bounded (0.0–1.0) where applicable.
2. Low-confidence responses include `warning` + degrade behavior.
3. Interval validity checks (`lower < estimate < upper`) for interval outputs.

---

## Contract A3) RAG + Recursive Verification (draft)

### Definition

RAG requires grounding in retrieved sources; recursive verification must be bounded for multi-step retrieval and consistency checks.

### Contract (MVP)

- Responses include `sources[]` (IDs + excerpts + scores).
- Claims not supported by sources are flagged as “inference beyond sources”.
- Recursion is bounded by explicit budgets (max hops/calls/time).

See also:

- Runtime memory trust boundaries + budgets (draft): `docs/orchestration/contracts/RUNTIME_CONTEXT_MEMORY_CONTRACTS.md`

### Suggested schema (illustrative)

```json
{
  "answer": "…",
  "sources": [
    {"id": "kb:doc123#chunk7", "similarity": 0.81, "excerpt": "…"}
  ],
  "unverified_inference": false,
  "retrieval": {"top_k": 5, "max_similarity": 0.81}
}
```

### Acceptance criteria (future tests)

1. Retrieval precedes generation (ordering evidence in logs / instrumentation).
2. No factual response without `sources[]` (unless explicit “no sources found”).
3. Budget enforcement: recursion stops deterministically at limits.

---

## Contract A4) CV pipeline (draft)

Canonical PR5 offline-eval overlay:
`docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md`

### Definition

CV pipeline turns photos into candidate food items with confidence, optionally portion estimates, and nutrition mapping via deterministic lookup.

### Contract (MVP)

- Per-item confidence required; PR5 keeps this qualitative only via the canonical
  CV contract (no competing numeric schema in this draft document).
- Nutrition values must come from deterministic lookup (no “LLM guessed calories”).
- Privacy/logging boundaries must be explicit (consent, retention).
- Canonical schema, degrade states, and privacy packet fields live only in:
  `docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md`

### Acceptance criteria (future tests)

1. Invalid images return 422 with clear errors.
2. Empty recognition returns `items: []` with warning.
3. Confidence propagation exists; low-confidence outcomes trigger the canonical
   degrade states from `CV_PHOTO_FOOD_EVAL_CONTRACT.md`.
