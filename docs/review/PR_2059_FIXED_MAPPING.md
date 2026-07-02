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

- [ ] Discussion-thread pass completed.
- [ ] Fixed in commit mapping completed.
- [ ] Post-open `qa-engineer-agent` pass completed.
- [ ] Post-open `bug-hunter` pass completed.
- [ ] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI inspected before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No review-thread actions yet.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze ...`
- PASS: `python3 scripts/orchestration/check_preflight.py --mode execute ...`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS: `pytest -q tests/test_python_dependency_surfaces.py tests/test_python_supply_chain_controls.py tests/test_orchestration_preflight.py tests/test_private_python_proxy_health.py`
- PASS: `pytest -q tests/test_core_db_enginecompat.py tests/test_core_db_async_optional.py`
- PASS: `python3 scripts/ci/check_private_python_proxy_health.py --index-url https://packages.pulseplate.app/root/pulseplate/+simple/ --requirements-file requirements.txt --requirements-file requirements-ci-lite.txt --requirements-file requirements-test.txt --python-version 3.11 --python-version 3.12 --python-version 3.13`
- PASS: `git diff --check`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks during `git push`, including pip-audit, backend
  pre-push tests, full-repo Bandit, and docker build test.

## Merge Readiness

Not merge-ready yet. Current-head CI, post-open review chain, bot comments,
discussion-thread disposition, and strict merge-readiness checks are pending.
