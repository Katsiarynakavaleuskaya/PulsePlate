# PR #2061 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2061

Branch: `codex/move-business-registration-to-canonical-bootstrap`

## Summary

This PR moves business route registration ownership from `legacy_app.py` to the
canonical `app.main` bootstrap and changes `BUSINESS_MODULE_ENABLED` to an
explicit-truthy feature flag contract. The business routes stay absent by
default, `/api/v1/business/analyze` keeps `require_app_api_key`, `/status`
keeps its existing unauthenticated behavior when enabled, and final public
OpenAPI remains free of `/api/v1/business/*`.

## Scope

- Add reusable explicit-truthy env parsing in `app.utils.feature_flags`.
- Add `BUSINESS_ROUTE_SPECS` in `app/routers/business.py`.
- Register the business route family from `app/main.py` through
  `ensure_route_family_registered(...)` only when the business feature flag is
  explicitly truthy.
- Remove business router import/registration ownership from `legacy_app.py`.
- Tighten the legacy-growth guard allowlist and regression coverage for direct,
  aliased, module-qualified, dynamic, and walrus reintroduction patterns.
- Add focused business bootstrap tests and update backend routing docs.

## Out Of Scope

No Bayesian analyzer, nutrition, shopping, FoodDB, frontend, iOS, macOS, auth
redesign, generated OpenAPI/client artifact changes, middleware, lifespan, or
app-factory refactor is included.

## Implementation Commits

- `322584475a96f25dfee803979c471a92992206c4` - moves business route
  registration to canonical bootstrap, removes legacy ownership, adds the
  explicit feature-flag helper, tightens guards, updates docs, and adds focused
  route-family tests.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/d880f5d825dd.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Role order executed pre-open:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/exp-866cae82ee55.json`

- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Experiment ID: `exp-866cae82ee55`
- Source diff applied: `true`
- Oracle commands executed: `3`
- Contribution kind: `oracle_review`
- Co-author required: `true`
- Commit trailer present in `322584475a96f25dfee803979c471a92992206c4`.

Zero-network local attempt:
`artifacts/orchestration/experiments/results/exp-2b53d4ed97f6.json` recorded
`status=rejected`, `failure_class=infra_flake`, because the macOS local
network-disabled sandbox lacked Linux `unshare`. The accepted packet used
`network_budget=1`; oracle commands remained local deterministic checks.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `pytest -q tests/test_business_registration_bootstrap.py tests/test_business_router.py tests/test_business_router_coverage.py tests/test_legacy_growth_guard.py`
- PASS: `pytest -q tests/test_business_registration_bootstrap.py tests/test_business_router.py tests/test_business_router_coverage.py tests/test_legacy_growth_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `DEV_PYTHON=<repo .venv python> make openapi-check`
- PASS: `pytest -q tests/test_openapi_determinism.py::test_openapi_pipeline_uses_current_python_for_make tests/test_openapi_determinism.py::test_openapi_and_schema_ts_are_deterministic`
- PASS: `git diff --check`
- PASS: `DEV_PYTHON=<repo .venv python> VENV_PYTHON=<repo .venv python> make validate-changed`
- PASS: `pre-commit run --all-files`

Full local `make verify` was intentionally not run under the repository local
full-verify budget rule. Heavy/current-head CI remains the merge evidence
source.

## Discussion Thread Pass

- [x] Initial fixed-mapping artifact created after PR open.
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed after rerun.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [x] CodeRabbit, Sourcery, and Cubic actionables checked and dispositioned.
- [x] Review threads checked and dispositioned.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2061#discussion_r3511088671 -> 77001496e05fbabe53c371ffb6e92cb83e3858c7
Commit: 77001496e05fbabe53c371ffb6e92cb83e3858c7
Evidence: `tests/test_coverage_boost_final.py` uses `monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")`; targeted pytest, `make validate-changed`, and `pre-commit run --all-files` passed.

Disposition: NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2061#pullrequestreview-4615160415
Evidence: Sourcery's async-test suggestion conflicts with `tests/AGENTS.md` hook guidance for pre-commit-selected tests, and the bootstrap-helper suggestion would add production API outside this narrow route-ownership PR.
Reason: Current test shape intentionally covers the private canonical bootstrap seam changed by this PR without widening runtime API surface.

## Initial Mapping Evidence

Disposition: NOT-A-BUG

Finding: No actionable review threads existed at initial PR creation.

Evidence: PR #2061 was opened after focused local gates, pre-open role passes,
premortem, and accepted Experiment Runner oracle evidence. Post-open review
passes and bot thread disposition remain pending in this artifact until they
are actually complete.

## Premortem Finding Closure

Disposition: FIXED

Finding: Moving business registration could accidentally default-enable hidden
business routes.

Evidence: `app/main.py` registers the business route family only when
`is_business_module_enabled()` returns true, and
`tests/test_business_registration_bootstrap.py` covers unset, empty, false,
`0`, `no`, and `off` as absent.

Disposition: FIXED

Finding: Route dependency behavior could drift during ownership migration.

Evidence: `tests/test_business_registration_bootstrap.py` verifies
`/api/v1/business/analyze` contains the same `require_app_api_key` callable in
the route dependency graph and verifies `/status` remains callable without auth
when the module is enabled.

Disposition: FIXED

Finding: Source route visibility could leak business routes into public
OpenAPI.

Evidence: `BUSINESS_ROUTE_SPECS` preserves current source visibility, and
`tests/test_business_registration_bootstrap.py` verifies final `app.openapi()`
does not expose `/api/v1/business/*`. `make openapi-check` also produced zero
generated artifact diff.

Disposition: FIXED

Finding: Legacy guard allowlists could continue to permit business router
reintroduction.

Evidence: `scripts/ci/check_legacy_growth_guard.py` removes the business router
legacy facts, and `tests/test_legacy_growth_guard.py` covers direct, aliased,
module-qualified, dynamic, and walrus reintroduction patterns.

Disposition: NOT-A-BUG

Finding: `make validate-changed` can false-green before an implementation
commit because the branch-diff selector may not see staged-only changes.

Evidence: `make validate-changed` was rerun after implementation commit
`322584475a96f25dfee803979c471a92992206c4`; it selected and passed
`tests/security/test_api_authz_contract_static.py`,
`tests/test_business_registration_bootstrap.py`, `tests/test_business_router.py`,
`tests/test_business_router_coverage.py`, and `tests/test_legacy_growth_guard.py`.

## Post-open Role Review Evidence

Disposition: FIXED

Role: `qa-engineer-agent`

Finding: `tests/test_coverage_boost_final.py` still patched the removed
`app.routers.business.BUSINESS_MODULE_ENABLED` module attribute, encoding the
old business feature-flag contract.

Commit: `77001496e`

Evidence: `tests/test_coverage_boost_final.py` now uses
`monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")`. Targeted validation
passed with `pytest -q tests/test_coverage_boost_final.py -k
business_router_edge_paths`, and post-commit `make validate-changed` selected
and passed `tests/test_coverage_boost_final.py`.

Required post-open pass order remains:
`qa-engineer-agent -> bug-hunter -> security-auditor`, followed by Codex
Security diff scan / finding discovery and `pulseplate-pr-review`.

Review thread:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2061#discussion_r3511088671

Disposition: FIXED

Finding: Codex review identified the same stale
`app.routers.business.BUSINESS_MODULE_ENABLED` patch target in
`tests/test_coverage_boost_final.py`.

Commit: `77001496e05fbabe53c371ffb6e92cb83e3858c7`

Evidence: `tests/test_coverage_boost_final.py` now enables the feature through
`monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")`, matching the new
canonical feature-flag helper. Targeted validation passed with
`pytest -q tests/test_coverage_boost_final.py -k business_router_edge_paths`,
and the post-fix branch validation passed with `make validate-changed` and
`pre-commit run --all-files`.

Disposition: NOT-A-BUG

Role: `bug-hunter`

Finding: No actionable runtime regression findings after the QA fix.

Evidence: The bug-hunter pass verified canonical business registration in
`app/main.py`, the `require_app_api_key` route-family dependency for
`POST /api/v1/business/analyze`, request-time disabled behavior in
`app/routers/business.py`, and final OpenAPI filtering for
`/api/v1/business/*`. It reran focused pytest, direct route-table checks for
enabled and unset env states, `scripts/ci/check_legacy_growth_guard.py`, and
generated OpenAPI/client zero-diff checks.

Disposition: NOT-A-BUG

Role: `security-auditor`

Finding: No actionable security findings after the QA fix.

Evidence: The security-auditor pass verified that
`/api/v1/business/analyze` still carries `require_app_api_key`, business route
registration is explicit-truthy and default-disabled, public OpenAPI filtering
excludes `/api/v1/business/*`, and the legacy-growth guard rejects business
router reintroduction. It reran the focused business bootstrap tests, default
disabled/enabled route probes, `scripts/ci/check_legacy_growth_guard.py`, and
`git diff --check origin/main...HEAD`.

## Codex Security Evidence

Disposition: NOT-A-BUG

Finding: Codex Security diff scan found no reportable security findings.

Evidence:

- Scan ID: `0775a86e-aac6-471a-aebb-da641ee6982d`
- Mode: diff scan for `e253631c20ff2a8a052685b697e9e2acacd5dcf9..77001496e05fbabe53c371ffb6e92cb83e3858c7`
- Reportable findings: `0`
- Reviewed source-like rows: `4/4`
- Report:
  `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-e01Jen/move-business-registration-to-canonical-bootstrap/77001496e05fbabe53c371ffb6e92cb83e3858c7_20260702T073012Z_nothpny3/report.md`

## pulseplate-pr-review Disposition

Disposition: NOT-A-BUG

Finding: The advisory dry-run report flagged a `note` for large diff risk
because the diff has 719 changed lines, above the 300-line review-risk
threshold.

Evidence: This PR is the approved narrow business-route canonical-bootstrap
slice. The larger line count is primarily deterministic bootstrap, route-family,
legacy-growth, and authz test coverage plus the required fixed-mapping artifact.
Focused tests, `make validate-changed`, pre-commit, post-open role passes, and
Codex Security diff scan completed; the dry-run report recorded no correctness,
security, architecture, or QA findings beyond the review-planning size note.

Artifacts:

- Context: `artifacts/orchestration/pr_review/pr_2061_context_after_push.json`
- Markdown report: `artifacts/orchestration/pr_review/pr_2061_review_after_push.md`
- JSON report: `artifacts/orchestration/pr_review/pr_2061_review_after_push.json`

## Sourcery Review Disposition

Review:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2061#pullrequestreview-4615160415

Disposition: NOT-A-BUG

Finding: Sourcery suggested keeping
`test_analyze_business_code_oversized_payload_internal` as a native async
pytest test and suggested exposing a higher-level public registration API
instead of testing `app.main` private bootstrap helpers directly.

Evidence: The sync `asyncio.run(...)` test shape follows `tests/AGENTS.md`,
which forbids adding async pytest markers to pre-commit-selected tests unless
the hook environment is proven to load `pytest-asyncio`. The direct
`app.main` helper assertions are intentional in this migration PR: the changed
contract is canonical bootstrap ownership and fail-closed route-family
registration, so tests assert the narrow private seam instead of adding a new
production API only for test ergonomics. Focused validation and
`pre-commit run --all-files` passed with this shape.

## External Bot Status Disposition

Disposition: NOT-A-BUG

Finding: CodeRabbit provided a summary-only comment, Cubic reported a completed
neutral/success advisory status, and Sourcery's high-level review was
dispositioned above.

Evidence: `gh api repos/Katsiarynakavaleuskaya/PulsePlate/pulls/2061/comments`
returned one actionable inline review comment, the Codex P1 thread fixed in
`77001496e05fbabe53c371ffb6e92cb83e3858c7`. The Sourcery review URL is mapped
as `NOT-A-BUG` above. No additional CodeRabbit or Cubic inline actionables were
present in the GitHub pull request comments fetched during the current-head
merge-readiness failure triage.

## Merge Readiness

Not ready yet.

- Local focused gates: PASS.
- Fixed mapping artifact: created.
- Current-head GitHub CI: pending.
- Post-open role/security review: pending.
- Review thread / bot actionable disposition: pending.
- Strict merge-readiness wrapper: pending.

No merge-readiness, ready, green, or mergeable claim is made by this artifact.
