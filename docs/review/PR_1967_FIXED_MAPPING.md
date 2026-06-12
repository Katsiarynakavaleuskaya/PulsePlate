# PR #1967 Fixed in Commit Mapping

## Goal

Extract `/privacy` and `/terms` ownership from `legacy_app.py` into the
canonical legal router/bootstrap while preserving runtime behavior and public
API contracts.

## Business Reason

This is the next narrow legacy cleanup slice after PR #1954: move the first
low-risk publication routes out of the compatibility seam and keep the seam
guard fail-closed so they cannot drift back into legacy ownership.

## Scope

- Add canonical `/privacy` ownership in `app.routers.legal`.
- Keep canonical `/terms` ownership in `app.routers.legal`.
- Register legal publication routes atomically from `app/main.py`.
- Remove legacy `/privacy` and `/terms` route handlers from `legacy_app.py`.
- Shrink the legacy growth guard so the removed legal route/import facts cannot
  return silently.
- Add deterministic route ownership, payload parity, OpenAPI non-exposure,
  bootstrap fail-closed, and legacy-growth guard tests.

## Out Of Scope

- No health/readiness extraction.
- No auth, billing, entitlement, tier, provider, LLM, quota, semantic-cache,
  FoodDB, WebSocket, export, admin, OpenAPI/client generation, or broad
  `legacy_app.py` retirement.
- No runtime behavior change for canonical `app.main:app`.

## Files Changed

- `app/main.py`
- `app/routers/legal.py`
- `legacy_app.py`
- `scripts/ci/check_legacy_growth_guard.py`
- `tests/test_app_endpoints_1383_1401.py`
- `tests/test_app_endpoints_combined.py`
- `tests/test_fitchef_structured_api.py`
- `tests/test_legacy_app_diff_coverage.py`
- `tests/test_legacy_growth_guard.py`
- `tests/test_main_paywall_bootstrap.py`
- `docs/review/PR_LEGAL_PUBLICATION_ROUTE_EXTRACTION_PREMORTEM.md`
- `docs/review/PR_1967_FIXED_MAPPING.md`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1967#issuecomment-4688944758 -> 8bbbdac5be1e46fe24552163e17ed7e9d039f2d3
Disposition: FIXED
Commit: 8bbbdac5be1e46fe24552163e17ed7e9d039f2d3
Evidence: Codecov initial patch-coverage comment was addressed by adding duplicate canonical legal-router coverage and exact `/privacy` payload parity coverage; focused pytest and focused mypy passed locally before this mapping.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1967#issuecomment-4688750870
Disposition: NOT-A-BUG
Evidence: CodeRabbit comment is a review-rate/usage-credit notice and contains no code-actionable finding.
Reason: External reviewer availability notice only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1967#issuecomment-4688755368
Disposition: NOT-A-BUG
Evidence: Codex connector comment is a code-review usage-limit notice and contains no code-actionable finding.
Reason: External reviewer availability notice only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1967#pullrequestreview-4483536910
Disposition: NOT-A-BUG
Evidence: Sourcery review is a weekly diff-character rate-limit notice and contains no code-actionable finding.
Reason: External reviewer availability notice only.

## Implementation Commit Evidence

- `1f9c5ed81baf8079421c0b493c1b2137c80870bb` extracts `/privacy` and
  `/terms` from `legacy_app.py`, adds canonical legal-router/bootstrap
  ownership, shrinks the legacy seam guard, and adds deterministic tests.
- `8bbbdac5be1e46fe24552163e17ed7e9d039f2d3` closes post-open
  coordinator/QA/Codecov findings by rejecting duplicate canonical legal-router
  paths, asserting exact `/privacy` payload parity, and fixing changed-file mypy
  typing in the touched test file.

## Premortem Finding Closure

- PM-LEGAL-001 OpenAPI leak: FIXED.
  Evidence: `tests/test_app_endpoints_combined.py` asserts `/privacy` and
  `/terms` are absent from public OpenAPI.
- PM-LEGAL-002 duplicate/foreign route handlers: FIXED.
  Evidence: `app/main.py` rejects malformed, partial, duplicate, and foreign
  legal route registration; `tests/test_main_paywall_bootstrap.py` covers these
  states.
- PM-LEGAL-003 stale legacy allowlist: FIXED.
  Evidence: `scripts/ci/check_legacy_growth_guard.py` removes `/privacy`,
  `/terms`, and the legacy legal helper import allowance; tests cover
  reintroduction failure.
- PM-LEGAL-004 raw `legacy_app:app` expectation: NOT-A-BUG.
  Evidence: canonical serving remains `app.main:app`; the accepted legacy seam
  document permits shrinking raw legacy publication-route ownership.

## Post-open Role Findings

| Role | Result | Evidence |
| --- | --- | --- |
| `agent-coordinator` | P2 duplicate canonical legal-router gap FIXED. | `8bbbdac5be1e46fe24552163e17ed7e9d039f2d3` counts legal router GET routes per expected path before inclusion and rejects duplicate canonical paths. |
| `qa-engineer-agent` | P2 `/privacy` exact payload parity gap FIXED. | `8bbbdac5be1e46fe24552163e17ed7e9d039f2d3` asserts `/privacy` JSON equals `jsonable_encoder(build_privacy_endpoint_payload())`. |
| `bug-hunter` | PASS after fixes; no remaining blocker. | Bug-hunter verified exactly one canonical legal route per path, hidden OpenAPI exposure, route owner `app.routers.legal`, and no stale legacy ownership. |
| `security-auditor` | PASS after fixes; no remaining blocker. | Security-auditor verified no auth, billing, provider, LLM/quota/cache, FoodDB/catalog, or middleware widening and confirmed route-hijack/OpenAPI/legacy-seam controls. |

## Codex Security Diff Scan

- Report: `/tmp/codex-security-scans/extract-legal-publication-routes-from-legacy/1f9c5ed81baf_20260612T081032Z/report.md`
- HTML report: `/tmp/codex-security-scans/extract-legal-publication-routes-from-legacy/1f9c5ed81baf_20260612T081032Z/report.html`
- Coverage: 4/4 `deep_review_input.csv` rows have completion receipts in
  `work_ledger.jsonl`.
- Result: no reportable findings; validation and attack-path phases were
  skipped because discovery emitted no candidates.

## PulsePlate PR Review

- Context: `/tmp/pulseplate_pr_1967_review_context.json`
- Markdown report: `/tmp/pulseplate_pr_1967_review_report.md`
- JSON report: `/tmp/pulseplate_pr_1967_review_report.json`
- Result before this mapping artifact: advisory governance findings only for
  missing fixed mapping and large-diff review planning.
- Disposition: mapping missing is FIXED by this artifact; large-diff advisory is
  NOT-A-BUG because the slice is the operator-approved PR-2 extraction scope and
  local focused gates plus `make validate-changed` are run for this lane.

## Tests / Validation

Passed locally for the current PR lane:

- `python3 scripts/orchestration/check_preflight.py`
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py`
- `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_app_endpoints_combined.py tests/test_main_paywall_bootstrap.py tests/test_fitchef_structured_api.py tests/test_app_endpoints_1383_1401.py tests/test_legacy_app_diff_coverage.py`
- `.venv/bin/python -m pytest -q tests/test_app_endpoints_combined.py tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_app_endpoints_1383_1401.py tests/test_legacy_app_diff_coverage.py`
- `.venv/bin/python scripts/ci/check_legacy_growth_guard.py`
- `.venv/bin/python scripts/ci/check_semantic_cache_gate.py`
- `.venv/bin/mypy --no-incremental --cache-dir=/dev/null app/main.py tests/test_main_paywall_bootstrap.py tests/test_app_endpoints_combined.py`
- `PYTHONPATH=. .venv/bin/python scripts/generate_openapi.py` with no tracked
  OpenAPI diff.
- `.venv/bin/python -m pytest tests/test_pr_review_report.py -q`
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed`
  before PR open.
- `PRE_COMMIT_HOME=/tmp/pre-commit-extract-legal-publication-routes pre-commit run --all-files`
  before PR open.
- Pre-push hook before PR open: changed-file mypy, pip-audit, backend tests,
  full Bandit, and docker build test.

Known local warning: focused legacy diff-coverage tests emit the existing
Pydantic serializer warning for `diet_flags` list versus set in
`tests/test_legacy_app_diff_coverage.py::test_week_plan_missing_required_fields_raises_422`.

## Security Notes

No secrets, auth, billing, entitlement, LLM/provider/quota, semantic-cache
serving, FoodDB/catalog, WebSocket, export, admin, or middleware behavior was
widened. Legal publication routes remain public runtime endpoints and hidden
from public OpenAPI, matching the intended compatibility contract.

## Risks / Rollback

Risk: deployments or local commands that directly serve raw `legacy_app:app`
will no longer see `/privacy` and `/terms`.

Mitigation: repo canonical serving path is `app.main:app`, and this PR adds
tests proving canonical route ownership and runtime payload parity.

Rollback: revert `1f9c5ed81baf8079421c0b493c1b2137c80870bb`,
`8bbbdac5be1e46fe24552163e17ed7e9d039f2d3`, and this mapping commit. No data
migration or OpenAPI/client regeneration is involved.

## Deferred / Follow-Ups

None for this PR. Broader legacy retirement, health/readiness extraction,
semantic-cache serving, FoodDB cutover, and other route-family migrations remain
out of scope for separate reviewed PRs.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/54b7e6ad7501.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/extract-legal-publication-routes-from-legacy`
- Worktree: `worktrees/extract-legal-publication-routes-from-legacy`
- Operator override: lane start was approved while current-head `main` CI was
  pending. This was a start override only, not a merge-readiness override.
- Pre-open declared role order:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> qa-engineer-agent -> security-auditor`
- Post-open packet: `artifacts/orchestration/task_packets/bfcca76d58b6.json`
- Post-open role order:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`,
  then Codex Security diff scan / finding discovery, then `pulseplate-pr-review`.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-3fa856f58217.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Contribution: `oracle_review`
- Oracles: focused pytest, legacy growth guard, and semantic-cache gate.
- The implementation commit includes:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Merge Readiness

Not claimed. Required before readiness claim:

- Mapping/body mirror pushed and current-head CI rerun healthy.
- Codecov refreshed on the current head after the post-open test commit.
- Review threads and bot actionables verified/dispositioned on current head.
- Strict merge-readiness wrapper passes with required GitHub auth.
- Mandatory wait-window elapses after latest bot/review activity.
