# PR 2039 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2039
- Title: `test(vip): align regions route lookup with effective routes`
- Branch: `codex/fix-main-vip-effective-route-test`
- Base: `main`

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/eda0af18b627.json`
- Goal: Fix post-merge main CI VIP regions route test by using effective route helpers.
- Role dispatch: `agent-coordinator -> qa-engineer-agent -> bug-hunter`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Sourcery review comment disposition recorded.
- [x] Local focused tests, `make validate-changed`, and `pre-commit run --all-files` passed.
- [x] Pre-push hooks passed, including `pip-audit`, backend tests, and full-repo Bandit.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/pr2039-vip-effective-route-oracle-packet.json`
- Artifact: `artifacts/orchestration/experiments/results/pr2039-vip-effective-route-oracle-result.json`
- Runner mode: `oracle_only_governance_reviewer`
- Result: accepted; shared tree untouched; 2/2 oracle pytest commands returned 0.
- Contribution kind: `oracle_review`
- Commit trailer required: yes, because the accepted oracle result shaped the commit decision.
- Commit trailer used on commit `2ad8ed133bf2275e66d2fb9e40de6823b45cbfda`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `app/effective_routes.py:15`, `app/effective_routes.py:67`, `app/effective_routes.py:73`, `app/effective_routes.py:77`, `tests/test_vip_coverage_boost_fixed.py:109`, `tests/test_vip_coverage_boost_fixed.py:115`, `AGENTS.md:65`
Reason: `route_endpoint_for_path_method(...)` is the canonical effective-route lookup helper; it intentionally receives the app route table and expands included-router contexts internally via `iter_effective_route_candidates(...)`. Missing routes still return `None` and preserve the test assertion message; duplicate routes intentionally fail closed because duplicate FastAPI method/path registrations are forbidden by repo policy.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2039#pullrequestreview-4587776067

## Validation Evidence

- Main CI run `28326897612`, `test-main (3.12, 90)`, `tests/test_vip_coverage_boost_fixed.py::TestVIPCoverageBoostFixed::test_vip_regions_missing_function` raw `app.routes` lookup failure is fixed by commit `2ad8ed133bf2275e66d2fb9e40de6823b45cbfda`.
- Main CI run `28326897612`, `test-main (3.11, 60)`, the same VIP regions route lookup failure is fixed by commit `2ad8ed133bf2275e66d2fb9e40de6823b45cbfda`.
- `python3 scripts/orchestration/check_preflight.py --path tests/test_vip_coverage_boost_fixed.py`: PASS.
- `python3 scripts/orchestration/check_agent_consistency.py`: PASS.
- `python3 scripts/orchestration/task_bootstrap.py --goal "Fix post-merge main CI VIP regions route test by using effective route helpers" --task-class ci_fix --path tests/test_vip_coverage_boost_fixed.py --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase pre_open`: packet `eda0af18b627`.
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/eda0af18b627.json --pretty`: dispatch order confirmed.
- Role passes: `agent-coordinator`, `qa-engineer-agent`, `bug-hunter`: no blocking findings.
- Premortem: `artifacts/orchestration/premortem/pr2039-vip-effective-route-hotfix-premortem.md`; findings fixed or process-dispositioned.
- `./.venv/bin/python -m pytest tests/test_vip_coverage_boost_fixed.py::TestVIPCoverageBoostFixed::test_vip_regions_missing_function -q`: 1 passed.
- `./.venv/bin/python -m pytest tests/test_vip_coverage_boost_fixed.py -q`: 8 passed.
- `./.venv/bin/python -m ruff check tests/test_vip_coverage_boost_fixed.py`: PASS.
- `git diff --check`: PASS.
- `make validate-changed`: selected `tests/test_vip_coverage_boost_fixed.py`; 8 passed.
- `pre-commit run --all-files`: PASS.
- Pre-push hooks: `pip-audit`, backend tests, and full-repo Bandit PASS.

## Merge Readiness

- [ ] Current-head CI is passing for PR #2039.
- [ ] Review threads and bot actionables are dispositioned.
- [ ] `check_merge_ready.py --require-auth` passes for PR #2039.

## Machine-Heavy Exception

Full local `make verify` was not run for this narrow main-CI hotfix per the operator-approved machine-heavy exception. Local evidence is the focused regression suite, `make validate-changed`, `pre-commit run --all-files`, pre-push hooks, and current-head GitHub CI parity before merge.

## Security Notes

No production code, auth, secrets, dependency, workflow, or runtime security behavior changed. No new Codex Security scan was launched for this test-only route-helper migration to avoid redundant scan loops.

## Deferred / Follow-ups

- The raw-route lookup guard gap is real. Do not add a broad guard in this red-main hotfix; first run a false-positive scan over existing route-introspection tests and then add a narrow guard that targets endpoint discovery loops over raw `app.routes`.
- Starlette/httpx2 deprecation warning remains outside this main-CI hotfix.
- Private Python index/proxy work remains in the dedicated infrastructure lane.
