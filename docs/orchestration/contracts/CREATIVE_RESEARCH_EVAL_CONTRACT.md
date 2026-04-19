# Creative Research Eval Contract

<!-- markdownlint-disable MD013 -->

**Status:** Canonical PR-B contract for deterministic offline creative-research evaluation only.

**Scope:** `prompt seed -> candidate hypotheses -> deterministic classification -> scorecard -> promote|defer|discard`

**Non-goal:** This file does not define runtime API shapes, model/provider configuration, or user-visible product behavior.

---

## 1. Input bundle shape

Illustrative input:

```json
{
  "schema_version": "1.0",
  "bundle_id": "creative-research-valid",
  "task_class": "creative_research",
  "phase": "verification",
  "prompt_seed": "meal adherence under time scarcity",
  "reference_corpus": [
    "Weekly reminder loops improve meal adherence."
  ],
  "candidates": [
    {
      "candidate_id": "hyp-batch",
      "claim": "Sunday ingredient batching may reduce weekday skipping.",
      "mechanism": "Batching lowers prep friction before time pressure builds.",
      "evidence_needed": "Compare skip rate and prep time across four weeks.",
      "falsifier": "If skip rate stays flat despite lower prep time, the mechanism is wrong.",
      "confidence": "medium",
      "known_risks": ["selection bias"],
      "wellness_boundary": "Wellness coaching only. Not diagnosis or treatment."
    }
  ]
}
```

Required top-level fields:

- `schema_version`
- `bundle_id`
- `task_class = creative_research`
- `phase`
- `prompt_seed`
- `candidates[]`

Optional top-level fields:

- `reference_corpus[]`

Required candidate fields:

- `candidate_id`
- `claim`
- `confidence`
- `known_risks[]`
- `wellness_boundary`

Discovery fields that may be empty but trigger downgrade when missing:

- `mechanism`
- `evidence_needed`
- `falsifier`

Scientific structure fields that may be empty but trigger downgrade when missing:

- `alternative_explanations[]`
- `counterevidence[]`
- `stopping_rule`
- `decision_rule`
- `minimum_observation`

---

## 2. Output classes

The runner must emit exactly one output class per candidate:

- `mechanistic_hypothesis`
- `experimental_proposal`
- `anomaly_explanation_candidate`
- `creative_ideation`

Canonical downgrade rule:

- If `mechanism`, `evidence_needed`, or `falsifier` is missing, the candidate becomes
  `creative_ideation` even if the prose sounds novel.
- If scientific structure fields are missing, parsing still succeeds but the evaluator must
  downgrade the promotion decision to `defer` or `discard`.

---

## 3. Scorecard

Every candidate must emit:

```json
{
  "originality": 0,
  "flexibility": 0,
  "mechanism_specificity": 0,
  "groundedness": 0,
  "falsifiability": 0,
  "wellness_safety": 0,
  "hallucination_risk": 0
}
```

Scale:

- `0` = fails closed or essentially absent
- `5` = strongest deterministic score for this phase

Heuristic meaning:

- `originality`: distance from seed corpus
- `flexibility`: distance from sibling candidates
- `mechanism_specificity`: causal specificity instead of generic prose
- `groundedness`: quality of evidence plan and explicit risks
- `falsifiability`: quality of the refutation path
- `wellness_safety`: claim-semantic safety under wellness posture
- `hallucination_risk`: risk of overclaiming beyond evidence

---

## 4. Promotion thresholds

Canonical decisions:

- `promote`
- `defer`
- `discard`

Deterministic policy:

- `discard` when any of the following holds:
  - unsafe wellness language
  - duplicate candidate
  - `creative_ideation`
  - high hallucination risk
- `promote` only when the candidate:
  - remains a discovery-class output
  - clears wellness safety
  - reaches at least medium quality on novelty, mechanism, evidence, and falsifiability
- `defer` for intermediate cases

Weak-grounding downgrade:

- non-promoted weak-grounding candidates must carry
  `presentation_label = "interesting but unverified hypothesis"`

---

## 5. Negative controls

Minimum negative controls for PR-B:

- duplicate candidate
- unsafe wellness claim
- missing discovery fields
- high corpus overlap

Future PRs may add stronger novelty checks, but PR-B must stay deterministic and network-free.
