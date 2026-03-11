# Research Examples (Repo-native, bounded)

**Purpose:** Provide concrete examples of how to apply:

- `docs/research/SCIENTIFIC_WORKFLOW_TEMPLATE.md`
- `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md` (`docs/orchestration/RESEARCH_TRACK_PROTOCOL.md:L52-L112`)
- `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md` (`docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md:L37-L93`)

**Status:** Examples (dev-only). Copy/paste safe.

---

## Example 1 — Choosing a RAG vector store (decision-ready)

### Decision question

Which vector store should we adopt for PulsePlate RAG: `pgvector` (Postgres) vs `Qdrant`?

### Hypothesis

`pgvector` will be operationally simpler and sufficient for MVP-scale retrieval quality, while meeting privacy/deletion needs.

### Success criteria

- [ ] Deterministic integration tests exist for retrieval correctness + deletion behavior
- [ ] Operational footprint is documented (how to run locally + in CI)
- [ ] Cost/latency trade-offs are measured or bounded

### Constraints

- External facts must be evidence-backed via Research Track
- No runtime code in docs-only PR; produce plan artifacts only

### Methods

- Run Research Track in parallel:
  - OSS/maintenance signals
  - privacy/deletion semantics
  - latency/cost expectations
  - deterministic test plan for deletion + retrieval correctness

### Negative controls

- Validate that conclusions don’t rely on a single blog post
- Verify at least two primary sources for any “Verified” claim

### Promotion plan

- Ledger item for runtime selection PR with DoD
- ADR if we commit to a long-lived dependency

---

## Example 2 — CV “photo → food items” contract (uncertainty + privacy)

### Decision question

What is the minimal contract for photo→items recognition that supports uncertainty-aware UX and privacy boundaries?

### Hypothesis

Defining a contract with explicit confidence + degrade states will reduce “hallucinated certainty” and enable deterministic tests for UI states.

### Success criteria

- [ ] Contract schema includes: items[], per-item confidence, overall confidence, degrade_reason_key
- [ ] UX degrade states are enumerated (low confidence, multiple plausible, no food detected)
- [ ] Privacy packet defines retention/deletion and user consent copy

### Constraints

- Treat all image-derived content as sensitive; default to minimal retention
- No “magic sizing” claims; physically plausible bounds required (sensor/physics priors)

### Methods

- Brainstorm protocol with tracks:
  - CV pipeline + confidence (cv-agent)
  - uncertainty contract (bayesian-uq-agent)
  - privacy posture (security-auditor)
  - sensor plausibility (physics-sensor-agent)
- Promote as:
  - schema doc + ledger items for runtime implementation + tests

Canonical PR5 follow-up docs:

- `docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md`
- `docs/orchestration/CV_EXPERIMENT_PACKET_TEMPLATE.md`
- `docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md`

### Negative controls

- Ensure contract works even when recognition returns empty/ambiguous results
- Ensure UI does not imply medical accuracy
