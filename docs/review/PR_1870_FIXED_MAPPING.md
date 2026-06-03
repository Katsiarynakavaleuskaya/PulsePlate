# PR #1870 Fixed in Commit Mapping

## Summary

This PR adds the bounded VIP Identity Loop Mapper structured runtime at
`POST /api/v1/vip/fitchef/insight`.

The lane stays backend/runtime and contract-scoped: no Signal vs Noise, chat,
week-repair, semantic cache, GraphRAG, DB, frontend UI, iOS, Slack commands,
billing, food-data ingest, or plan-adaptation implementation is included.

## Lane Start Provenance

- Branch: `codex/vip-identity-loop-mapper-runtime`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Packet: `artifacts/orchestration/task_packets/93065865e7bb.json`
- Pre-open packet: `artifacts/orchestration/task_packets/93065865e7bb.json`
- Role order preserved: `agent-coordinator -> architecture-specialist -> backend-engineer -> wellness-analyst-agent -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Implementation commit: `0220fd4cef9f2a6eea61194ba0c483a8f9a3dfe1`

## Experiment Runner Evidence

- Summary: `docs/review/PR_VIP_IDENTITY_LOOP_MAPPER_EXPERIMENT_RUNNER_EVIDENCE.md`
- Artifact: `artifacts/orchestration/experiments/results/exp-feb0c1afe33f.json`
- Local raw artifact: `artifacts/orchestration/experiments/results/exp-feb0c1afe33f.json`
- Status: accepted
- Mode: `oracle_only_governance_reviewer`
- Mutation boundary: `mutated_paths=[]`, `shared_tree_untouched=true`, `promotion_ready=false`
- Co-author: required and present on commit `0220fd4cef9f2a6eea61194ba0c483a8f9a3dfe1`

## Premortem Closure

- Summary: `docs/review/PR_VIP_IDENTITY_LOOP_MAPPER_PREMORTEM.md`
- PM-VIP-001: VIP route registration could bypass the canonical bootstrap seam.
  - Disposition: FIXED
  - Commit: `0220fd4cef9f2a6eea61194ba0c483a8f9a3dfe1`
  - Evidence: `app/routers/vip_registration.py`; `tests/vip/test_vip_diff_coverage.py`
- PM-VIP-002: Identity-loop copy could imply diagnosis, therapy, or fixed identity labels.
  - Disposition: FIXED
  - Commit: `0220fd4cef9f2a6eea61194ba0c483a8f9a3dfe1`
  - Evidence: `core/insight/fitchef_companion.py`; `tests/test_fitchef_companion_helpers.py`
- PM-VIP-003: Product-tier, feature-flag, quota, or rate-limit ordering could fail open.
  - Disposition: FIXED
  - Commit: `0220fd4cef9f2a6eea61194ba0c483a8f9a3dfe1`
  - Evidence: `app/routers/fitchef_structured.py`; `app/services/fitchef_runtime.py`; `tests/test_fitchef_structured_api.py`; `tests/test_rate_limit_llm_and_exports_api.py`
- PM-VIP-004: OpenAPI and generated client mirrors could drift from backend truth.
  - Disposition: FIXED
  - Commit: `0220fd4cef9f2a6eea61194ba0c483a8f9a3dfe1`
  - Evidence: `frontend/src/api/openapi.json`; `frontend/src/api/schema.ts`; `tests/test_fitchef_structured_api.py`; `tests/test_openapi_determinism.py`
- PM-VIP-005: Privacy and transparency docs could omit the new AI endpoint.
  - Disposition: FIXED
  - Commit: `0220fd4cef9f2a6eea61194ba0c483a8f9a3dfe1`
  - Evidence: `core/compliance/privacy.py`; `core/compliance/transparency.py`; `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`; `docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`; `docs/legal/Privacy.md`; `tests/test_compliance_control_plane.py`

## Discussion Thread Pass

- [x] Discussion-thread pass completed after post-open bot and role reviews.
- [x] Fixed in commit mapping completed after all post-open findings.
- Current state: post-open QA, bug-hunter, security-auditor, Codex Security,
  and `pulseplate-pr-review` completed for the current local head.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#discussion_r3347300272 -> a451eb9e741d7a6623f556d5fb93de9ed09a45ce
Disposition: FIXED
Commit: a451eb9e741d7a6623f556d5fb93de9ed09a45ce
Evidence: `app/services/fitchef_runtime.py` routes structured runtime provider generation through `_generate_with_timeout`; regression coverage: `tests/test_fitchef_structured_api.py::TestFitChefStructuredRuntimeCoverage::test_identity_runtime_supports_async_provider_generate`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#discussion_r3347300290 -> a451eb9e741d7a6623f556d5fb93de9ed09a45ce
Disposition: FIXED
Commit: a451eb9e741d7a6623f556d5fb93de9ed09a45ce
Evidence: `core/insight/fitchef_companion.py` rewrites unsafe fallback goal copy to `the current wellness goal`; regression coverage: `tests/test_fitchef_companion_helpers.py::test_prepare_identity_loop_mapper_draft_sanitizes_unsafe_goal_fallback`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#discussion_r3347300300 -> 5812072da2a62c2167f690c6a8327314114b84ca
Disposition: FIXED
Commit: 5812072da2a62c2167f690c6a8327314114b84ca
Evidence: `core/insight/fitchef_companion.py` normalizes high-distress homoglyphs and blocks crisis/euphemism phrases before route runtime delegation; regression coverage: `tests/test_fitchef_companion_helpers.py::test_identity_loop_mapper_detects_high_distress_boundary` and `tests/test_fitchef_structured_api.py::TestFitChefIdentityLoopMapperRoute::test_high_distress_euphemism_rejected_before_runtime`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#discussion_r3347623257 -> 9a9dc19fa3d1d76c7873346eb26415fd814087a2
Disposition: FIXED
Commit: 9a9dc19fa3d1d76c7873346eb26415fd814087a2
Evidence: `tests/vip/test_vip_diff_coverage.py` adds the missing `pytest.MonkeyPatch` parameter type and `-> None` return annotation; regression coverage: `tests/vip/test_vip_diff_coverage.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#pullrequestreview-4417515360 -> 9a9dc19fa3d1d76c7873346eb26415fd814087a2
Disposition: FIXED
Commit: 9a9dc19fa3d1d76c7873346eb26415fd814087a2
Evidence: CodeRabbit review-level actionable mirrors `discussion_r3347623257`; `tests/vip/test_vip_diff_coverage.py` adds the missing `pytest.MonkeyPatch` parameter type and `-> None` return annotation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#discussion_r3347961447 -> 78d7090e05b244c964bd92549681b90c7e84fef4
Disposition: FIXED
Commit: 78d7090e05b244c964bd92549681b90c7e84fef4
Evidence: `core/compliance/privacy.py` discloses `/api/v1/vip/fitchef/insight` in the pseudonymous security/rate-limit category and signed audit envelopes category; regression coverage: `tests/test_compliance_control_plane.py::test_privacy_payload_contains_additive_control_plane_fields`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#discussion_r3348341705 -> b33b9b6c5afac8a4784a3d2d6f5d2670532be5f6
Disposition: FIXED
Commit: b33b9b6c5afac8a4784a3d2d6f5d2670532be5f6
Evidence: `app/main.py` now passes `target_app` to `register_vip_routes(...)` inside `ensure_canonical_app_bootstrap`; regression coverage: `tests/test_fitchef_structured_api.py::test_canonical_bootstrap_registers_structured_route_idempotently` and `tests/test_main_paywall_bootstrap.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#discussion_r3348341731 -> b33b9b6c5afac8a4784a3d2d6f5d2670532be5f6
Disposition: FIXED
Commit: b33b9b6c5afac8a4784a3d2d6f5d2670532be5f6
Evidence: `app/routers/fitchef_structured.py` wraps VIP structured route-level/runtime `HTTPException` failures in the frozen `vip_error(...)` envelope, `app/schemas/fitchef_coaching.py` documents `FitChefVipCoachingErrorResponse`, and `frontend/src/api/openapi.json` plus `frontend/src/api/schema.ts` mirror the updated OpenAPI contract; regression coverage: VIP envelope assertions in `tests/test_fitchef_structured_api.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1870#discussion_r3348341734 -> b33b9b6c5afac8a4784a3d2d6f5d2670532be5f6
Disposition: FIXED
Commit: b33b9b6c5afac8a4784a3d2d6f5d2670532be5f6
Evidence: `scripts/ci/ci_risk_profile.py` now routes structured FitChef route/runtime/schema/test changes through `insight_ai`; regression coverage: `tests/test_ci_risk_profile.py::test_fitchef_structured_source_change_hits_insight_openapi_and_route_groups`.

## Post-Open Role-Agent Finding Closure

- `qa-engineer-agent`: FIXED in
  `a451eb9e741d7a6623f556d5fb93de9ed09a45ce`.
  - Findings: high-distress input could reach provider, async providers failed
    after quota consumption, fallback could echo unsafe food-morality goal copy,
    and PR governance body/mapping remained incomplete.
  - Evidence: focused route/runtime/helper tests passed; mapping/body closure is
    mirrored in this artifact and PR body.
- `bug-hunter`: FIXED in
  `4693539915263cce447ad16f7f65b24081f20c46`.
  - Findings: high-distress phrase coverage missed common wording and canonical
    bootstrap did not rehydrate the VIP structured route.
  - Evidence: high-distress boundary tests and canonical bootstrap idempotency
    tests cover `/api/v1/vip/fitchef/insight`.
- `security-auditor`: FIXED in
  `5812072da2a62c2167f690c6a8327314114b84ca`.
  - Findings: additional crisis/euphemism and homoglyph bypasses plus tracked
    review-artifact local-path leakage.
  - Evidence: expanded detector tests, route euphemism block test, and local-path
    scan over PR #1870 review artifacts.
- `Codex Security diff scan / finding discovery`: PASS.
  - Evidence: local gitignored Codex Security scan
    `5812072da2a62c2167f690c6a8327314114b84ca_20260603T095123Z` records 9/9
    deep-review worklist receipts and no reportable diff-scoped candidates.
- `pulseplate-pr-review`: FIXED/PASS after this artifact and the PR body mirror
  are updated.
  - Evidence: exact Phase 2 headings, fixed mapping, Experiment Runner artifact,
    lane provenance, scope/split approvals, and local-validation sections are
    present in this artifact/body pair before the final push.

## Current-Head CI Finding Closure

- `diff-coverage` on head `8e9325e840a406ae62937176016422a7c2fabfa5`:
  FIXED in `059a7a7f8`.
  - Finding: CI coverage-producing suites did not include the FitChef structured
    API/helper/contract tests or VIP route registration coverage, leaving the
    new runtime files below the 97% diff-cover threshold.
  - Evidence: `.github/workflows/ci.yml` routes FitChef structured tests through
    `insight_ai` and VIP route coverage tests through `route_contract_safety`;
    `tests/AGENTS.md` documents the routing contract;
    `tests/vip/test_vip_diff_coverage.py` covers the remaining VIP route lookup
    branch; local diff-cover reports 100% on changed Python lines.
- `pr_scope_guard` / PR size governance on head
  `059a7a7f8`: FIXED by PR body mirror.
  - Finding: adding `.github/workflows/ci.yml` for the CI coverage routing fix
    classified this already-open 28-file runtime PR as
    `privileged_ci_security_workflow`, requiring explicit operator-approved
    privileged scope evidence.
  - Evidence: PR body records `operator approval: approved for PR #1870.` and
    `privileged scope exception: approved for CI coverage-routing fix after
    current-head diff-coverage failure.`
- `pr_scope_guard` / PR size governance on head
  `269773851`: FIXED by PR body mirror.
  - Finding: generated `frontend/src/api/schema.ts` pushed the PR to 31 counted
    files, so oversized governance required an explicit emergency exception
    line in addition to the existing operator approval and split justification.
  - Evidence: PR body records `operator approval: approved for PR #1870.` and
    `emergency exception: approved for PR #1870 generated OpenAPI schema mirror
    after review-fix pushed counted file total to 31.`

## External Bot Review Status

- CodeRabbit: NOT-A-BUG for code scope; review was rate-limited and emitted no
  initial code finding. Later type-hint finding FIXED and mapped above.
- Sourcery: NOT-A-BUG for code scope; review was rate-limited and emitted no
  actionable code finding.
- Cubic: PASS / no issues found on remote head `bc39758c29881e4410f5aa63507f1ada9be604f8`.
- Codex connector: six actionable threads were FIXED and mapped above.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `PATH=.venv/bin:$PATH make openapi-check` - PASS
- `PATH=.venv/bin:$PATH python -m pytest -q tests/test_fitchef_structured_contracts.py tests/test_fitchef_structured_api.py tests/test_fitchef_companion_helpers.py tests/test_rate_limit_llm_and_exports_api.py tests/test_pro_vip_route_dependency_guard.py tests/test_compliance_control_plane.py tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py tests/vip/test_vip_diff_coverage.py` - PASS
- `PATH=.venv/bin:$PATH python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/insights/CBT_COACHING_PRODUCT_WAVE.md docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md docs/contracts/API_CANONICAL_MAP.md docs/contracts/PRODUCT_TIER_MAP.md docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md docs/legal/Privacy.md docs/review/PR_VIP_IDENTITY_LOOP_MAPPER_PREMORTEM.md docs/review/PR_VIP_IDENTITY_LOOP_MAPPER_EXPERIMENT_RUNNER_EVIDENCE.md` - PASS
- `PATH=.venv/bin:$PATH python3 scripts/ci/check_docs_phase1_gates.py --files docs/review/PR_1870_FIXED_MAPPING.md` - PASS
- Local coverage parity for the CI routing fix: `coverage run` over
  `tests/test_fitchef_insight_api.py`, FitChef structured tests, VIP route guard
  tests, and `tests/vip/test_vip_diff_coverage.py`; `diff-cover coverage.xml
  --compare-branch origin/main --fail-under 97` - PASS at 100%.
- `PATH=.venv/bin:$PATH make validate-changed` - PASS
- `PATH=.venv/bin:$PATH pre-commit run --all-files` - PASS
- `PATH=.venv/bin:$PATH make lint` - PASS
- `PATH=.venv/bin:$PATH make typecheck` - PASS
- `.venv/bin/python -m pytest -q tests/test_fitchef_structured_contracts.py tests/test_fitchef_structured_api.py tests/test_fitchef_companion_helpers.py tests/test_main_paywall_bootstrap.py tests/test_ci_risk_profile.py tests/test_compliance_control_plane.py tests/vip/test_vip_diff_coverage.py` - PASS
- `python3 scripts/orchestration/check_preflight.py` - PASS after review-fix diff
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS after review-fix diff
- Pre-push hooks - PASS, including changed-file mypy, pip-audit, backend pre-push tests, full-repo Bandit, and docker build test

## Merge Readiness

- [ ] Current-head CI terminal success confirmed.
- [x] Post-open role review completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [x] CodeRabbit / Sourcery / Cubic actionables checked and mapped or
  dispositioned as no-actionable/rate-limited.
- [ ] Strict review-thread disposition passes with auth.
- [ ] Strict merge-readiness guard passes with auth.
- [ ] Mandatory wait-window after latest bot/review activity completed.

## Deferred / Follow-ups

- Signal vs Noise remains `PR-TBD-SIGNAL-NOISE-REPORT-LANE`.
- FitChef chat and week-repair remain future VIP structured follow-ups.
- Semantic cache, GraphRAG, frontend UI, iOS, food-data, billing, DB, and plan adaptation remain separately gated lanes.
