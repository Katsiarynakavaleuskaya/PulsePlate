# PR 2037 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2037

Branch: `codex/fix-main-plan-export-effective-routes`

## Summary

This PR fixes the post-merge `main` CI regression in
`tests/test_plan_export_additional.py::test_export_routes_are_registered_but_hidden_from_public_openapi`
by making the test inspect FastAPI effective route contexts instead of raw
direct `app.routes` `APIRoute` objects.

## Scope

- In scope: test-only route contract alignment for plan export route
  registration under FastAPI lazy included effective routes.
- Out of scope: runtime route registration changes, dependency updates,
  private Python index/proxy changes, Starlette/httpx2 migration, and new Codex
  Security scan loops.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/526ea0bcd975.json`
- Branch: `codex/fix-main-plan-export-effective-routes`
- Base: `origin/main` at merge commit `b87259bc85f0b98b64e8d87b288664438f0e2a4f`
- Worktree: isolated hotfix worktree
  `worktrees/fix-main-plan-export-effective-routes`
- Role order executed pre-open:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter`
- Packet creation was treated as provenance only, not role execution.

## Role Evidence

- Coordinator pass: PASS / no blockers. Scope stayed narrow to one test file
  and existing effective-route helpers.
- QA pass: PASS / no blockers. Acceptance coverage was adequate for the
  failing main CI test and adjacent route dependency assertions.
- Bug-hunter pass: PASS / no blockers. Dependency graph, duplicate route,
  OpenAPI visibility, and Starlette warning risks were reviewed.

## Experiment Runner Evidence

- Not applicable: test-only post-merge main CI hotfix; no Experiment Runner
  oracle artifact shaped implementation, tests, docs, mapping, or commit
  decisions.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] No review threads existed when this artifact was created.
- [x] CodeRabbit current comment is a rate-limit notice, not an actionable
  review finding.
- [x] Sourcery current comment is a reviewer guide, not an actionable finding.
- [x] Local focused tests, `make validate-changed`, and
  `pre-commit run --all-files` passed.
- [x] Pre-push hooks passed, including `pip-audit`, backend tests, and
  full-repo Bandit.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path tests/test_plan_export_additional.py`
  passed with explicit `GIT_DIR` / `GIT_WORK_TREE` for this local worktree.
- `python3 scripts/orchestration/task_bootstrap.py ...` emitted packet
  `artifacts/orchestration/task_packets/526ea0bcd975.json`.
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/526ea0bcd975.json --pretty`
  resolved the role sequence with no missing agents.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_plan_export_additional.py::test_export_routes_are_registered_but_hidden_from_public_openapi -q`
  passed.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_plan_export_additional.py -q`
  passed: 16 tests.
- Focused auth dependency graph tests passed: 3 tests.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/ruff check tests/test_plan_export_additional.py`
  passed.
- `make validate-changed` passed after commit and selected
  `tests/test_plan_export_additional.py`: 16 tests.
- `pre-commit run --all-files` passed.
- Pre-push hooks passed.

## Merge Readiness

- [ ] Current-head CI inspected and passing for the latest pushed head SHA.
- [ ] CodeRabbit no-actionable status confirmed.
- [ ] Sourcery no-actionable status confirmed.
- [ ] Cubic no-actionable status confirmed.
- [ ] Strict merge-readiness wrapper with auth passes.
- [ ] Mandatory wait-window satisfied.
