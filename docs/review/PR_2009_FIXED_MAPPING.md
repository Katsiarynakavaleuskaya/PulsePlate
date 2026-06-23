# PR #2009 - Fixed in Commit Mapping SoT

## Scope

Move PRO and VIP route registration ownership from `legacy_app.py` to canonical
`app/main.py` bootstrap. The later duplicate-route finding was fixed in this
PR as current PR-surface debt: generated OpenAPI/client artifacts changed only
to remove the stale VIP shoplist shadow contract and expose the real canonical
`app/routers/vip_shoplist.py` DTO contract. No auth, DB, iOS, billing,
entitlement, AI, or FoodDB behavior changed.

## Implementation Commit

- `afa840d50e00ae5b457b50c00321c8fcee7eeb2e` - move paid-tier registration
  ownership into canonical bootstrap and preserve legacy compatibility attrs.
- `1e17831a1bf156484d6e4773b2df94f7654aed6c` - address post-open
  CodeRabbit/Sourcery review findings with exact routing-map evidence and
  fail-closed compatibility mirroring.
- `da9c3b355ac6e4a93928022bfd14b8cd7d4a56de` - remove duplicate VIP shoplist
  daily/weekly route owners, add strict PRO/VIP route-family collision guards,
  update generated OpenAPI/client artifacts to the canonical shoplist DTO
  contract, and document the no-softening/no-duplicate agent rule.
- `9deaeef263bc9015086a9cf3f20f82e670556d5e` - fix changed-file mypy
  typing for route-family dependency contract construction discovered by
  pre-push hooks.
- `343bc4749d0a90f62175dab146bd82b1b50d359d` - retry reportless transient
  Safety CLI failures without weakening fail-closed vulnerability handling.
- `b910fcf7d8de84a4d56b35b5961d2f09821ea5f3` - cover paid-tier bootstrap
  guard branches that current-head CI `diff-coverage` identified as missing.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Status: Completed for PR open and refreshed after post-open bot review.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2009#discussion_r3457758614 -> 1e17831a1bf156484d6e4773b2df94f7654aed6c
Disposition: FIXED
Commit: 1e17831a1bf156484d6e4773b2df94f7654aed6c
Evidence: `docs/architecture/backend_routing_map.md:124` now names `app/main.py:829-832` for canonical VIP-before-PRO ownership, and `docs/architecture/backend_routing_map.md:126` names `app/routers/vip_registration.py:61-137` for the VIP implementation and `api_key_header` dependency.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2009#pullrequestreview-4550869584 -> 1e17831a1bf156484d6e4773b2df94f7654aed6c
Disposition: FIXED
Commit: 1e17831a1bf156484d6e4773b2df94f7654aed6c
Evidence: `app/main.py:794-805` now catches only the missing VIP module case and re-raises unrelated import failures; `app/main.py:808-832` resolves all compatibility values before mutating `app.main` or `legacy_app`; `tests/test_main_paywall_bootstrap.py:847-896` covers the no-partial-mutation failure path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2009#pullrequestreview-4550882968
Disposition: NOT-A-BUG
Evidence: The CodeRabbit review object was the post-push review wrapper/rate-limit walkthrough for commits through `635086017a3e1f9efe77ad871b3d5d7a8444aa29`; its earlier actionable inline architecture-map finding is separately mapped to `1e17831a1bf156484d6e4773b2df94f7654aed6c` above, and `gh pr checks 2009 --watch=false` reported `CodeRabbit` as `pass` for the same head.
Reason: No additional code-actionable finding remained in that review object after the mapped CodeRabbit inline item was fixed.

## Additional Fixed Findings

Codex Security finding discovery `e6d69443-1961-434b-8bec-f948e7680e93`: paid-tier canonical bootstrap did not fail closed on pre-existing protected route collisions; live duplicate VIP shoplist daily/weekly routes also created runtime/OpenAPI split-brain.
Disposition: FIXED
Commit: da9c3b355ac6e4a93928022bfd14b8cd7d4a56de
Follow-up Commit: 9deaeef263bc9015086a9cf3f20f82e670556d5e
Evidence: `app/routers/vip.py:62-123` now has no legacy `core.shoplist` shadow owner and only includes canonical `vip_shoplist_router`; `app/routers/vip_shoplist.py:405-460` owns daily/weekly shoplist routes with stable operation IDs and typed DTO contracts; `app/bootstrap/route_family.py:88-126`, `app/routers/vip_registration.py:122-135`, and `app/routers/pro_registration.py:43-154` fail closed on duplicate source routes, foreign existing handlers, missing dependencies, and missing/empty route owners; `tests/test_pro_vip_route_dependency_guard.py:47-62` asserts no duplicate canonical PRO/VIP method/path entries; `tests/test_main_paywall_bootstrap.py:86-107` and `tests/test_main_paywall_bootstrap.py:957-994` cover duplicate source and foreign paid-tier route collisions. `9deaeef263bc9015086a9cf3f20f82e670556d5e` keeps that route-family dependency contract mypy-clean.

Operator PR-surface rule clarification: duplicate routes and surfaced PR errors must be fixed in the current PR; production invariants must not be softened for placeholders.
Disposition: FIXED
Commit: da9c3b355ac6e4a93928022bfd14b8cd7d4a56de
Evidence: `AGENTS.md:57-73`, `app/AGENTS.md:278-289`, and `docs/ENGINEERING_LESSONS.md:688-713` now require fixing current-PR defects, forbidding duplicate method/path routes, and rejecting `None`/empty placeholder routers instead of weakening production behavior.

Current-head CI `security` job failed because Safety crashed before producing `safety-requirements-evals.json` for `requirements-evals.txt` with `Unhandled exception happened: '"detail"'`.
Disposition: FIXED
Commit: 343bc4749d0a90f62175dab146bd82b1b50d359d
Evidence: `scripts/ci/run_safety_audit.py:43-45` recognizes reportless Safety CLI transient crash markers; `scripts/ci/run_safety_audit.py:683-690` retries only non-zero reportless transient crashes; `scripts/ci/run_safety_audit.py:765-778` keeps fail-closed behavior after retry exhaustion; `tests/test_run_safety_audit.py:351-384` covers a reportless `Unhandled exception happened: '"detail"'` crash followed by a successful scan. `pytest -q tests/test_run_safety_audit.py -q` passed.

Current-head CI `diff-coverage` failed on guard branches in the paid-tier
bootstrap refactor.
Disposition: FIXED
Commit: b910fcf7d8de84a4d56b35b5961d2f09821ea5f3
Evidence: `tests/test_main_paywall_bootstrap.py:102-139` covers
non-HTTP/static family, framework-only method, and empty source-router
fail-closed branches; `tests/test_main_paywall_bootstrap.py:878-934` covers the
VIP compat disabled/missing/nested-import branches; and
`tests/test_main_paywall_bootstrap.py:1072-1086` covers the empty canonical PRO
router guard. Local repro passed:
`diff-cover /tmp/pr2009-coverage.xml --compare-branch origin/main --fail-under 97 ...`
reported `app/bootstrap/route_family.py (100%)`, `app/main.py (100%)`,
`app/routers/pro_registration.py (100%)`, `app/routers/vip_registration.py (100%)`,
`Coverage: 100%`.

`pulseplate-pr-review` dry-run reported a `large-diff-risk` advisory note because the PR diff exceeds 800 changed lines.
Disposition: NOT-A-BUG
Evidence: PR body contains `## Split Justification` plus explicit `operator approval`, `frontend/backend mix approval`, and `privileged scope exception` lines; PR labels include `scope/operator-approved`, `scope/frontend-backend-mix-approved`, and `scope/privileged-approved`; `python3 scripts/ci/check_pr_size_governance.py --base-sha 58fe0a81199e5ab0b08ecd643adc1b139a2072b7 --head-sha HEAD --event-path /tmp/pr2009-event.json` passed with `PR scope governance: OK (privileged CI/security/workflow policy)`; `make validate-changed` and `pre-commit run --all-files` passed after the scope expansion.
Reason: The diff is intentionally larger because the operator required removing all duplicate routes, adding production-code agent rules, updating generated OpenAPI/client mirrors, and fixing the current-head Safety CI blocker in this PR instead of deferring surfaced defects.

## Governance Evidence

- Worktree isolation: branch
  `codex/move-paid-tier-registration-to-canonical-bootstrap` in
  `worktrees/move-paid-tier-registration-to-canonical-bootstrap`.
- Preflight:
  `python3 scripts/orchestration/check_preflight.py --mode analyze --path app/main.py --path legacy_app.py --path scripts/ci/check_legacy_growth_guard.py`
  passed.
- Agent consistency:
  `python3 scripts/orchestration/check_agent_consistency.py` passed.
- Role dispatch packet:
  `artifacts/orchestration/task_packets/e2fbda40b04e.json` (local artifact).
- Role pass order completed: `agent-coordinator`, `architecture-specialist`,
  `backend-engineer`, `security-auditor`, `qa-engineer-agent`.
- Premortem against actual diff: risks were double registration, compatibility
  attr drift, OpenAPI/client drift, and empty-selector validation false
  confidence; all are covered by code removal, focused tests, OpenAPI diff
  check, and post-commit `make validate-changed`.
- Codex Security finding discovery identified duplicate/foreign paid-tier route
  collision risk. Commit `da9c3b355ac6e4a93928022bfd14b8cd7d4a56de` fixed the
  finding by removing the VIP shoplist duplicate owner and adding strict
  route-family guards.
- `pulseplate-pr-review` dry-run completed after head
  `a798f358ecb01e6300cd262545c212b351fc90f5`; its only finding was the
  advisory large-diff-risk note dispositioned above.
- Final latest-head Codex Security diff scan / finding discovery completed
  after head `712aef4cdb047e5606edd649d665085762af58ba`; scan
  `69281795-1706-42d7-9bf3-962b6481511b` reviewed 9 paid-tier, generated
  contract, and Safety CI surfaces with 0 reportable findings.
- Experiment Runner oracle-only evidence:
  `artifacts/orchestration/experiments/results/paid-tier-registration-ownership-oracle-result.json`
  (local artifact), experiment `exp-756e43207b6d`, status `accepted`,
  `mutated_paths=[]`, shared tree untouched.
- Experiment Runner attribution: implementation commit includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because the
  accepted oracle-only evidence shaped the commit decision.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze --path app/main.py --path legacy_app.py --path scripts/ci/check_legacy_growth_guard.py`
  - PASS
- `python3 scripts/orchestration/check_preflight.py --mode analyze --path app/main.py --path legacy_app.py --path app/bootstrap/route_family.py --path app/routers/vip.py --path app/routers/vip_shoplist.py --path app/routers/vip_registration.py --path app/routers/pro_registration.py --path scripts/ci/check_legacy_growth_guard.py --path tests/test_main_paywall_bootstrap.py --path tests/test_pro_vip_route_dependency_guard.py --path tests/test_pro_registration_router_coverage.py --path AGENTS.md --path app/AGENTS.md --path docs/ENGINEERING_LESSONS.md`
  - PASS after duplicate-route scope expansion.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/ci/check_legacy_growth_guard.py` - PASS
- `pytest -q tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_pro_registration_router_coverage.py tests/vip/test_vip_diff_coverage.py`
  - PASS
- `pytest -q tests/test_pro_vip_route_dependency_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py`
  - PASS
- `pytest -q tests/test_env_guards.py tests/test_app_public_surface.py tests/test_openapi_determinism.py tests/test_pro_premium_contract_parity.py tests/edges/test_premium_week_edges.py`
  - PASS
- `pytest -q tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_pro_registration_router_coverage.py tests/vip/test_vip_diff_coverage.py tests/test_pro_vip_route_dependency_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py tests/test_env_guards.py tests/test_app_public_surface.py tests/test_openapi_determinism.py tests/test_pro_premium_contract_parity.py tests/edges/test_premium_week_edges.py tests/test_vip_guard_consistency.py tests/test_vip_shoplist_daily.py tests/test_vip_shoplist_weekly.py tests/test_vip_shoplist_generate_api.py tests/test_vip_shoplist_invalid_enum_422.py tests/test_vip_shoplist_router_hardening.py tests/test_vip_api.py tests/test_vip_guard_order_403_vs_422.py`
  - PASS after duplicate-route scope expansion.
- No-duplicate full route probe:
  `python - <<'PY' ... ensure_canonical_app_bootstrap(app) ... assert no duplicate method/path routes`
  - PASS, `total route keys 127`.
- `PATH=".venv/bin:$PATH" make openapi-check`
  - PASS. A raw `make openapi-check` attempt without the repo venv failed
    before app code with `ModuleNotFoundError: No module named 'dotenv'`.
- `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
  - PASS
- `make validate-changed` - PASS after commit; selected
  `tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py`
- `pre-commit run --all-files` - PASS after Black formatted
  `tests/test_pro_registration_router_coverage.py` and the hook was rerun.
- Changed-file mypy pre-push check initially failed on
  `app/bootstrap/route_family.py:101`; commit
  `9deaeef263bc9015086a9cf3f20f82e670556d5e` fixed the type root cause, and
  `mypy app/bootstrap/route_family.py app/routers/pro_registration.py app/routers/vip_registration.py app/routers/vip.py app/routers/vip_shoplist.py --no-incremental --cache-dir=/dev/null`
  passed.
- `git diff --check` - PASS
- `pytest -q tests/test_run_safety_audit.py -q` - PASS after Safety retry
  remediation.
- `pytest -q tests/test_main_paywall_bootstrap.py` - PASS after the
  `diff-coverage` remediation; warning is from upstream
  `.venv/.../fastapi/testclient.py:1` importing Starlette `TestClient` with
  `# noqa`, not from this PR diff.
- Targeted coverage repro:
  `coverage run -m pytest -q tests/test_main_paywall_bootstrap.py tests/test_pro_vip_route_dependency_guard.py tests/test_openapi_determinism.py tests/test_pro_registration_router_coverage.py tests/test_vip_guard_consistency.py tests/vip/test_vip_diff_coverage.py`;
  `coverage xml -o /tmp/pr2009-coverage.xml`; `diff-cover ... --fail-under 97`
  - PASS, `Coverage: 100%`.
- `python3 scripts/ci/check_pr_size_governance.py --base-sha 58fe0a81199e5ab0b08ecd643adc1b139a2072b7 --head-sha HEAD --event-path /tmp/pr2009-event.json`
  - PASS with live PR body/labels:
  `PR scope governance: OK (privileged CI/security/workflow policy)`.
- Post-review-fix validation:
  `python -m py_compile app/main.py tests/test_main_paywall_bootstrap.py` -
  PASS;
  `pytest -q tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_pro_vip_route_dependency_guard.py`
  - PASS; `make validate-changed` - PASS; `pre-commit run --all-files` -
  PASS.
- `make validate-changed` - PASS after commit
  `b910fcf7d8de84a4d56b35b5961d2f09821ea5f3`; selected
  `tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_pro_registration_router_coverage.py tests/test_pro_vip_route_dependency_guard.py tests/test_run_safety_audit.py tests/test_vip_guard_consistency.py`.
- `pre-commit run --all-files` - PASS after commit
  `b910fcf7d8de84a4d56b35b5961d2f09821ea5f3`.
- Pre-push hooks - PASS: changed-file mypy where applicable, pip-audit,
  backend tests, full Bandit, docker build test.

Full local `make verify` was intentionally not run per operator machine-budget
constraint for this narrow lane. This PR is not merge-ready until focused local
gates, latest-head CI parity after commit
`b910fcf7d8de84a4d56b35b5961d2f09821ea5f3`, post-open role review refresh if
required, final Codex Security diff scan / finding discovery on latest head,
CodeRabbit/Sourcery/Cubic disposition, review-thread mapping, and strict
merge-readiness checks all support it.

## Post-Open Requirements

- [ ] Current-head CI parity reviewed.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass refreshed after latest push if required.
- [x] Codex Security diff scan / finding discovery finalized on latest head.
- [x] `pulseplate-pr-review`.
- [x] CodeRabbit/Sourcery comments dispositioned for current post-open bot
  findings.
- [ ] Cubic comments checked and dispositioned.
- [ ] Strict merge-readiness wrapper run with current-head evidence.
