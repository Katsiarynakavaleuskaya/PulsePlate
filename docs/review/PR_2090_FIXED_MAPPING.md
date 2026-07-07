# PR #2090 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2090
Branch: `codex/move-legacy-weekly-plan-contracts-out-of-legacy-app`

## Summary

Move legacy weekly-plan request/response contracts and reusable weekly-menu
helpers out of `legacy_app.py` while preserving the hidden compatibility route
`POST /api/v1/premium/plan/week`.

## Scope

Move weekly-plan schema/service ownership to `app/*`, keep the router thin over
canonical seams, preserve `_get_api_key_dynamic` auth, and leave
`legacy_app.py` as compatibility delegation only. Preserve hidden/deprecated
route behavior, bootstrap/idempotency guards, safe errors, malformed-day
filtering, finite-number coercion, estimated-cost fallback, and avg-cost
behavior.

## Out Of Scope

Direct insight, `/api/v1/premium/plan/week-flexible`,
`/api/v1/pro/meal/weekly`, weekly-plan algorithm changes, frontend/iOS changes,
and deleting `legacy_app.py`.

## Implementation Commits

- `8bc3d9f827a1b0853a621beedbcb40796f99ffeb` - move ownership out of `legacy_app.py`.
- `f334214edf49d0aaae1ff58e585ecb58cebb8fa2` - preserve resolver monkeypatch seam.
- `043b68351ff001a7a99b152f615621bedac51c4f` - add PR mapping artifact.
- `d8e45dbdd36d938bbb8c9adfd1aec02bed794acd` - sync current `origin/main`.
- `454aeff6d3f5e935594ae5be28ba4d8b0187fa0f` - fix CodeRabbit stale-comment nitpick.
- `fdbe38435a6d418df32b7357cc065ebedc4f0eae` - cover moved schema/service branches.

## Lane Start Provenance

Starter: `bash scripts/orchestration/start_pr_lane.sh`
Packet: `artifacts/orchestration/task_packets/a61539e84620.json`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] `qa-engineer-agent` completed.
- [x] `bug-hunter` completed.
- [x] `security-auditor` completed.
- [x] Codex Security diff scan completed for material code range `76ffb6e4..f334214ed`.
- [x] Creative-code private-pilot state collected for real PR #2090 head `d06be5785`.
- [x] `pulseplate-pr-review` completed after compact mapping and main-sync push.
- [x] CodeRabbit stale-comment nitpick fixed and mapped.
- [x] Codecov patch-coverage feedback fixed and mapped.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after final review/check cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2090#issuecomment-4902964873 -> 454aeff6d3f5e935594ae5be28ba4d8b0187fa0f
Disposition: FIXED
Commit: 454aeff6d3f5e935594ae5be28ba4d8b0187fa0f
Evidence: CodeRabbit stale-comment nitpick fixed in `tests/test_premium_week_app_coverage.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2090#issuecomment-4903419521 -> fdbe38435a6d418df32b7357cc065ebedc4f0eae
Disposition: FIXED
Commit: fdbe38435a6d418df32b7357cc065ebedc4f0eae
Evidence: Added focused schema/resolver branch tests; local coverage probe reports 100% for `app/schemas/legacy_premium_weekly_plan.py` and `app/services/legacy_premium_weekly_plan.py`.

## Role Findings

### qa-engineer-agent

Disposition: FIXED

Commit: `f334214edf49d0aaae1ff58e585ecb58cebb8fa2`

Evidence: QA found the compatibility resolver no longer honored the historical
`legacy_app._get_app_package_module` patch seam. Commit `f334214ed` adds
explicit resolver hooks in `app/services/legacy_premium_weekly_plan.py`, passes
legacy shim hooks from `legacy_app.py`, and adds regression coverage in
`tests/test_premium_week_app_coverage.py`.

Disposition: NOT-A-BUG

Evidence: QA also flagged tests patching legacy global `VIP_MODULE_ENABLED`.
The request-time `is_vip_module_enabled()` check is intentional scope and
preserves external enabled/disabled env-state HTTP behavior.

### bug-hunter

Disposition: NOT-A-BUG

Evidence: The post-open bug-hunter pass reviewed `f334214ed` and reported no
actionable findings. It confirmed canonical schema/service imports, only
`_get_api_key_dynamic` remains from `legacy_app`, and focused/adjacent tests
passed.

### security-auditor

Disposition: NOT-A-BUG

Evidence: The post-open security-auditor pass reviewed `f334214ed` and
reported no actionable findings. It confirmed auth preservation,
hidden/deprecated metadata, fail-closed VIP disabled behavior, safe generic
errors, response normalization, and compatibility delegation.

### Codex Security

Disposition: NOT-A-BUG

Evidence: Codex Security scan `e1c03064-dbe9-4dc8-a65e-fdc7ddb119da` completed
for material code range `76ffb6e4..f334214ed`; coverage closed 4/4 worklist
rows and reportable findings were `0`.

Report:
`/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-Rx0Z5Y/move-legacy-weekly-plan-contracts-out-of-legacy-app/f334214edf49d0aaae1ff58e585ecb58cebb8fa2_20260707T111518Z_flwdh76r/report.md`

### pulseplate-pr-review

Disposition: NOT-A-BUG

Evidence: Final dry-run after main sync and compact mapping reviewed 10 files,
517 additions, and 271 deletions with no source warnings. It emitted one
advisory large-diff planning note because 788 changed lines exceed the 300-line
threshold. The slice remains coherent: one legacy weekly-plan ownership move,
one compatibility shim fix, and one mapping artifact. Targeted deterministic
gates passed (`282` focused/adjacent tests, `make validate-changed`,
`pre-commit run --all-files`, and pre-push hooks). No split is required.

## Creative-Code Private-Pilot Evidence

Local gitignored artifact, not committed:
`artifacts/orchestration/creative_code/private_pilot/2090/pilot_state.json`

- Artifact file SHA-256 at latest refresh before this mapping update:
  `6f6be875cda39ef6be4fd4deab2dab202b2da8bd1af3c90133180e1f98acfe17`.
- Source PR head at collection time: `d06be5785dab0904d2ccd6815d4d1b496b692f39`.
- Decision: `fix_current_pr`.
- Required checks at collection time: `0` failing, `0` pending, `0` missing.
- Current checks at collection time: `1` failing, `5` pending, `2` success.
- GitHub App capability: `manual_only`.

Interpretation: use the latest private-pilot artifact from the local worktree,
not a stale PR-body summary. It proves the private pilot evaluated real PR
#2090 metadata and chose `fix_current_pr`, but it is gitignored evidence only:
do not commit the artifact, and do not treat it as merge-readiness, PR
promotion, patch-generation, or GitHub App authority.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python -m mypy app/schemas/legacy_premium_weekly_plan.py app/routers/legacy_premium_weekly_plan.py app/services/legacy_premium_weekly_plan.py legacy_app.py` - PASS.
- `python -m pytest tests/test_premium_week_app_coverage.py` - PASS (`9` passed).
- Focused weekly-plan pytest - PASS (`91` passed, `3` existing Pydantic serializer warnings).
- Coverage probe for moved schema/service modules - PASS (`100%` for `app/schemas/legacy_premium_weekly_plan.py` and `app/services/legacy_premium_weekly_plan.py`).
- Adjacent OpenAPI/auth/policy pytest subset - PASS (`196` passed).
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS.
- Pre-push hook for `d06be5785` - PASS, including `pip-audit`, backend tests, full-repo Bandit, and docker build status as selected by hooks.
- `python3 scripts/orchestration/pr_review_context.py --pr 2090 --output /tmp/pulseplate_pr_2090_review_context_final.json` - PASS.
- `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_2090_review_context_final.json --format markdown` - PASS with advisory large-diff note dispositioned above.

## Local Verification Exception

Local `make verify` was not run. This follows the repository hard gate for this
checkout; full/heavy verification remains GitHub current-head CI.

## Merge Readiness

- [x] Local narrow bundle completed for pushed head `d06be5785`.
- [x] Post-open role order completed through `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan completed for material code diff.
- [x] `pulseplate-pr-review` completed after compact mapping and main-sync push.
- [ ] Current-head CI complete for latest PR head.
- [ ] CodeRabbit, Sourcery, and Cubic actionables checked and dispositioned.
- [ ] Strict merge-readiness wrapper passes with auth.
