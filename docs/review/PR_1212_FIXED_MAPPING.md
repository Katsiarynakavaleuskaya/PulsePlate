# PR 1212 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

- Status: ready for review / not ready to merge.
- Current packet commits:
  - `d85e7f1d` — `docs(roadmap): sync Batch B close-out after PR #1207`
  - `bf3c05a2` — `fix(payments): persist bounded manual activation expiry`
  - `4efff5c9` — `fix(authz): preserve legacy manual compat in entitlement routing`
  - `26a697b6` — `test(payments): cover activation envelopes and compat guards`
  - `e6708d9f` — `docs(api): sync backend billing truth contract`
  - `69b18ee1` — `fix(payments): narrow ios activation status typing`
  - `04e2cdaf` — `fix(payments): satisfy push-hook billing typing`
  - `3870d514` — `fix(payments): restore canonical manual reconcile path`
- Current scope discipline:
  - activation persistence semantics, backend entitlement routing truth, deterministic Apple upstream envelopes, generated OpenAPI/types sync, roadmap/index sync, and billing regression tests only
  - no App Store offers / ASC protected envs
  - no screenshot or assets rollout
  - no semantic App Store validators
  - no new iOS/client billing redesign
  - no Batch C/D/E scope
- Required before merge:
  - record every actionable review disposition in this artifact
  - resolve review threads only after disposition evidence exists
  - confirm current-head required checks are green with no pending required jobs
  - confirm no actionable bot comments remain
  - re-run `pre-commit run --all-files`
  - re-run `make verify`
- PR-local validation executed on this lane:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `pre-commit run --all-files`
  - `make verify`
  - `pytest -q tests/test_subscription_activation_api.py`
  - `pre-commit run --hook-stage push mypy --files app/services/payments_activation.py`
