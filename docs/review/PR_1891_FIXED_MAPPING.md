# PR #1891 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891
Branch: `codex/user-coaching-state-service-v1`
Title: `feat(fitchef): add coaching state service v1`

## Scope

Service-only backend personalization foundation for FitChef:

- internal Pydantic v2 coaching-state schemas
- internal builder over canonical analyzer state and bounded nutrition-event aggregates
- prompt-safe serializer projection
- deterministic schema, builder, serializer, and service-only guard tests

Out of scope:

- public route or OpenAPI exposure
- generated client changes
- FitChef prompt/runtime injection
- semantic cache, RAG, RL, MDP, hidden memory, or public prompt injection
- client-declared BMI/goal/nutrition truth

## Pre-Open Governance

- Startup preflight: `python3 scripts/orchestration/check_preflight.py` PASS.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- Task bootstrap packet: `artifacts/orchestration/task_packets/d7b9ed048df2.json`.
- Role dispatch bridge: packet order verified with no missing agents.
- Required pre-open role order completed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> backend-engineer`.
- Premortem skill: `pulseplate-premortem-risk-review`.
- Premortem artifact: `artifacts/orchestration/premortem/user-coaching-state-service-v1-premortem.md`.
- Premortem decision: `proceed with changes`; all findings are FIXED by
  `f93432ee6` and validation evidence.
- Experiment Runner oracle-only packet:
  `artifacts/orchestration/experiments/exp-6992ef258dec.json`.
- Experiment Runner result:
  `artifacts/orchestration/experiments/results/exp-6992ef258dec.json`.
- Experiment Runner status: `accepted`, shared tree untouched,
  contribution kind `none`, no coauthor required.

## Implementation Commits

- `f93432ee6` - `feat(fitchef): add coaching state service v1`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- PR-open state initially had no resolved GitHub review threads; post-open bot
  findings are dispositioned in the canonical mapping below.
- Merge readiness is not claimed while unresolved threads, current-head CI, and
  strict merge-readiness checks remain open.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#pullrequestreview-4438107720 -> e2ce99e51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#discussion_r3364169298 -> e2ce99e51
Disposition: FIXED
Commit: e2ce99e51
Evidence: docs/review/PR_1891_FIXED_MAPPING.md now keeps only GitHub review URLs and disposition proof in Fixed in Commit Mapping; internal findings moved to Internal Finding Dispositions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#discussion_r3364145266 -> e0db06bc3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#discussion_r3364186147 -> e0db06bc3
Disposition: FIXED
Commit: e0db06bc3
Evidence: app/services/coaching_state_builder.py catches TypeError and ValueError for malformed analyzer rows and tests/test_user_coaching_state.py covers invalid payload degradation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#discussion_r3365164918 -> 1f670a217
Disposition: FIXED
Commit: 1f670a217
Evidence: app/services/coaching_state_builder.py validates raw analyzer payload values before service coercion and tests/test_user_coaching_state.py covers booleans plus fractional n degradation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#pullrequestreview-4438128739 -> 32790a0f6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#discussion_r3364186146 -> 32790a0f6
Disposition: FIXED
Commit: 32790a0f6
Evidence: docs/review/PR_1891_FIXED_MAPPING.md records f93432ee6 as the existing implementation proof commit and no longer references the stale b7355f8f9 SHA.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#discussion_r3364995580
Disposition: NOT-A-BUG
Evidence: git branch --contains f93432ee6 includes codex/user-coaching-state-service-v1 and git log shows f93432ee6 is an ancestor of the PR branch.
Reason: The comment evaluated stale reviewed-SHA context after the rebase; current PR ancestry contains f93432ee6.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1891#discussion_r3365238389
Disposition: NOT-A-BUG
Evidence: gh pr view reports headRefOid 180bf712053532edaedafa9f426b1bd058525d00 and git merge-base --is-ancestor returned 0 for e2ce99e51, e0db06bc3, and 1f670a217 against HEAD.
Reason: The review referenced synthetic or stale head 44fe7963394bbddf6710b0c42170c1cb8fdd04e7, not the published PR branch head.

## Internal Finding Dispositions

Premortem / role-agent findings closed before PR open:

- PM-UCS-001 public/runtime surface widening -> `f93432ee6`
  - Disposition: FIXED.
  - Evidence: `tests/test_user_coaching_state.py:538` guards against
    public route, OpenAPI, client, FitChef runtime, semantic cache, RAG, RL,
    MDP, and write-path wiring.
- PM-UCS-002 raw text / PII-like / API-key-like / medical-claim leakage ->
  `f93432ee6`
  - Disposition: FIXED.
  - Evidence: `app/services/coaching_state_builder.py:204` uses a static
    prompt-safe allowlist; `tests/test_user_coaching_state.py:220` proves raw
    event text, PII-like values, API-key-like values, therapy terms, and
    medical claims are excluded.
- PM-UCS-003 caller-supplied derived state injection -> `f93432ee6`
  - Disposition: FIXED.
  - Evidence: `tests/test_user_coaching_state.py:500` proves frozen strict
    models and derived-field recomputation ignore caller-supplied values.
- PM-UCS-004 bounded aggregation cap/order/payload edges -> `f93432ee6`
  - Disposition: FIXED.
  - Evidence: `app/services/coaching_state_builder.py:29` sets the event scan
    cap; `app/services/coaching_state_builder.py:96` orders by
    `created_at desc, id desc`; `tests/test_user_coaching_state.py:461`
    covers missing/nonnumeric day-close scores.
- PM-UCS-005 false branch-diff validation before commit -> `f93432ee6`
  - Disposition: FIXED.
  - Evidence: post-commit `make validate-changed` selected
    `tests/test_user_coaching_state.py` and passed with `14 passed`;
    `pre-commit run --all-files` passed; `git status --short` was clean.

## Validation Evidence

- Rebased implementation proof commit: `f93432ee6` on top of
  base `9252c6c6292ebc1ae18a2f7d63e199919cbe1c96`.
- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `. .venv/bin/activate && python -m pytest -q tests/test_user_coaching_state.py tests/test_bayes_adherence_model.py tests/test_bayes_adherence_service.py tests/test_nutrition_log_idempotency.py`
  - PASS: `36 passed`.
- `.venv/bin/python -m mypy app/schemas/user_coaching_state.py app/services/coaching_state_builder.py tests/test_user_coaching_state.py --no-incremental --cache-dir=/dev/null`
  - PASS.
- `.venv/bin/python -m flake8 app/schemas/user_coaching_state.py app/services/coaching_state_builder.py tests/test_user_coaching_state.py`
  - PASS.
- `.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py tests/test_no_bmi_logic_in_paywall.py`
  - PASS: `20 passed`.
- `.venv/bin/python -m pytest -q tests/test_openapi_determinism.py::test_register_pro_routes_is_idempotent tests/test_openapi_determinism.py::test_prune_unreferenced_schema_components_ignores_missing_components`
  - PASS: `2 passed`.
- `make validate-changed`
  - PASS: selected `tests/test_user_coaching_state.py`, `14 passed`.
- `pre-commit run --all-files`
  - PASS.
- `pre-commit run --all-files` from isolated PR worktree after rebase
  - PASS.
- `git push --force-with-lease origin codex/user-coaching-state-service-v1`
  - PASS: pre-push backend pytest, Bandit full repo, and Docker build test passed.

## Post-Open Evidence

- Post-open task packet: `artifacts/orchestration/task_packets/269d25c63e9a.json`.
- Role dispatch bridge: PASS; mandatory post-open role agents reported as
  `qa-engineer-agent`, `bug-hunter`, `security-auditor`.
- `qa-engineer-agent`: PASS for code/test review.
  - Evidence: QA reran preflight, agent consistency, focused pytest,
    focused mypy/flake8, and `make validate-changed`; no actionable schema,
    builder, serializer, or deterministic-test blockers.
- `bug-hunter`: BLOCK then FIXED.
  - Initial adapter issue: existing bug-hunter agent returned empty completion
    payload twice; first replacement adapter errored with usage-limit exhaustion.
  - Replacement pass: completed on current PR head and produced three findings.
  - Finding 1: local absolute path in review artifact.
    - Disposition: FIXED.
    - Commit: `e0db06bc3`.
    - Evidence: `docs/review/PR_1891_FIXED_MAPPING.md` now uses relative
      isolated-worktree wording; local-path guard rerun is part of the required
      validation bundle below.
  - Finding 2: malformed analyzer state did not fully degrade.
    - Disposition: FIXED.
    - Commit: `e0db06bc3`.
    - Evidence: `app/services/coaching_state_builder.py` now catches malformed
      analyzer reads and validates finite `alpha`, `beta`, `risk_slip`, and
      `confidence` before snapshot construction; regression coverage in
      `tests/test_user_coaching_state.py`.
  - Finding 3: `model_copy(update=...)` could inject derived prompt fields.
    - Disposition: FIXED.
    - Commit: `e0db06bc3`.
    - Evidence: `to_prompt_safe_context(...)` revalidates/recomputes the state
      before projection; regression coverage in `tests/test_user_coaching_state.py`.
  - Fix validation run:
    `.venv/bin/python -m pytest -q tests/test_user_coaching_state.py tests/test_bayes_adherence_model.py tests/test_bayes_adherence_service.py`
    PASS: `28 passed`.
  - Focused mypy/flake8: PASS.
- `security-auditor`: PASS for code; governance finding FIXED.
  - Code review: no blockers for prompt safety, raw payload leakage, cross-user
    reads, malformed analyzer degradation, derived-field injection, persistence
    writes, public route/OpenAPI/client/runtime/cache widening, or wellness-only
    boundaries.
  - Finding: tracked review artifact recorded local `/tmp` paths.
    - Disposition: FIXED.
    - Commit: `fd0eed936`.
    - Evidence: local-only artifact paths are omitted from the tracked mapping;
      the security-auditor local-path hygiene grep returned no matches.
  - Codex Security rerun after `e0db06bc3`: PASS / no findings.
    - Local-only artifact id: `7bd80b60_pr1891_20260605T201151Z`.
    - Coverage: 2 of 2 diff-scoped source-like rows completed.
- Codex Security diff scan: PASS / no findings.
  - Local-only artifact id: `b4cf8acb_pr1891_20260605T194527Z`.
  - Local report paths are intentionally omitted from this tracked review
    artifact.
  - Coverage: 2 of 2 diff-scoped source-like rows completed.
- `pulseplate-pr-review` dry run: completed.
  - Local-only dry-run markdown/json artifacts retained outside git.
  - Finding: large-diff advisory note.
  - Disposition: NOT-A-BUG.
  - Evidence: diff is one coherent service-only slice; implementation files are
    `app/schemas/user_coaching_state.py` and
    `app/services/coaching_state_builder.py`, with deterministic tests in
    `tests/test_user_coaching_state.py` and review artifact
    `docs/review/PR_1891_FIXED_MAPPING.md`. Rebased-head focused pytest,
    mypy, flake8, `make validate-changed`, `pre-commit run --all-files`, and
    pre-push hooks passed.

## Post-Open Review Plan

Required before any readiness claim:

- close post-open `bug-hunter -> security-auditor`
- current-head CI evidence
- CodeRabbit / Sourcery / Cubic disposition pass
- strict merge-readiness wrapper with auth

## Merge Readiness

Not claimed. This artifact records initial mapping and pre-open evidence only.
