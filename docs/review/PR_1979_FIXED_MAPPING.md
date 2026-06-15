# PR 1979 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979>

## Summary

This guard-compatibility lane makes the ruff dependency guard derive the
expected ruff version from `requirements-dev.in` instead of hard-coding the
previous exact pin. The guard still requires the generated and constraint
surfaces to match that source and still forbids a ruff emergency wheel fallback.

This is a prerequisite for the Dependabot ruff lane (#1973). Raw #1973 remains
blocked separately because it includes broad `requirements-lock.txt` resolver
churn and adds `pip==26.1.2`.

## Lane Start Provenance

- Branch: `codex/ruff-guard-manifest-parity`
- Base at branch start: `eabf69ecc8ed288c718239d09579fd61f4cd879a`
- Initial implementation commit:
  `ea74f14fb2d6c9d7d4efff268f624a2334f7c84f`
- Initial mapping artifact commit:
  `ea52cf7cfb6758163b5c66f3e5c440b42a64f0a8`
- Task packet: `artifacts/orchestration/task_packets/1a8d6fe97dcc.json`
- Experiment Runner packet:
  `artifacts/orchestration/experiments/exp-9bd8f13b42ee.json`
- Experiment Runner accepted result:
  `artifacts/orchestration/experiments/results/exp-9bd8f13b42ee.json`
- Machine-heavy exception: full local `make verify` intentionally deferred
  under the operator-approved dependency/security lane scope. Focused local
  gates and current-head CI remain required before merge readiness.

## Discussion Thread Pass

- [x] Discussion-thread pass initialized.
- [x] Fixed in commit mapping initialized.
- No actionable review comments yet.
- Post-open review loop remains required:
  `qa-engineer-agent -> bug-hunter -> security-auditor`, followed by Codex
  Security diff scan / finding discovery and `pulseplate-pr-review`.

### Fixed in Commit Mapping

- No actionable review comments yet.

## Role Dispatch Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/check_preflight.py --path tests/test_install_locked_python_requirements.py`
- PASS: role dispatch manifest from packet
  `artifacts/orchestration/task_packets/1a8d6fe97dcc.json`
- Pre-open role order completed before implementation:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> architecture-specialist`.
- `agent-coordinator`: blocked raw #1973 and required separate guard-compat
  work because the Dependabot branch carries resolver churn and `pip==26.1.2`.
- `qa-engineer-agent`: accepted deriving ruff from `requirements-dev.in` and
  required focused dependency guard coverage.
- `bug-hunter`: required existing parsers instead of ad hoc regexes and no new
  stale ruff literal.
- `security-auditor`: required no changes to manifests, lockfiles, emergency
  wheels, installer scripts, or torch waiver docs.
- `cursor-specialist-agent`: required non-draft PR, PR-numbered mapping, and
  post-open review loop.
- `architecture-specialist`: confirmed `requirements-dev.in` is the source
  surface and generated/constraint files are parity surfaces.

## Premortem Finding Closure

- PM-001: Deriving from generated lockfiles could bless resolver churn.
Disposition: FIXED
Commit: `ea74f14fb2d6c9d7d4efff268f624a2334f7c84f`
Evidence: `tests/test_install_locked_python_requirements.py` derives
`expected_ruff_version` from `requirements-dev.in` and compares other ruff
surfaces to that value.

- PM-002: Guard change could weaken emergency fallback or private-index
guarantees.
Disposition: FIXED
Commit: `ea74f14fb2d6c9d7d4efff268f624a2334f7c84f`
Evidence: the ruff emergency fallback assertion remains in
`tests/test_install_locked_python_requirements.py`; private-index preflight
passed with `scripts/ci/install_locked_python_requirements.py --preflight-only`.

- PM-003: Machine-heavy validation deferral could be under-documented.
Disposition: FIXED
Commit: `ea52cf7cfb6758163b5c66f3e5c440b42a64f0a8`
Evidence: this artifact records the local `make verify` deferral and the focused
validation bundle required for the operator-approved exception.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-9bd8f13b42ee.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Contribution: `oracle_review`
- Co-author required: true; implementation commit includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Accepted oracle commands:
  - `python3 -m pytest -q tests/test_install_locked_python_requirements.py -k 'ruff_private_proxy_pin or quality_tooling_profile'`
  - `python3 -m pytest -q tests/test_dependency_security_guard.py -k repo_managed_lock_surfaces_do_not_pin_pip`

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_preflight.py --path tests/test_install_locked_python_requirements.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`
- PASS: `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py -k 'ruff_private_proxy_pin or quality_tooling_profile'`
  (`2 passed`)
- PASS: `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py -k repo_managed_lock_surfaces_do_not_pin_pip`
  (`1 passed`)
- PASS: `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py`
- PASS: `make validate-changed`
  (reported no selected diff tests; focused pytest above is the concrete local
  coverage for this test-only guard change)
- PASS: `pre-commit run --all-files`
- PASS during push hooks: `pip-audit`, backend pre-push pytest, and full-repo
  Bandit.

## Merge Readiness

Merge readiness is not claimed by this artifact alone. Required remaining proof:

- post-open role loop:
  `qa-engineer-agent -> bug-hunter -> security-auditor`;
- Codex Security diff scan / finding discovery;
- `pulseplate-pr-review`;
- current-head PR CI for the latest pushed head;
- PR-body Phase2 and mapping guards after this artifact is committed and the PR
  body mirror is refreshed;
- strict merge-readiness wrapper with GitHub auth;
- no unresolved review threads or actionable bot comments;
- mandatory wait-window after the latest bot/review activity.

## Risks / Rollback

- Risk: deriving from the wrong surface would make the guard self-referential.
  Mitigation: the expected ruff version is derived only from `requirements-dev.in`.
- Risk: future Dependabot updates could still include unrelated resolver churn.
  Mitigation: this PR does not merge #1973; the later ruff dependency lane must
  keep a clean ruff-only diff with no `pip==...` pin.
- Rollback: revert this PR. It changes tests only and does not alter runtime or
  dependency state.
