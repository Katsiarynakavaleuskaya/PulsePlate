# PR 2086 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2086

Branch: `codex/fix-main-premium-wrapper-route-tests`

## Summary

This PR fixes post-merge `main` CI failures in the legacy premium nutrition
route-family wrapper delegation tests. It changes test monkeypatch targets from
the potentially stale `app_main._legacy_module` alias to the live runtime
`legacy_app` module that the wrappers import at call time.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2086#pullrequestreview-4637062224 -> 03e4af380f7bef767e108b078007af641dacefcd
Commit: 03e4af380f7bef767e108b078007af641dacefcd
Evidence: `tests/test_route_family_bootstrap.py:20`, `tests/test_legacy_premium_nutrition_registration_bootstrap.py:21`, `tests/helpers/module_resolve.py:7`, `tests/helpers/module_resolve.py:17`
Reason: The duplicated local `_runtime_legacy_module()` helpers were removed and both test files now reuse the existing shared runtime module resolver.

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2086#pullrequestreview-4637102071 -> 03e4af380f7bef767e108b078007af641dacefcd
Commit: 03e4af380f7bef767e108b078007af641dacefcd
Evidence: `tests/test_route_family_bootstrap.py:20`, `tests/test_legacy_premium_nutrition_registration_bootstrap.py:21`, `tests/helpers/module_resolve.py:7`, `tests/helpers/module_resolve.py:17`
Reason: CodeRabbit's duplicate-helper and type-precision feedback is addressed by reusing `resolve_legacy_app()`, whose shared helper returns `ModuleType`.

Disposition: NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2086#pullrequestreview-4637062224
Evidence: `tests/helpers/module_resolve.py:7`, `tests/helpers/module_resolve.py:10`, `tests/helpers/module_resolve.py:14`
Reason: Caching the imported `legacy_app` module would weaken the regression guard. The original `main` failure came from stale module identity under purge/reload order, so these tests must resolve the module at monkeypatch time.

## Implementation Evidence

Disposition: FIXED
Commit: e0da71dd3bb0f30a3b220f4d0d9c3a219c5810ca
Evidence: `tests/test_route_family_bootstrap.py:20`, `tests/test_route_family_bootstrap.py:263`, `tests/test_legacy_premium_nutrition_registration_bootstrap.py:21`, `tests/test_legacy_premium_nutrition_registration_bootstrap.py:236`, `tests/helpers/module_resolve.py:17`
Reason: Post-merge `main` CI showed that six wrapper delegation tests patched a stale legacy module alias under full-suite import/reload order. The fix resolves the live `legacy_app` module before patching the six delegate handlers while preserving object-identity and request-identity assertions.

## Main CI Failure Evidence

- `main` CI run: https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28796797871
- Failed job: `test-main (3.11, 60)` / job `85389472234`.
- Failed job: `test-main (3.12, 90)` / job `85389472322`.
- Failure class: six failures in `tests/test_route_family_bootstrap.py` where
  `assert response is expected` failed because real legacy responses were
  returned instead of monkeypatched fake delegates.

## Role-Agent Evidence

- Lane packet: `artifacts/orchestration/task_packets/8dcf55324443.json`
- Pre-open role order completed:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`.
- Security-auditor verdict: no production files changed; no auth, tier,
  API-key, OpenAPI, or route-registration behavior changed; no skip, xfail,
  nosec, type-ignore, pragma weakening, or fail-open pattern introduced.

## Premortem Evidence

- Artifact:
  `artifacts/orchestration/premortem/fix-main-premium-wrapper-route-tests-premortem.md`
- Decision: `proceed with changes`; patch the live runtime module and require
  current-head CI as the heavy matrix signal.

## Experiment Runner Evidence

Packet:
`artifacts/orchestration/experiments/artifacts/orchestration/experiments/fix-main-premium-wrapper-route-tests-oracle-packet.json`

Artifact:
`artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/fix-main-premium-wrapper-route-tests-oracle-result.json`
- Experiment id: `exp-1287ead84df4`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution kind: `oracle_review`
- `coauthor_required=true`
- Commit carrying required trailer:
  `e0da71dd3bb0f30a3b220f4d0d9c3a219c5810ca`
- Oracle commands passed:
  - `python3 -m pytest -q tests/test_route_family_bootstrap.py tests/test_legacy_premium_nutrition_registration_bootstrap.py -k "wrapper_delegates"`
  - `python3 -m pytest -q tests/test_route_family_bootstrap.py tests/test_legacy_premium_nutrition_registration_bootstrap.py`

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `git diff --check` - PASS.
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_route_family_bootstrap.py tests/test_legacy_premium_nutrition_registration_bootstrap.py -k 'wrapper_delegates'` - PASS, `12 passed`.
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_route_family_bootstrap.py tests/test_legacy_premium_nutrition_registration_bootstrap.py` - PASS, `45 passed`.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS.
- Push hook - PASS, including backend pre-push tests, full-repo Bandit,
  pip-audit, and Docker build test skip/no files.

## Merge Readiness

Not claimed here. Requires current-head GitHub CI on PR #2086, strict
merge-readiness wrapper, bot/review disposition pass, and post-open role/security
review chain.
