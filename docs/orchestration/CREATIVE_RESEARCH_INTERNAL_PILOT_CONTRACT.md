# Creative Research Internal Pilot Contract

**Purpose:** Define the bounded runtime shape for `PR-C` of the governed
`creative_research` sub-lane.

**Status:** Internal-only pilot. Hidden from public OpenAPI. No public product
surface is created by this contract.

---

## Canonical references

- Umbrella experimentation SoT:
  `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- Creative sub-lane SoT:
  `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`
- Offline eval overlay:
  `docs/orchestration/CREATIVE_RESEARCH_OFFLINE_EVAL_PROTOCOL.md`
- Offline eval contract:
  `docs/orchestration/contracts/CREATIVE_RESEARCH_EVAL_CONTRACT.md`

---

## 1. Runtime surface

- Canonical hidden path:
  `/api/v1/internal/creative-research/pilot`
- Router module:
  `app/routers/creative_research_internal.py`
- Runtime service:
  `app/services/creative_research_runtime.py`
- Shared evaluation SoT:
  `core/creative_research.py`

Rules:

- `include_in_schema=False`
- hidden from public OpenAPI
- internal namespace only
- no new `/api/v1/pro/*`, `/api/v1/vip/*`, or public `/api/v1/insight/*`
  product surface

---

## 2. Policy gates

- Feature flag:
  `FEATURE_CREATIVE_RESEARCH_PILOT`
- Execution mode env:
  `CREATIVE_RESEARCH_EXECUTION_MODE`
- Tier gate:
  VIP API key required
- Input safety:
  `require_safe_ai_agent_input(...)` for prompt seed and reference corpus items
- Rate limiting:
  `RATE_LIMIT_INSIGHT`
- Monthly hard quota:
  `attempt_consume_llm_monthly_quota(..., tier="VIP")` before provider call

Fail-closed outcomes:

- feature disabled -> `503`
- execution review-required / blocked -> `503`
- quota exhausted -> `429`
- invalid provider payload -> `503`
- provider timeout -> `504`

---

## 3. Bounded pilot shape

The pilot intentionally uses one provider-backed divergence call and then applies
deterministic evaluation from the PR-B contract.

Budget state returned to internal callers:

- `max_branches = 6`
- `max_total_llm_calls = 10`
- `max_recursive_depth = 2`
- `max_retrieval_hops = 2`
- `llm_calls_used = 1`

Notes:

- provider generation is bounded to a single call in PR-C
- reference corpus input is clipped to the pilot retrieval-hop budget
- evaluation and promote/defer/discard logic remains deterministic

---

## 4. Tracing and audit

- route-level agent span with feature-flag metadata only
- LLM span uses prompt/completion fingerprints and lengths only
- no raw prompts or completions in trace metadata
- privileged provider call writes signed audit metadata with prompt hash/length,
  not raw text

This pilot must not create a second orchestration telemetry plane.

---

## 5. Output semantics

Returned candidates must still follow the governed creative research contract:

- `claim`
- `mechanism`
- `evidence_needed`
- `falsifier`
- `confidence`
- `known_risks`
- `wellness_boundary`

Deterministic evaluation still decides:

- output class
- scorecard
- negative controls
- `promote | defer | discard`

If grounding is weak, presentation must degrade to:

- `interesting but unverified hypothesis`

---

## 6. Non-goals

- no public creativity endpoint
- no hidden memory promotion
- no autonomous merge/push/continuation
- no mutable evaluation oracle writes
- no orchestration recursion beyond the bounded pilot metadata
