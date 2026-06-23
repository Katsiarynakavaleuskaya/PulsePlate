# PR #2013 - Fixed in Commit Mapping SoT

## Scope

Fix post-merge `main` CI after PR #2009 by cleaning stale VIP coverage tests
that still expected deleted legacy shoplist/export symbols on
`app.routers.vip`. This PR does not restore production aliases and does not
change runtime routes, auth, OpenAPI, generated clients, DB, billing,
entitlements, frontend, or iOS surfaces.

## Implementation Commits

- `e26069f83dc1090ff6454e7081c5ff4eba8e6039` - sync
  `.secrets.baseline` line numbers after test-line cleanup.
- `8184b8b84a5867d327361c21f4a598a707f8f185` - remove stale VIP coverage
  tests and patches for deleted `app.routers.vip` shoplist/export aliases,
  replace duplicate fallback coverage with a negative alias-absence guard, and
  assert the real `/api/v1/vip/shoplist/formats` contract.
- `5b490696cc4ead4d408359b90d4471d7b47602ad` - address Sourcery review by
  using set intersection for the legacy-alias absence guard and centralizing
  the VIP shoplist formats response assertion in a shared test helper.
- `1c036e13a604ba26289c4999e2dc07b55037102d` - repair the canonical fixed
  mapping artifact shape so Phase2 parsers accept the PR closeout evidence.
- `7d91746984a76637ac9a425b0878223a4c2ae8f9` - address CodeRabbit JSON
  response parsing comments by asserting `Content-Type` before `response.json()`
  in changed VIP coverage tests.
- `6524080fd62e9531b91cd79383618f40d26742f2` - refresh the existing Faraday
  Trivy suppression metadata to match Trivy `v0.71.2` current output while
  preserving exact package/CVE scoping and existing backlog tracking.
- `603e8381af9b65f77e0474c5cbc84ff637dae537` - remove machine-local absolute
  paths from PR #2013 review evidence after post-open QA review.
- `5b70da19c9685f505b57ee1f39913a337ab5c3e0` - remove the stale Faraday
  `FixedVersion == "2.14.3"` assertion from the Trivy policy guard test while
  keeping the current Trivy `>= 2.14.3` assertion.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [ ] Initial PR open: no human review threads existed at artifact creation.
- [ ] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2013`.
- [ ] Initial Sourcery review comments fixed and mapped.
- [ ] CodeRabbit JSON response parsing comments fixed and mapped.
- [ ] Later post-open bot/human review comments are fixed or dispositioned
  before merge readiness.
- [ ] Current-head CI is complete before merge readiness.
- [ ] Strict merge-readiness check runs after the final review/check cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#pullrequestreview-4556631754 -> 5b490696cc4ead4d408359b90d4471d7b47602ad
Disposition: FIXED
Commit: 5b490696cc4ead4d408359b90d4471d7b47602ad
Evidence: `tests/test_vip_coverage_clean.py` now checks legacy VIP shoplist alias absence with `legacy_shoplist_aliases & set(dir(vip))`; `tests/_helpers/vip_contracts.py` centralizes the static VIP shoplist formats contract; `tests/test_vip_coverage_simple.py` and `tests/test_vip_coverage_additional.py` call the helper instead of duplicating the `formats` / `locales` literals. Focused validation passed: `pytest -q tests/test_vip_coverage_clean.py tests/test_vip_coverage_simple.py tests/test_vip_coverage_additional.py`; the full stale-VIP cleanup bundle passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#pullrequestreview-4556687766 -> 7d91746984a76637ac9a425b0878223a4c2ae8f9
Disposition: FIXED
Commit: 7d91746984a76637ac9a425b0878223a4c2ae8f9
Evidence: `tests/test_vip_coverage_additional.py` and `tests/test_vip_coverage_simple.py` now parse `/api/v1/vip/shoplist/formats` through helpers that assert an `application/json` response before calling `response.json()`. The same CodeRabbit review also included a documentation nitpick, fixed by `95cf19be260975677a786f07a395b03c5e9dd8be`. Focused validation passed: `pytest -q tests/test_vip_coverage_simple.py tests/test_vip_coverage_additional.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#discussion_r3462576094 -> 7d91746984a76637ac9a425b0878223a4c2ae8f9
Disposition: FIXED
Commit: 7d91746984a76637ac9a425b0878223a4c2ae8f9
Evidence: `tests/test_vip_coverage_additional.py` now parses responses through `assert_json_response_payload(...)` or `assert_vip_shoplist_formats_response(...)`; `tests/_helpers/vip_contracts.py` asserts `Content-Type` starts with `application/json` before calling `response.json()`. Focused validation passed: `pytest -q tests/test_vip_coverage_simple.py tests/test_vip_coverage_additional.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#discussion_r3462576102 -> 7d91746984a76637ac9a425b0878223a4c2ae8f9
Disposition: FIXED
Commit: 7d91746984a76637ac9a425b0878223a4c2ae8f9
Evidence: `tests/test_vip_coverage_simple.py` now parses responses through `assert_json_response_payload(...)` or `assert_vip_shoplist_formats_response(...)`; `tests/_helpers/vip_contracts.py` asserts `Content-Type` starts with `application/json` before calling `response.json()`. Focused validation passed: `pytest -q tests/test_vip_coverage_simple.py tests/test_vip_coverage_additional.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#pullrequestreview-4557050411 -> b97bed8f9aa8a3ec2171be99ba4d808953ae4eb5
Disposition: FIXED
Commit: b97bed8f9aa8a3ec2171be99ba4d808953ae4eb5
Evidence: `tests/test_trivy_ignore_policy_expiry.py` now scopes Faraday CVE-2026-54297 suppression assertions to `faraday_policy` instead of the full Rego policy text. Focused validation passed: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`; `pytest -q tests/test_trivy_ignore_policy_expiry.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#discussion_r3462888780 -> b97bed8f9aa8a3ec2171be99ba4d808953ae4eb5
Disposition: FIXED
Commit: b97bed8f9aa8a3ec2171be99ba4d808953ae4eb5
Evidence: `docs/review/PR_2013_FIXED_MAPPING.md` keeps only the two artifact-level checkboxes checked and leaves later review/merge-cycle checklist items unchecked until final merge readiness.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#pullrequestreview-4557195306 -> 5b70da19c9685f505b57ee1f39913a337ab5c3e0
Disposition: FIXED
Commit: 5b70da19c9685f505b57ee1f39913a337ab5c3e0
Evidence: `tests/test_trivy_ignore_policy_expiry.py` no longer asserts the stale Faraday `FixedVersion == "2.14.3"` literal in the current PR diff and keeps the active `FixedVersion == ">= 2.14.3"` expectation. Focused validation passed: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`; `pytest -q tests/test_trivy_ignore_policy_expiry.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#discussion_r3463019921 -> 5b70da19c9685f505b57ee1f39913a337ab5c3e0
Disposition: FIXED
Commit: 5b70da19c9685f505b57ee1f39913a337ab5c3e0
Evidence: `tests/test_trivy_ignore_policy_expiry.py` no longer asserts the stale Faraday `FixedVersion == "2.14.3"` literal in the current PR diff and keeps the active `FixedVersion == ">= 2.14.3"` expectation. Focused validation passed: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`; `pytest -q tests/test_trivy_ignore_policy_expiry.py`.

## Additional Fixed Findings

Post-merge `main` CI run
`https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28032859273`
failed in `test-main` shards because stale VIP coverage tests referenced
deleted `app.routers.vip.ShoplistGenerator` and `app.routers.vip.format_export`
symbols.

Disposition: FIXED

Commit: `8184b8b84a5867d327361c21f4a598a707f8f185`

Evidence:

- `tests/test_vip_coverage_clean.py` now asserts that
  `ShoplistGenerator`, `aggregate_ingredients`, `round_to_packages`, and
  `format_export` are absent from `app.routers.vip`.
- `tests/test_vip_coverage_fixed.py`,
  `tests/test_vip_coverage_comprehensive.py`, and
  `tests/test_vip_coverage_precise.py` no longer mutate `sys.modules` to
  re-import `app.routers.vip` and assert stale shoplist aliases.
- `tests/test_vip_coverage_simple.py` and
  `tests/test_vip_coverage_additional.py` now assert the live static
  `/api/v1/vip/shoplist/formats` contract.
- `tests/test_vip_coverage_boost.py`,
  `tests/test_vip_coverage_boost_fixed.py`, and
  `tests/test_vip_simple_working.py` no longer patch the removed
  `app.routers.vip.ShoplistGenerator` alias.
- `rg -n "app\\.routers\\.vip\\.(ShoplistGenerator|aggregate_ingredients|round_to_packages|format_export)|vip\\.(ShoplistGenerator|aggregate_ingredients|round_to_packages|format_export)" tests/test_vip_* tests/test_coverage_*`
  returned no matches after cleanup.

Current-head Docker `security-scan` run
`https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28054134124`
failed because Trivy `v0.71.2` now reports Faraday `CVE-2026-54297` with
`FixedVersion` `>= 2.14.3` and `DataSource.ID` `ruby-advisory-db`, while the
existing exact temporary suppression expected older metadata.

Disposition: FIXED

Commit: `6524080fd62e9531b91cd79383618f40d26742f2`

Evidence:

- `trivy/ignore-policy.rego` now matches the current Trivy metadata while
  preserving exact `CVE-2026-54297`, `faraday`, `1.10.5`, PURL, package ID,
  severity, status, and primary URL constraints.
- `docs/security/CVE-2026-54297-faraday-fastlane.md`,
  `docs/security/DEPENDABOT_ALERT_INVENTORY.md`, and
  `docs/roadmap/BACKLOG_LEDGER.md` now record the current fixed-version shape.
- `tests/test_trivy_ignore_policy_expiry.py` asserts the updated exact policy.
- PASS:
  `trivy fs . --db-repository ghcr.io/aquasecurity/trivy-db --skip-dirs trivy --ignorefile .trivyignore --ignore-policy trivy/ignore-policy.rego --scanners vuln --severity CRITICAL,HIGH --format table --exit-code 1`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_trivy_ignore_policy_expiry.py`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`

Post-open `qa-engineer-agent` review found machine-local absolute paths in
the PR body and `docs/review/PR_2013_FIXED_MAPPING.md`.

Disposition: FIXED

Commit: `603e8381af9b65f77e0474c5cbc84ff637dae537`

Evidence:

- `docs/review/PR_2013_FIXED_MAPPING.md` now uses the repo Python resolver form
  instead of machine-local paths for local validation evidence.
- A direct local-path leak scan of the touched mapping/security/test/policy files
  returned no matches after cleanup.

## Governance Evidence

- Worktree isolation: branch
  `codex/fix-main-vip-coverage-after-paid-tier-merge` in
  `worktrees/fix-main-vip-coverage-after-paid-tier-merge`.
- Lane start packet:
  `artifacts/orchestration/task_packets/fee0b9e24cfa.json` (local artifact).
- Role pass order completed before edits:
  `agent-coordinator -> qa-engineer-agent -> backend-engineer -> security-auditor -> bug-hunter`.
- Backend role pass confirmed route ownership:
  `app.routers.vip` owns only static `GET /api/v1/vip/shoplist/formats`;
  `app.routers.vip_shoplist` owns `/generate`, `/daily`, `/weekly`, and
  `/export`; duplicate VIP shoplist route keys were not present.
- Security role pass confirmed no auth/tier drift and no reason to restore
  deleted production aliases.
- Experiment Runner oracle-only evidence:
  `artifacts/orchestration/experiments/results/exp-9c2ff5026aa1.json`
  (local artifact), status `accepted`, runner mode
  `oracle_only_governance_reviewer`, shared tree untouched, failure class
  `null`, mutated paths `[]`.
- Experiment Runner attribution:
  commit `8184b8b84a5867d327361c21f4a598a707f8f185` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because
  the accepted oracle-only result shaped validation evidence.

## Local Validation Evidence

- PASS:
  `python3 scripts/orchestration/check_preflight.py --mode analyze --path ...`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_vip_coverage_clean.py tests/test_vip_coverage_fixed.py tests/test_vip_coverage_comprehensive.py tests/test_vip_coverage_precise.py tests/test_vip_coverage_simple.py tests/test_vip_coverage_boost_fixed.py tests/test_vip_simple_working.py tests/test_vip_coverage_additional.py tests/test_vip_coverage_boost.py tests/test_coverage_final_push.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_paywall_bootstrap.py tests/test_pro_vip_route_dependency_guard.py tests/test_vip_shoplist_daily.py tests/test_vip_shoplist_weekly.py tests/test_vip_shoplist_generate_api.py tests/test_vip_shoplist_invalid_enum_422.py tests/test_vip_shoplist_router_hardening.py tests/test_vip_guard_consistency.py tests/test_pro_registration_router_coverage.py tests/edges/test_vip_auth_edges.py tests/test_repo_policy_sys_modules.py tests/test_repo_policy_guards.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; PATH="$(dirname "$VENV_PYTHON"):$PATH" make openapi-check`
- PASS:
  `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; PATH="$(dirname "$VENV_PYTHON"):$PATH" make validate-changed`
  after commit; selected all changed VIP test files.
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; PATH="$(dirname "$VENV_PYTHON"):$PATH" pre-commit run --all-files`
- PASS: pre-push hooks during `git push`, including pip-audit, backend
  pre-push pytest, and full-repo Bandit.
- PASS: `git diff --check && git diff --check origin/main...HEAD`
- PASS: `python3 scripts/orchestration/check_experiment_runner_identity.py`

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. The operator explicitly requested narrow
validation for this hotfix because the full suite is machine-heavy without
shards. Merge readiness requires the focused local gates above, current-head CI
parity for the PR surface, post-open role review, bot/human comment
disposition, Codex Security diff scan / finding discovery when available,
`pulseplate-pr-review`, strict merge-readiness checks with auth, and the final
wait-window.
