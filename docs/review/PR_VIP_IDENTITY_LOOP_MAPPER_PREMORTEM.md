# VIP Identity Loop Mapper Runtime Premortem

## Summary

Plan: add the bounded VIP structured coaching runtime route
`POST /api/v1/vip/fitchef/insight` using existing FitChef structured-coach
guards, quota, orchestration, schemas, OpenAPI generation, and docs truth.

Frame: it is six months from now and this PR failed because a narrowly scoped
wellness runtime lane either drifted into unsafe coaching claims, bypassed
product-tier controls, or created contract truth that clients and governance
could not rely on.

## Findings And Closure

### PM-VIP-001: VIP route registration could bypass the canonical bootstrap seam

- Failure story: The route is added directly in `app/main.py` or as a duplicate
  router include. It works locally but is skipped or double-registered when
  `register_vip_routes(...)` controls the app bootstrap path.
- Underlying assumption: Adding a FastAPI route anywhere is equivalent to adding
  it through the VIP route registry.
- Early warning signs: OpenAPI contains duplicate methods for the same path, or
  route-count tests see more than one `POST /api/v1/vip/fitchef/insight`.
- Containment action: keep VIP structured registration inside
  `app/routers/vip_registration.py` and fail closed on foreign handlers.
- Disposition: FIXED
- Evidence: `app/routers/vip_registration.py` registers the structured VIP
  router idempotently and raises on a same-path foreign handler;
  `tests/vip/test_vip_diff_coverage.py` covers enabled, disabled,
  idempotent, and duplicate-handler behavior.

### PM-VIP-002: Identity-loop copy could imply diagnosis, therapy, or fixed identity labels

- Failure story: Provider output turns self-talk mapping into clinical or
  identity-labeling language. Users could read the response as diagnosis or
  therapy, violating the PulsePlate wellness-only boundary.
- Underlying assumption: JSON schema shape alone keeps the coaching language
  safe.
- Early warning signs: Response text contains diagnosis, treatment, therapy,
  crisis, or fixed-identity phrasing.
- Containment action: prompt with explicit wellness-only constraints, reject or
  rewrite unsafe structured text, and return non-clinical fallback language.
- Disposition: FIXED
- Evidence: `core/insight/fitchef_companion.py` builds a wellness-only,
  request-scoped prompt and rewrites unsafe drafts through
  `wellness_language_rewritten`; `tests/test_fitchef_companion_helpers.py`
  covers malformed JSON fallback and unsafe clinical-language fallback.

### PM-VIP-003: Product-tier, feature-flag, quota, or rate-limit ordering could fail open

- Failure story: The new VIP route calls runtime orchestration before VIP auth,
  feature-gate, safe-input, quota, or rate-limit checks. Non-VIP users or unsafe
  prompts could consume LLM quota or reach provider paths.
- Underlying assumption: Existing structured helper behavior automatically
  covers every new route.
- Early warning signs: Non-VIP requests return 200, disabled feature/mode still
  delegates to runtime, or quota tests do not prove hard 429 behavior.
- Containment action: keep route-level VIP auth, feature and mode gates,
  safe-input checks, SlowAPI limiting, and service-level monthly quota tests.
- Disposition: FIXED
- Evidence: `app/routers/fitchef_structured.py` gates the route with
  `require_vip_tier`, `FEATURE_FITCHEF_STRUCTURED_COACH`,
  `FITCHEF_STRUCTURED_COACH_EXECUTION_MODE`, `require_safe_ai_agent_input`, and
  `RATE_LIMIT_INSIGHT`; `tests/test_fitchef_structured_api.py` covers 403, 503,
  400, 429, timeout, fallback, and VIP quota delegation.

### PM-VIP-004: OpenAPI and generated client mirrors could drift from backend truth

- Failure story: The backend route ships but OpenAPI or generated frontend
  schema stays stale. Future client work then relies on incomplete contract
  truth or misses the VIP route entirely.
- Underlying assumption: Backend tests are enough for contract-visible runtime
  work.
- Early warning signs: `openapi.json` lacks the route, schema generation does
  not include `FitChefIdentityLoopMapperResponse`, or OpenAPI determinism fails.
- Containment action: regenerate OpenAPI mirrors and test the route contract.
- Disposition: FIXED
- Evidence: `frontend/src/api/openapi.json` and `frontend/src/api/schema.ts`
  include the VIP identity-loop route and schemas; `tests/test_fitchef_structured_api.py`
  asserts OpenAPI request/response refs, and `tests/test_openapi_determinism.py`
  passes with repo `.venv` on `PATH`.

### PM-VIP-005: Privacy and transparency docs could omit the new AI endpoint

- Failure story: The runtime endpoint is exposed, but compliance docs and
  transparency registries still list only the PRO Distortion route. Operators
  and reviewers then lack accurate user-facing disclosure.
- Underlying assumption: A second structured route does not change compliance
  surfaces because it reuses the same feature flag.
- Early warning signs: Privacy matrix or AI transparency registry mentions
  `/api/v1/pro/fitchef/explain` but not `/api/v1/vip/fitchef/insight`.
- Containment action: update code registries, legal/privacy docs, and contract
  tests together with the route.
- Disposition: FIXED
- Evidence: `core/compliance/privacy.py`, `core/compliance/transparency.py`,
  `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`,
  `docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`, and
  `docs/legal/Privacy.md` include the VIP route; `tests/test_compliance_control_plane.py`
  verifies registry and documentation coverage.

## Synthesis

Most likely failure: contract/compliance drift, because this PR adds backend
runtime plus generated contract mirrors and several repo-truth documents.

Most dangerous failure: unsafe identity-loop language, because it would break
the wellness-only product boundary even if the route behaved correctly.

Hidden assumption: reusing the existing structured-coach feature flag and
execution mode is safe only if the new route also reuses the same fail-closed
auth, quota, safety, transparency, and OpenAPI contracts.

Revised plan: proceed with the implemented changes above, keep the route inside
VIP registration, keep the runtime bound to `corpus://cbt-agent` and `VIP`, and
leave Signal vs Noise, chat, week-repair, semantic cache, GraphRAG, frontend UI,
iOS, DB, food-data, billing, and plan adaptation out of scope.

## Pre-Merge Checklist

- Focused FitChef runtime, structured API, compliance, VIP registration, and
  OpenAPI tests pass.
- `make validate-changed` passes from the fresh worktree.
- `pre-commit run --all-files` passes before push.
- Experiment Runner oracle evidence is recorded before PR open.
- PR fixed mapping mirrors premortem, role-agent, Experiment Runner, bot, Codex
  Security, and custom review findings after fixes or dispositions.

## Decision

Proceed with changes.
