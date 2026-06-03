# VIP Identity Loop Mapper - Experiment Runner Evidence Summary

## Purpose

Committed summary for the local Experiment Runner oracle result used by this
VIP Identity Loop Mapper runtime PR. Raw Experiment Runner JSON artifacts remain
under gitignored `artifacts/` by repo policy, so this document records the
verifiable fields used for PR governance without tracking local runtime
artifacts.

## Local Result

- Path: `artifacts/orchestration/experiments/results/exp-feb0c1afe33f.json`
- SHA-256: `fc656c877423e933985cd8efa1f33bed0b25344cb4044e93b46a8c3dd05c2be6`
- Experiment ID: `exp-feb0c1afe33f`
- Runner mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Failure class: `None`
- Mutated paths in the raw local result: `[]`
- Shared tree untouched: `true`
- Contribution kind: `commit_decision`
- Co-author required: `true`
- Co-author reason: mandatory pre-open Experiment Runner oracle review shaped
  the PR commit decision and review evidence for the VIP Identity Loop Mapper
  runtime.

## Source Diff Paths

- `app/routers/fitchef_structured.py`
- `app/routers/vip_registration.py`
- `app/services/fitchef_runtime.py`
- `core/compliance/privacy.py`
- `core/compliance/transparency.py`
- `core/insight/fitchef_companion.py`
- `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
- `docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`
- `docs/contracts/API_CANONICAL_MAP.md`
- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`
- `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
- `docs/contracts/PRODUCT_TIER_MAP.md`
- `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
- `docs/legal/Privacy.md`
- `docs/review/PR_VIP_IDENTITY_LOOP_MAPPER_PREMORTEM.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `frontend/src/api/openapi.json`
- `frontend/src/api/schema.ts`
- `tests/test_compliance_control_plane.py`
- `tests/test_fitchef_companion_helpers.py`
- `tests/test_fitchef_structured_api.py`
- `tests/test_rate_limit_llm_and_exports_api.py`
- `tests/vip/test_vip_diff_coverage.py`

## Oracle Commands

- `python -m pytest -q tests/test_fitchef_structured_contracts.py tests/test_fitchef_structured_api.py tests/test_fitchef_companion_helpers.py tests/test_rate_limit_llm_and_exports_api.py tests/test_pro_vip_route_dependency_guard.py tests/test_compliance_control_plane.py tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py tests/vip/test_vip_diff_coverage.py`
  - PASS, return code 0.
- `python scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/insights/CBT_COACHING_PRODUCT_WAVE.md docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md docs/contracts/API_CANONICAL_MAP.md docs/contracts/PRODUCT_TIER_MAP.md docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md docs/legal/Privacy.md`
  - PASS, return code 0.

## Attribution Scope

Because this accepted oracle result materially shaped the commit decision and
review evidence, the branch commit must include:

`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

This evidence summary does not replace coordinator, role-agent, review-thread,
current-head CI, fixed-mapping, or merge-readiness gates.
