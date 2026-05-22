# PR #1795 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/2f798e5a9505.json`
- Branch: `fix/deps-fastapi-starlette-security-compat`
- Worktree: `worktrees/deps-fastapi-starlette-security-compat`
- Operator exception: opened before PR #1792 merge to stabilize already-red `main` and preserve #1792 as A8 closeout-only.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/deps_fastapi_starlette_security_compat_oracle.json`
- Status: `accepted`
- Contribution: `oracle_review` (`coauthor_required: true`)
- Commit trailer used: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on implementation commit `d24efe54c`
- Post-review status: `accepted`
- Post-review contribution: `oracle_review` (`coauthor_required: true`)
- Post-review commit trailer used: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on hardening commit `e4feeb11e`

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1795#discussion_r3291373376 -> e4feeb11e
Disposition: FIXED
Commit: e4feeb11e
Evidence: `app/bootstrap/food_search.py:109-118` wraps preserved lifespan execution in `try/finally` so `_dispose_meili_http_client(app)` always runs; `tests/test_food_search_foundation.py::test_food_search_shutdown_hook_disposes_when_existing_lifespan_raises` covers the shutdown-exception leak path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1795#discussion_r3291373391 -> e4feeb11e
Disposition: FIXED
Commit: e4feeb11e
Evidence: `tests/fixtures/dependency_security_schema.json:2-8` includes `starlette: 1.0.1`; `requirements-dev.in` / `requirements-dev.txt` include the same security floor so `tests/test_dependency_security_guard.py` enforces the advisory across repo-managed surfaces.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1795#pullrequestreview-4349013801 -> d24efe54c
Disposition: FIXED
Commit: d24efe54c
Evidence: Aggregate CodeRabbit review covered the initial dependency/runtime compatibility implementation; implementation commit `d24efe54c` aligns constraints, patches `app/bootstrap/food_search.py`, and adds focused lifespan tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1795#pullrequestreview-4349129363 -> e4feeb11e
Disposition: FIXED
Commit: e4feeb11e
Evidence: Aggregate CodeRabbit review covered `discussion_r3291373376` and `discussion_r3291373391`; both are mapped above to `e4feeb11e` with direct code/test/schema evidence.

## Local Validation

- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/check_preflight.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/check_agent_consistency.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pip check` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pip install --dry-run -r requirements.txt` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pip install --dry-run -r requirements-ci-lite.txt` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pip install --dry-run -r requirements-docker-runtime.txt` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_food_search_foundation.py tests/test_repo_policy_guards.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_food_search_foundation.py tests/test_app_main_import.py tests/test_api.py tests/test_app_endpoints_combined.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null app/bootstrap/food_search.py tests/test_food_search_foundation.py` -> passed
- `make validate-changed` -> passed
- `pre-commit run --all-files` -> passed

## Merge Readiness

- [ ] Current-head CI is green.
- [ ] Required checks complete with no pending jobs.
- [ ] All review threads resolved on GitHub after disposition updates.
- [ ] No actionable CodeRabbit/Sourcery/Cubic/Codex comments remain.
- [ ] `check_pr_body_phase2_gates.py` passes.
- [ ] `check_review_threads_disposition.py --require-auth` passes.
- [ ] Strict merge-readiness wrapper with auth passes.
- [ ] Final wait-window completed.
