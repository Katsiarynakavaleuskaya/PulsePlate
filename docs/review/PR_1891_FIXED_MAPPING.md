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

## Fixed in Commit Mapping

No GitHub review threads have been resolved at PR open.

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
- `git push -u origin codex/user-coaching-state-service-v1`
  - PASS: pre-push backend pytest, Bandit full repo, and Docker build test passed.

## Post-Open Review Plan

Required before any readiness claim:

- post-open `qa-engineer-agent -> bug-hunter -> security-auditor`
- Codex Security diff scan / finding discovery
- `pulseplate-pr-review`
- current-head CI evidence
- CodeRabbit / Sourcery / Cubic disposition pass
- strict merge-readiness wrapper with auth

## Merge Readiness

Not claimed. This artifact records initial mapping and pre-open evidence only.
