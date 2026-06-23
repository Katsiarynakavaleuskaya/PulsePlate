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

## Additional Fixed Findings

Codex Security finding discovery `e6d69443-1961-434b-8bec-f948e7680e93`: paid-tier canonical bootstrap did not fail closed on pre-existing protected route collisions; live duplicate VIP shoplist daily/weekly routes also created runtime/OpenAPI split-brain.
Disposition: FIXED
Commit: da9c3b355ac6e4a93928022bfd14b8cd7d4a56de
Evidence: `app/routers/vip.py:62-123` now has no legacy `core.shoplist` shadow owner and only includes canonical `vip_shoplist_router`; `app/routers/vip_shoplist.py:405-460` owns daily/weekly shoplist routes with stable operation IDs and typed DTO contracts; `app/bootstrap/route_family.py:88-126`, `app/routers/vip_registration.py:122-135`, and `app/routers/pro_registration.py:43-154` fail closed on duplicate source routes, foreign existing handlers, missing dependencies, and missing/empty route owners; `tests/test_pro_vip_route_dependency_guard.py:47-62` asserts no duplicate canonical PRO/VIP method/path entries; `tests/test_main_paywall_bootstrap.py:86-107` and `tests/test_main_paywall_bootstrap.py:957-994` cover duplicate source and foreign paid-tier route collisions.

Operator PR-surface rule clarification: duplicate routes and surfaced PR errors must be fixed in the current PR; production invariants must not be softened for placeholders.
Disposition: FIXED
Commit: da9c3b355ac6e4a93928022bfd14b8cd7d4a56de
Evidence: `AGENTS.md:57-73`, `app/AGENTS.md:278-289`, and `docs/ENGINEERING_LESSONS.md:688-713` now require fixing current-PR defects, forbidding duplicate method/path routes, and rejecting `None`/empty placeholder routers instead of weakening production behavior.

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
- `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" make openapi-check`
  - PASS. A raw `make openapi-check` attempt without the repo venv failed
    before app code with `ModuleNotFoundError: No module named 'dotenv'`.
- `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
  - PASS
- `make validate-changed` - PASS after commit; selected
  `tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py`
- `pre-commit run --all-files` - PASS after Black formatted
  `tests/test_pro_registration_router_coverage.py` and the hook was rerun.
- `git diff --check` - PASS
- Post-review-fix validation:
  `python -m py_compile app/main.py tests/test_main_paywall_bootstrap.py` -
  PASS;
  `pytest -q tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_pro_vip_route_dependency_guard.py`
  - PASS; `make validate-changed` - PASS; `pre-commit run --all-files` -
  PASS.
- Pre-push hooks - PASS: changed-file mypy, pip-audit, backend tests, full
  Bandit, docker build test.

Full local `make verify` was intentionally not run per operator machine-budget
constraint for this narrow lane. This PR is not merge-ready until focused local
gates, latest-head CI parity after commit `da9c3b355ac6e4a93928022bfd14b8cd7d4a56de`,
post-open role review refresh if required, final Codex Security diff scan /
finding discovery on latest head, CodeRabbit/Sourcery/Cubic disposition,
review-thread mapping, and strict merge-readiness checks all support it.

## Post-Open Requirements

- [ ] Current-head CI parity reviewed.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass refreshed after latest push if required.
- [ ] Codex Security diff scan / finding discovery finalized on latest head.
- [ ] `pulseplate-pr-review`.
- [x] CodeRabbit/Sourcery comments dispositioned for current post-open bot
  findings.
- [ ] Cubic comments checked and dispositioned.
- [ ] Strict merge-readiness wrapper run with current-head evidence.
