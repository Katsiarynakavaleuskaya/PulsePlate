# WAVE6 A7 Task Analysis

## Task Analysis

**Task:** Implement `PR-A7` as a bounded Wave 6 runtime slice for recursive RAG
and bounded recursive verification on the existing product-AI insight surfaces.

**Domain(s):** AI/ML | Architecture | Security | Multiple

**Complexity:** Complex

**Priority:** P1

- **Priority track (P0-A / P0-B / P1):** P1

**Expected Outcome:** A narrow recursive W1 lane promotes the existing
deterministic recursive retrieval/orchestration foundation into an explicit
runtime rollout slice without widening into semantic cache, recursive learning,
provider-side chain-of-thought, or public/API contract drift.

**Invariants Affected:**
- [ ] One BMI Engine
- [x] Thin HTTP Adapter Policy
- [x] Layer Separation
- [x] Contract-First
- [x] Other: bounded Wave 6 product-AI runtime rail

**Risks:**
1. Scope drift could reopen aspirational recursive roadmap phases instead of
   shipping the bounded recursive retrieval/orchestration lane already present
   in `main`; mitigate by limiting W1 to recursive retrieval, orchestration,
   runtime surfacing, and deterministic verification diagnostics only.
2. Recursive rollout could weaken the cost/safety envelope and turn into an
   uncontrolled latency/cost multiplier; mitigate by preserving existing hop,
   refinement, verification, and timeout budgets as hard boundaries.
3. Recursive verification signals could drift away from the canonical
   `VerificationBundle` contract added in `PR-V1`; mitigate by reusing the
   existing registry/orchestration bundle path instead of inventing a second
   validation stack.
4. Public/runtime claims could overstate quality or latency gains; mitigate by
   treating all uplift claims as benchmark-gated hypotheses and keeping replay /
   publication evidence out of scope for this PR.

**Proposed Approach:**
1. Create a dedicated A7 lane packet and reconcile recursive live-code truth
   against the current orchestration/runtime seams.
2. Keep recursive execution bounded to the existing deterministic retrieval path
   in `core/rag/recursive_retrieval.py` and its orchestration/runtime handoff.
3. Preserve the current feature-flag and app-service ownership seams while
   tightening deterministic diagnostics and bounded recursive verification
   behavior where needed.
4. Add deterministic tests on the canonical recursive surfaces and keep public
   payload/OpenAPI behavior unchanged.
5. Keep semantic cache, recursive learning, provider-side reasoning expansion,
   and broader experimentation claims out of scope.

**Evidence / Current-head anchors:**
- Deterministic recursive retrieval and bounded verification path:
  `core/rag/recursive_retrieval.py:338-510`
- Orchestration/runtime handoff plus `VerificationBundle` assembly:
  `core/rag/orchestration.py:254-380`, `core/rag/orchestration.py:526-572`
- Prepared recursive rollout authority seam:
  `core/ai/insight_runtime.py:47-75`, `core/ai/insight_runtime.py:173-231`
- Thin application/runtime feature-flag handoff:
  `app/services/insight_application_service.py:145-210`,
  `app/services/insight_runtime.py:74-104`,
  `app/services/insight_runtime.py:138-218`
- Deferred semantic-cache boundary:
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:5-27`,
  `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:665-677`

**Agent Assignment:**
- **Primary:** `agent-coordinator` - owns scope, role order, synthesis, and DoD.
- **Secondary:** `architecture-specialist` - enforces bounded recursive seams and anti-drift review.
- **Secondary:** `data-scientist-agent` - reviews recursive verification framing and benchmark-claim boundaries.
- **Secondary:** `backend-engineer` - implements the bounded recursive runtime/orchestration changes.
- **Secondary:** `security-auditor` - verifies fail-closed budgets, feature flags, and no contract widening.
- **Secondary:** `qa-engineer-agent` - adds deterministic recursive-path tests.
- **Secondary:** `bug-hunter` - mandatory final defect pass.
- **Dependencies:** preflight and agent consistency must pass before edits; the
  canonical post-open `qa-engineer-agent -> bug-hunter` pass remains mandatory.

**Constraints:**
- No `legacy_app.py`, `app/routers/*`, OpenAPI, DTO, or response-shape changes.
- No semantic cache, Redis/GPTCache rollout, GraphRAG, ContextManifest, or
  recursive learning lane.
- No provider-side tree-of-thought or hidden reasoning feature expansion.
- No reopening `PR-V1`; the verification registry and verify-before-write
  contract remain in force and must be preserved.
- W1 stays bounded to recursive retrieval/orchestration/runtime surfacing; do
  not claim full recursive-framework completion in one PR.
- Any quality/latency uplift claims stay deferred until replay/benchmark
  evidence explicitly promotes them.

---

**Analysis by:** agent-coordinator
**Date:** 2026-04-22
