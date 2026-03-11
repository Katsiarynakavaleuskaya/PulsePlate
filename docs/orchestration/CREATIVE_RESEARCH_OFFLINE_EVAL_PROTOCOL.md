# Creative Research Offline Eval Protocol

<!-- markdownlint-disable MD013 -->

**Purpose:** Define the canonical offline-eval overlay for the governed `creative_research` sub-lane.

**Status:** Canonical overlay for PR-B. This file extends, and does not replace,
`docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md` and
`docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`.

**Hard rule:** This protocol is offline-eval-only. It does not authorize runtime agent branching,
provider calls, public endpoints, OpenAPI changes, feature-flag rollout, or autonomous promotion.

---

## Canonical references

- Umbrella experimentation SoT: `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- Creative sub-lane SoT: `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`
- Eval contract: `docs/orchestration/contracts/CREATIVE_RESEARCH_EVAL_CONTRACT.md`
- Experiment packet template: `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
- Research entrypoint: `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
- KPP: `docs/memory/kpp_knowledge_promotion_pipeline.md`
- Runtime claim validator: `core/insight/philosophy_validator.py`

---

## 1. Scope

### In scope

- Deterministic offline scoring of `creative_research` candidate bundles.
- Output-class classification:
  - `mechanistic_hypothesis`
  - `experimental_proposal`
  - `anomaly_explanation_candidate`
  - `creative_ideation`
- Corpus-distance and peer-distance heuristics for novelty and duplicate detection.
- Negative controls for unsafe wellness language, missing discovery fields, duplicate candidates,
  and shallow corpus overlap.
- Stable `promote` | `defer` | `discard` decisions with explicit downgrade to
  `interesting but unverified hypothesis` when grounding is weak.

### Out of scope

- Runtime orchestration execution.
- Sampling/provider/model decisions.
- Hidden memory or silent canon promotion.
- Public creativity endpoints or heavy core-path LLM surfaces.
- OpenAPI, frontend, iOS, or runtime policy changes.

---

## 2. Offline bundle contract

The input unit for PR-B is a deterministic bundle:

- `schema_version`
- `bundle_id`
- `task_class = creative_research`
- `phase`
- `prompt_seed`
- optional `reference_corpus[]`
- `candidates[]`

Each candidate must carry the hypothesis fields needed for offline evaluation:

- `candidate_id`
- `claim`
- `mechanism`
- `evidence_needed`
- `falsifier`
- `confidence`
- `known_risks[]`
- `wellness_boundary`

Rule:

- Missing `mechanism`, `evidence_needed`, or `falsifier` does not fail bundle parsing.
- Instead, the runner must demote that candidate to `creative_ideation` and discard it.

---

## 3. Deterministic judge semantics

PR-B uses a model-free judge. No embeddings, provider calls, or network dependencies are allowed.

The judge must:

- validate the bundle fail-closed
- classify each candidate into the canonical output classes
- compute scorecard fields:
  - `originality`
  - `flexibility`
  - `mechanism_specificity`
  - `groundedness`
  - `falsifiability`
  - `wellness_safety`
  - `hallucination_risk`
- flag negative controls
- emit `promote` | `defer` | `discard`

Allowed heuristics for PR-B:

- lexical corpus-distance
- peer similarity / duplicate clustering
- rule-based mechanism/evidence/falsifier hints
- deterministic wellness claim validation via `philosophy_validator`

Disallowed in PR-B:

- embedding distance
- stochastic judges
- latent memory promotion
- self-modifying routing/telemetry policy

---

## 4. Negative controls

PR-B must carry explicit negative controls and regression tests for at least:

- duplicate or near-duplicate candidates
- missing discovery fields
- unsafe wellness / medical-claim drift
- high corpus-overlap / shallow novelty

Rule:

- negative controls must fail closed without provider calls
- repeated identical inputs must yield byte-stable JSON outputs

---

## 5. Promotion thresholds

Canonical outcomes:

- `promote`
  - candidate remains discovery-class, clears wellness safety, and reaches minimum quality bars
- `defer`
  - candidate is potentially useful but remains under-grounded or only partially specific
- `discard`
  - candidate is unsafe, duplicate, ideation-only, or high-risk

Degrade rule:

- If grounding or falsifiability is weak, the runner must label the candidate as
  `interesting but unverified hypothesis`.

Promotion remains human-gated:

- PR-B may emit a decision
- PR-B does not itself promote to runtime or memory

---

## 6. Artifact rules

Artifacts from the offline runner may be written only under gitignored local paths such as:

- `artifacts/orchestration/creative_research/evals/`

Tracked fixtures are allowed only in test fixture directories.

PR-B must not commit:

- generated eval outputs
- local brainstorming logs
- provider traces
- raw hidden-memory artifacts
