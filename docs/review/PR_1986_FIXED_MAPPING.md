# PR #1986 Fixed Mapping

## Lane Start Provenance

- Branch: `codex/extract-legacy-export-aliases`
- Packet: `artifacts/orchestration/task_packets/522dd21f499b.json`
- Base: `origin/main` at `46d93e628444a5ef70e9283152297e98bb42a4e1`
- Operator override: branch start only while a colleague watches `main` CI;
  not merge-readiness evidence.
- Role order executed pre-open:
  `agent-coordinator -> backend-engineer -> architecture-specialist -> qa-engineer-agent -> bug-hunter -> security-auditor`

## Scope Boundary

- In scope: five legacy export/demo alias routes, canonical app-router shim
  registration, legacy-growth guard shrinkage, focused route/auth/rate-limit
  regression tests.
- Out of scope: full `legacy_app.py` removal, semantic cache, Redis/GPTCache,
  GraphRAG, FoodDB cutover, OpenAPI/client regeneration, billing/auth
  entitlement changes, frontend/iOS work, and broad premium nutrition/insight
  cleanup.

## Premortem Closure

- Skill: `pulseplate-premortem-risk-review`
- Decision: proceed with changes.
- Finding: route-level helper rebinding parity could regress if the shim captured
  legacy helper functions at construction time.
- Disposition: FIXED.
- Evidence: `app/routers/legacy_export_aliases.py` resolves injected helper
  resolvers at request time, and `tests/test_legacy_export_aliases.py` covers
  rebinding `legacy_app.export_pdf_generic` after app bootstrap.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-0b4ae0fb5914.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-0b4ae0fb5914.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted.
- Source diff applied: `true`.
- Source diff paths:
  `app/main.py`, `app/routers/legacy_export_aliases.py`, `legacy_app.py`,
  `scripts/ci/check_legacy_growth_guard.py`,
  `tests/test_legacy_export_aliases.py`,
  `tests/test_legacy_growth_guard.py`,
  `tests/test_main_paywall_bootstrap.py`,
  `tests/test_rate_limit_llm_and_exports_api.py`.
- Oracle commands: 3/3 returned 0.
- `shared_tree_untouched=true`.
- Contribution kind: `none`; no Experiment Runner co-author trailer required.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial PR open: no review threads existed at artifact creation.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass
  pending.
- [ ] Codex Security diff scan / finding discovery pending.
- [ ] `pulseplate-pr-review` pending.
- [ ] New CodeRabbit/Sourcery/Cubic comments must be fixed or dispositioned
  before merge readiness.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 34086db39
Evidence: `app/routers/legacy_export_aliases.py`, `app/main.py`, `legacy_app.py`, `scripts/ci/check_legacy_growth_guard.py`, and focused tests preserve auth, rate-limit metadata, feature gating, hidden OpenAPI visibility, response parity, and route-level helper rebinding.
Reason: Implements the PR scope before review threads existed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1986 -> 34086db39

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path legacy_app.py --path app/main.py --path app/routers/legacy_export_aliases.py --path scripts/ci/check_legacy_growth_guard.py --path tests/test_legacy_export_aliases.py --path tests/test_main_paywall_bootstrap.py --path tests/test_legacy_growth_guard.py --path tests/test_rate_limit_llm_and_exports_api.py`
- PASS:
  `.venv/bin/python -m pytest -q tests/test_legacy_export_aliases.py tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_rate_limit_llm_and_exports_api.py`
- PASS:
  `.venv/bin/python -m pytest -q tests/test_export_endpoints.py tests/test_export_endpoints_final_97.py tests/test_legacy_app_diff_coverage.py tests/test_openapi_namespace_guards.py tests/test_app_init_rebinding_spec.py tests/edges/test_app_edges.py tests/edges/test_app_branches.py tests/test_app_coverage_missing_lines.py`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `python3 scripts/ci/check_artifact_reader_contracts.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during commit/push hooks: changed-file mypy, pip-audit, backend
  pre-push tests, full-repo Bandit, and docker build test.
- PASS: Experiment Runner oracle-only evidence listed above.

## Security Notes

- All five aliases still use `_get_api_key_dynamic`.
- All five aliases keep `request: Request`, `RATE_LIMIT_EXPORTS`, and 429
  response metadata.
- Runtime aliases are hidden from public OpenAPI with `include_in_schema=False`.
- The legacy growth guard no longer allowlists the extracted export decorators,
  and regression coverage proves reintroduction is rejected.

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. This PR uses focused local gates,
`make validate-changed`, pre-commit/pre-push hooks, Experiment Runner oracle
evidence, and current-head CI/review governance before any readiness claim.

## Merge Readiness

Not ready at artifact creation. Required before merge:

- [x] Numbered fixed-mapping artifact created.
- [x] PR body mirror updated to point to this artifact.
- [ ] Post-open role-agent review sequence completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit/Sourcery/Cubic actionable comments fixed or dispositioned.
- [ ] Current-head CI parity on latest pushed commit.
- [ ] Strict merge-readiness check with `--require-auth`.
- [ ] No unresolved actionable review or bot comments.
- [ ] Mandatory wait-window after latest bot/review activity.
