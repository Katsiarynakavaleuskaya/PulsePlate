# PR #2090 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2090

Branch: `codex/move-legacy-weekly-plan-contracts-out-of-legacy-app`

## Summary

This PR moves legacy weekly-plan request/response contracts and reusable
weekly-menu helper behavior out of `legacy_app.py` and into canonical `app/*`
modules while preserving the hidden compatibility route
`POST /api/v1/premium/plan/week`.

## Scope

- Add canonical weekly-plan compatibility schemas in
  `app/schemas/legacy_premium_weekly_plan.py`.
- Add canonical weekly-menu response normalization and builder resolution in
  `app/services/legacy_premium_weekly_plan.py`.
- Keep `app/routers/legacy_premium_weekly_plan.py` as the route owner, using
  canonical schema/service seams and keeping `_get_api_key_dynamic` as the
  shared legacy credential dependency.
- Reduce `legacy_app.py` weekly-plan symbols to compatibility
  re-exports/delegation.
- Preserve hidden OpenAPI status, deprecated route metadata, duplicate/foreign
  handler rejection, idempotent bootstrap, auth dependency, safe error details,
  malformed-day filtering, finite-number normalization, estimated-cost fallback,
  and average-cost behavior.

## Out Of Scope

Direct insight, `/api/v1/premium/plan/week-flexible`,
`/api/v1/pro/meal/weekly`, weekly-plan algorithm changes, frontend/iOS changes,
and deleting `legacy_app.py` are out of scope.

## Implementation Commits

- `8bc3d9f827a1b0853a621beedbcb40796f99ffeb` - move weekly-plan contracts and
  helper ownership out of `legacy_app.py`.
- `f334214edf49d0aaae1ff58e585ecb58cebb8fa2` - preserve the historical
  `legacy_app._get_app_package_module` monkeypatch seam through the
  compatibility resolver shim.

## Discussion Thread Pass

- [x] Discussion-thread pass started for PR #2090.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan completed for material code diff
  `76ffb6e4e8eab21070b93b076fc5552caa5aed25..f334214edf49d0aaae1ff58e585ecb58cebb8fa2`.
- [x] Creative-code private-pilot state collected for real PR #2090 head
  `f334214edf49d0aaae1ff58e585ecb58cebb8fa2`.
- [ ] `pulseplate-pr-review` completed after this artifact is pushed.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after final review/check cycle.

## Fixed in Commit Mapping

- No GitHub review-thread mapping entries are recorded yet. At artifact
  creation time, role-agent findings were handled below, and merge-readiness is
  not claimed.

## Post-Open Role Findings

### qa-engineer-agent

Disposition: FIXED

Commit: `f334214edf49d0aaae1ff58e585ecb58cebb8fa2`

Evidence: QA found that the compatibility wrapper in `legacy_app.py` delegated
directly to the canonical resolver and no longer honored tests or callers that
patch the historical `legacy_app._get_app_package_module` seam. The fix adds
explicit resolver hooks in
`app/services/legacy_premium_weekly_plan.py:135`, passes legacy shim hooks from
`legacy_app.py:2075`, and adds regression coverage in
`tests/test_premium_week_app_coverage.py`.

Disposition: NOT-A-BUG

Evidence: QA also flagged that tests patching legacy module global
`VIP_MODULE_ENABLED` no longer drive the route. This is intentional for this PR:
`app/routers/legacy_premium_weekly_plan.py:43` checks
`is_vip_module_enabled()` at request time, matching the PR plan and preserving
external HTTP behavior for enabled/disabled env states. Coverage remains in
`tests/test_legacy_weekly_plan_alias_api.py`.

### bug-hunter

Disposition: NOT-A-BUG

Evidence: The post-open bug-hunter pass reviewed local head
`f334214edf49d0aaae1ff58e585ecb58cebb8fa2` against `origin/main` and reported
no actionable findings. The pass confirmed the router no longer imports weekly
DTO/helper behavior from `legacy_app`, the remaining legacy import is only
`_get_api_key_dynamic`, and focused/adjacent tests passed.

### security-auditor

Disposition: NOT-A-BUG

Evidence: The post-open security-auditor pass reviewed local head
`f334214edf49d0aaae1ff58e585ecb58cebb8fa2` against `origin/main` and reported
no actionable findings. The pass confirmed auth dependency preservation,
hidden/deprecated route metadata, fail-closed VIP disabled response, canonical
schema/service ownership, safe generic error details, response normalization,
and compatibility shim delegation.

### Codex Security

Disposition: NOT-A-BUG

Evidence: Codex Security diff scan
`e1c03064-dbe9-4dc8-a65e-fdc7ddb119da` completed for material code range
`76ffb6e4e8eab21070b93b076fc5552caa5aed25..f334214edf49d0aaae1ff58e585ecb58cebb8fa2`.
Coverage closed 4/4 worklist rows and reportable findings were `0`.

Report:
`/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-Rx0Z5Y/move-legacy-weekly-plan-contracts-out-of-legacy-app/f334214edf49d0aaae1ff58e585ecb58cebb8fa2_20260707T111518Z_flwdh76r/report.md`

## Creative-Code Private-Pilot Evidence

This PR includes a real-code pilot run against PR #2090 metadata, but does not
commit gitignored `artifacts/` outputs.

Artifact:
`artifacts/orchestration/creative_code/private_pilot/2090/pilot_state.json`

- Fingerprint:
  `sha256:1e221c48334db753bbaba128fe6ad68da51d505125f5499bca1db171e1ae5348`.
- Source PR head:
  `f334214edf49d0aaae1ff58e585ecb58cebb8fa2`.
- Decision at collection time: `hold_for_governance`.
- Current-head checks at collection time: `0` failing, `15` pending,
  `0` stale diagnostics.
- Fixed-mapping state at collection time: missing, because this artifact had
  not yet been committed.
- Checklist-only candidate plan command was intentionally blocked with:
  `ERROR: candidate plan requires prepare_next_candidate_plan decision.`

Interpretation: the pilot successfully exercised real PR metadata and correctly
refused to advance to candidate planning while governance and current-head CI
were incomplete. This is evidence for the employee-facing pipeline evaluation,
not merge-readiness evidence and not patch-generation authority.

Related creative-context experiment evidence:
`artifacts/orchestration/experiments/results/move-legacy-weekly-plan-contracts-out-of-legacy-app-oracle-result.json`

- Status: accepted.
- Mode: `oracle_only_governance_reviewer`.
- Oracle commands: 2/2 returned 0.
- Co-author requirement was satisfied in commit
  `8bc3d9f827a1b0853a621beedbcb40796f99ffeb`.

## Implementation Evidence

- `app/routers/legacy_premium_weekly_plan.py:12` imports the canonical
  weekly-plan schema/service symbols from `app.*`; `legacy_app` remains only for
  `_get_api_key_dynamic` at `app/routers/legacy_premium_weekly_plan.py:18`.
- `app/routers/legacy_premium_weekly_plan.py:27` keeps the route hidden,
  deprecated, and protected by `Depends(_get_api_key_dynamic)`.
- `app/routers/legacy_premium_weekly_plan.py:43` checks the VIP flag at request
  time and preserves the disabled `503` response.
- `app/routers/legacy_premium_weekly_plan.py:65` and
  `app/routers/legacy_premium_weekly_plan.py:67` preserve generic safe error
  details.
- `app/schemas/legacy_premium_weekly_plan.py:13` owns
  `LegacyWeekPlanRequest`; `app/schemas/legacy_premium_weekly_plan.py:50`
  validates request mode and structured `TargetsIn` payloads.
- `app/schemas/legacy_premium_weekly_plan.py:72` owns `WeeklyMenuResponse`.
- `app/services/legacy_premium_weekly_plan.py:50` owns weekly-menu response
  normalization, including malformed-day filtering and finite-number coercion.
- `app/services/legacy_premium_weekly_plan.py:135` owns weekly-menu builder
  resolution with explicit compatibility hooks.
- `legacy_app.py:2057` delegates `_build_legacy_weekly_menu_response`.
- `legacy_app.py:2075` delegates `_resolve_legacy_weekly_menu_builder` while
  preserving the historical monkeypatch seams.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m mypy app/schemas/legacy_premium_weekly_plan.py app/routers/legacy_premium_weekly_plan.py app/services/legacy_premium_weekly_plan.py legacy_app.py` - PASS.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_legacy_weekly_plan_alias_api.py tests/test_premium_week_app_coverage.py tests/test_legacy_app_diff_coverage.py tests/test_legacy_premium_weekly_plan_registration_bootstrap.py` - PASS (`86` passed, `3` existing Pydantic serializer warnings).
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_pro_premium_contract_parity.py::test_premium_endpoints_hidden_from_openapi tests/test_pro_premium_contract_parity.py::test_openapi_prunes_premium_week_components_after_path_filtering tests/test_targets_in_parity.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py tests/test_legacy_growth_guard.py tests/test_app_public_surface.py tests/test_repo_policy_guards.py` - PASS (`196` passed).
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS.
- Commit hook for `f334214edf49d0aaae1ff58e585ecb58cebb8fa2` - PASS.
- Pre-push hook for `f334214edf49d0aaae1ff58e585ecb58cebb8fa2` - PASS,
  including changed-file mypy, `pip-audit`, backend pre-push tests, full-repo
  Bandit, and docker build test.
- Codex Security diff scan
  `e1c03064-dbe9-4dc8-a65e-fdc7ddb119da` - PASS; reportable findings `0`.

## Local Verification Exception

Local `make verify` was not run. This follows the repository hard gate for
this checkout; full/heavy verification remains GitHub current-head CI. No
merge-readiness claim is made in this artifact.

## Merge Readiness

- [x] Local narrow bundle completed for material code head
  `f334214edf49d0aaae1ff58e585ecb58cebb8fa2`.
- [x] Post-open role order completed through
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan completed for material code diff.
- [ ] `pulseplate-pr-review` completed after this artifact is pushed.
- [ ] Current-head CI complete for the latest PR head.
- [ ] CodeRabbit, Sourcery, and Cubic actionables checked and dispositioned.
- [ ] Strict merge-readiness wrapper passes with auth.
