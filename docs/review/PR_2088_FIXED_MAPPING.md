# PR 2088 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2088

Branch: `codex/extract-legacy-premium-weekly-plan-route`

## Summary

This PR moves hidden legacy `POST /api/v1/premium/plan/week` route ownership
from `legacy_app.py` into `app/routers/legacy_premium_weekly_plan.py`, registers
it through `ensure_route_family_registered(...)`, and preserves legacy API-key
auth, VIP feature gating, canonical VIP delegation, hidden OpenAPI visibility,
and client-safe unexpected-error envelopes. `/api/v1/premium/plan/week-flexible`
and weekly planning algorithms are intentionally out of scope.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e19d8dcb842d4f736145dc9711c8a8eadb35dc24
Evidence: `app/routers/legacy_premium_weekly_plan.py:65`; `tests/test_premium_week_app_coverage.py:186`; `tests/test_legacy_growth_guard.py:2196`; `docs/review/PR_2088_FIXED_MAPPING.md:45`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2088#discussion_r3532002323 -> e19d8dcb842d4f736145dc9711c8a8eadb35dc24
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2088#pullrequestreview-4639693359 -> e19d8dcb842d4f736145dc9711c8a8eadb35dc24
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2088#discussion_r3533156936 -> e19d8dcb842d4f736145dc9711c8a8eadb35dc24

## Implementation Evidence

Disposition: FIXED
Commit: a66aaec157aade8f1b784524e0734dc26204dccd
Evidence: `app/routers/legacy_premium_weekly_plan.py:23`,
`app/main.py:87`, `app/main.py:477`, `app/main.py:1114`,
`app/main.py:1385`, `legacy_app.py:3547`,
`scripts/ci/check_legacy_growth_guard.py:94`,
`tests/test_legacy_premium_weekly_plan_registration_bootstrap.py:141`,
`tests/test_legacy_growth_guard.py:52`,
`tests/test_legacy_app_diff_coverage.py:20`,
`docs/contracts/PRODUCT_TIER_MAP.md:167`
Reason: The initial implementation commit extracts exactly one hidden legacy
weekly-plan route owner, preserves the legacy API-key dependency and VIP alias
behavior, removes the old `legacy_app.py` decorator owner, and tightens the
legacy growth guard so route regrowth fails.

Disposition: FIXED
Commit: 051fd9774696a196c77170792f37cfbc1b19161b
Evidence: `docs/review/PR_2088_FIXED_MAPPING.md`
Reason: Current-head CI found the canonical PR-specific fixed-mapping artifact
was missing. This follow-up artifact closes the PR Body Phase2 and merge
readiness governance blocker introduced at PR open.

Disposition: FIXED
Commit: e19d8dcb842d4f736145dc9711c8a8eadb35dc24
Evidence: `app/routers/legacy_premium_weekly_plan.py:65`,
`tests/test_premium_week_app_coverage.py:186`,
`tests/test_legacy_growth_guard.py:2196`,
`docs/review/PR_2088_FIXED_MAPPING.md:43`
Reason: CodeRabbit review comments are fixed by returning generic client-safe
unexpected-error details, keeping the original exception only through exception
chaining, deriving the growth-guard expected message from
`SENSITIVE_APP_SURFACE_LIMITS["api_key"]`, and expanding the prior mapping
commit proof to the full SHA.

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_2088_FIXED_MAPPING.md:9`,
`app/routers/legacy_premium_weekly_plan.py:30`,
`legacy_app.py:2097`, `legacy_app.py:2251`,
`tests/test_legacy_premium_weekly_plan_registration_bootstrap.py:232`
Reason: CodeRabbit's router-thinness nitpick is valid general guidance, but a
new service-layer migration is intentionally outside this route-ownership PR.
This seam keeps weekly request/response models and legacy helper ownership in
`legacy_app.py` while proving the route-family registration boundary first.

## Role-Agent Evidence

- Lane packet: `artifacts/orchestration/task_packets/5ec7d360e84a.json`
- Pre-open role order completed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> backend-engineer -> qa-engineer-agent -> bug-hunter`.
- Post-open QA role completed. Finding: missing
  `docs/review/PR_2088_FIXED_MAPPING.md`; route behavior had no blocking QA
  finding.
- Post-open bug-hunter role completed. Finding: no route-behavior blocker;
  mapping artifact governance gap was already tracked.
- Post-open security-auditor role completed. Finding: no code-level
  security/auth blocker; mapping artifact governance gap was already tracked.

## Codex Security Evidence

- Scan id: `463ea408-a816-4c9a-9949-1ceaffcc9f8e`
- Target: `0484805160536882a82d75b6f3b6e99e75535647..051fd9774696a196c77170792f37cfbc1b19161b`
- Mode: diff / branch-diff
- Reviewed diff-scoped rows:
  `app/main.py`, `app/routers/legacy_premium_weekly_plan.py`, `legacy_app.py`
- Result: complete, report generated, `findingCount=0`
- Coverage: every `deep_review_input.jsonl` row has a completed
  `no_issue_found` receipt in `work_ledger.jsonl`.

## PulsePlate PR Review Evidence

- Context command:
  `python3 scripts/orchestration/pr_review_context.py --pr 2088 --output /tmp/pulseplate_pr_2088_review_context.json`
- Markdown/json report commands:
  `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_2088_review_context.json --format markdown|json`
- Calibration tests:
  `python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q` - PASS.

Disposition: NOT-A-BUG
Evidence: `make validate-changed` PASS, Codex Security scan
`463ea408-a816-4c9a-9949-1ceaffcc9f8e` completed with `findingCount=0`, and
the PR diff is a single coherent legacy-route extraction plus tests/docs.
Reason: The dry-run report raised a note-level large-diff planning advisory
because the diff has 819 changed lines, barely above the 800-line review-risk
threshold. The added lines are dominated by focused regression tests and
premortem/mapping evidence for one route-family seam; splitting would separate
the guard/test evidence from the route-owner move it is meant to prove.

## Premortem Evidence

- Artifact: `docs/review/PR_LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_EXTRACTION_PREMORTEM.md`
- Result: proceed with changes; findings closed by code, tests, growth-guard
  updates, and validation evidence.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-70465b2c66a1.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-70465b2c66a1.json`
- Experiment id: `exp-70465b2c66a1`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution kind: `oracle_review`
- `coauthor_required=true`
- Commit carrying required trailer:
  `a66aaec157aade8f1b784524e0734dc26204dccd`
- Oracle commands passed:
  - `python3 scripts/ci/check_legacy_growth_guard.py`
  - `python3 -m pytest -q tests/test_legacy_premium_weekly_plan_registration_bootstrap.py tests/test_legacy_weekly_plan_alias_api.py tests/test_legacy_growth_guard.py tests/test_app_openapi_coverage.py`
  - `python3 -m pytest -q tests/test_premium_week_app_coverage.py tests/test_pro_premium_contract_parity.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py`

Infra caveat: zero-network local oracle packet `exp-004f81c9dd4b` was rejected
before commands because this macOS development host did not provide `unshare`
for the network-disabled sandbox. The accepted `network_budget=1` artifact kept
the same local oracle commands and does not grant product runtime, provider,
client, dependency installer, or public API authority.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `pytest -q tests/test_legacy_premium_weekly_plan_registration_bootstrap.py tests/test_legacy_weekly_plan_alias_api.py tests/test_legacy_growth_guard.py tests/test_app_openapi_coverage.py` - PASS.
- `pytest -q tests/test_premium_week_app_coverage.py tests/test_pro_premium_contract_parity.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py` - PASS.
- `python3 scripts/ci/check_legacy_growth_guard.py` - PASS.
- `DEV_PYTHON=<repo-venv-python> make openapi-check` - PASS.
- `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts` - PASS.
- `make validate-changed` with repo `VENV_PYTHON` and `DEV_PYTHON` - PASS after commit; selected changed-file backend tests.
- `pre-commit run --all-files` with repo `VENV_PYTHON` and `DEV_PYTHON` - PASS before commit and after commit.
- Push hook - PASS, including backend pre-push tests, full-repo Bandit, dependency audit, and Docker build test.
- Codex Security diff scan / finding discovery - PASS, 0 findings.
- `pulseplate-pr-review` dry-run report and calibration tests - PASS, note-level
  large-diff advisory dispositioned above as NOT-A-BUG.
- CodeRabbit review findings - fixed/dispositioned in
  `e19d8dcb842d4f736145dc9711c8a8eadb35dc24`; targeted regression tests passed.

## Merge Readiness

Not claimed here. Requires current-head GitHub CI after the latest pushed
commit, bot review dispositions, and strict merge-readiness with auth.
