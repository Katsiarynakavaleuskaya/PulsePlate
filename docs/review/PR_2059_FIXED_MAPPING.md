# PR #2059 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2059

Branch: `codex/deps-runtime-ownership-stability`

## Summary

This PR settles the residual runtime dependency ownership warning after PR
#2057 without reopening broad dependency cleanup.

It promotes `aiosqlite` to documented SQLite async fallback/local-dev/test
ownership, adds a dependency-sensitive private proxy root preflight guard,
fixes stale `pyarrow` data-profile wording, and leaves direct `numpy` runtime
authority as warning-only because lock regeneration introduced unrelated unsafe
`pip==` churn.

## Scope

- `scripts/ci/check_python_dependency_surfaces.py`: document `aiosqlite` via
  explicit `core/db.py` SQLite async fallback evidence.
- `scripts/orchestration/check_preflight.py`: warn/fail on malformed
  `PULSEPLATE_PYTHON_INDEX_URL` only in the dependency-sensitive modes/paths.
- `requirements-data.in`: fix stale `pyarrow` ownership wording after #2057.
- Dependency docs/tests: mirror the `aiosqlite` and `numpy` decisions.

## Out Of Scope

No DigitalOcean, site, snapshot, Docker runtime behavior, Starlette/httpx2,
FastAPI/Pydantic/Ruff, route, `legacy_app.py`, `pyarrow` runtime, or broad
dependency lock change is included.

## Implementation Commits

- `f8640b5ad` - settle residual runtime dependency ownership.
- `c5037d32c` - add PR 2059 fixed mapping.
- `e3cd5c159` - address runtime ownership review findings.
- `3f3a7f658` - map PR 2059 review findings.
- `d9f3160ab` - normalize PR 2059 mapping blocks.
- `1244aa6ea` - record PR 2059 security closure.

## Lane Start Provenance

Base branch: `main`

Branch: `codex/deps-runtime-ownership-stability`

Packet: `artifacts/orchestration/task_packets/fed188909ba0.json`

Starter: `scripts/orchestration/start_pr_lane.sh`

Pre-implementation role order executed explicitly before edits:
`agent-coordinator -> cursor-specialist-agent -> security-auditor -> architecture-specialist`.

Security-auditor post-implementation finding:
directory-scoped dependency-sensitive paths initially warned instead of
failing. Fixed before commit in `f8640b5ad`; evidence:
`tests/test_orchestration_preflight.py` covers `scripts/ci` and
`.github/workflows` directory scopes.

## Premortem Evidence

Artifact: `docs/review/PR_RESIDUAL_RUNTIME_DEP_OWNERSHIP_PREMORTEM.md`

Decision: proceed with a narrow PR after preserving `pyarrow` quarantine,
rejecting unsafe `numpy` lock churn, and scoping `aiosqlite` to SQLite async
fallback/local-dev/test ownership.

## Experiment Runner Evidence

Packet: `artifacts/orchestration/experiments/exp-c1dea589d48f.json`

Artifact: `artifacts/orchestration/experiments/results/exp-c1dea589d48f.json`

Status: accepted; 3/3 oracle-only governance commands executed after the
security-auditor blocker fix.

Contribution: `oracle_review`; commit `f8640b5ad` includes
`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

Note: local macOS runner used `network_budget=1` because network-disabled
sandbox mode requires Linux `unshare`; oracle commands were local validation
commands and the shared tree stayed untouched.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [x] `pulseplate-pr-review` completed.
- [ ] Current-head CI inspected before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

Codex Security scan:
`7602e0f6-f1f1-4eb1-8285-814fecb6af10`

Result: complete; 0 findings; coverage 2/2 reviewed rows. The workbench
classified the revision-range coverage as `branch_diff` at finalization while
the scan workspace remained mode `diff`.

PulsePlate PR review:

Result: complete dry-run report with one advisory large-diff planning note.

Disposition: NOT-A-BUG

Evidence: PR scope is deliberately bounded to dependency ownership and
preflight governance; `docs/review/PR_RESIDUAL_RUNTIME_DEP_OWNERSHIP_PREMORTEM.md`
records split rationale, `make validate-changed` and `pre-commit run
--all-files` already passed, and Codex Security scan
`7602e0f6-f1f1-4eb1-8285-814fecb6af10` completed with 0 findings.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2059#pullrequestreview-4614304285 -> e3cd5c15962131cb1e2e336a8b3402ebf72dede3
Disposition: FIXED
Commit: e3cd5c15962131cb1e2e336a8b3402ebf72dede3
Evidence: review-level Sourcery summary raised the same two actionable items as the individual comments below; both were fixed by the `PurePosixPath.parts`-based dependency-sensitive path matcher and partial `core/db.py` marker evidence test coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2059#discussion_r3510275346 -> e3cd5c15962131cb1e2e336a8b3402ebf72dede3
Disposition: FIXED
Commit: e3cd5c15962131cb1e2e336a8b3402ebf72dede3
Evidence: `scripts/orchestration/check_preflight.py` now compares dependency-sensitive paths with `PurePosixPath.parts`, keeps exact/descendant and broad parent-scope matching explicit, and centralizes the decision in `_touches_dependency_sensitive_path`; `tests/test_orchestration_preflight.py` covers broad `scripts` and `.github` parent scopes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2059#discussion_r3510275358 -> e3cd5c15962131cb1e2e336a8b3402ebf72dede3
Disposition: FIXED
Commit: e3cd5c15962131cb1e2e336a8b3402ebf72dede3
Evidence: `tests/test_python_dependency_surfaces.py` now covers partial `core/db.py` marker evidence and verifies `aiosqlite` stays at `warning:db_fallback_test_split_pending` unless the complete SQLite async fallback owner evidence is present.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2059#pullrequestreview-4614308389 -> e3cd5c15962131cb1e2e336a8b3402ebf72dede3
Disposition: FIXED
Commit: e3cd5c15962131cb1e2e336a8b3402ebf72dede3
Evidence: `tests/test_orchestration_preflight.py` now asserts malformed proxy URL diagnostics do not echo the full inline-credential URL, `user:token`, `token@`, or the bare `token` fragment.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze ...`
- PASS: `python3 scripts/orchestration/check_preflight.py --mode execute ...`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS: `pytest -q tests/test_python_dependency_surfaces.py tests/test_python_supply_chain_controls.py tests/test_orchestration_preflight.py tests/test_private_python_proxy_health.py`
- PASS: `pytest -q tests/test_core_db_enginecompat.py tests/test_core_db_async_optional.py`
- PASS: `pytest -q tests/test_orchestration_preflight.py tests/test_python_dependency_surfaces.py`
- PASS: `python3 scripts/ci/check_private_python_proxy_health.py --index-url https://packages.pulseplate.app/root/pulseplate/+simple/ --requirements-file requirements.txt --requirements-file requirements-ci-lite.txt --requirements-file requirements-test.txt --python-version 3.11 --python-version 3.12 --python-version 3.13`
- PASS: `git diff --check`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks during `git push`, including pip-audit, backend
  pre-push tests, full-repo Bandit, and docker build test.

## Merge Readiness

Not merge-ready yet. Current-head CI and strict merge-readiness checks are
pending.
