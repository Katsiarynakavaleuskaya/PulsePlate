# PR #2021 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2021

Branch: `codex/move-bodyfat-registration-to-canonical-bootstrap`

## Summary

This PR moves `POST /api/v1/bodyfat` route ownership from `legacy_app.py` to
canonical `app.main` bootstrap without changing formulas, schemas, response
shape, auth/tier policy, rate limiting, generated OpenAPI, or generated client
artifacts.

## Scope

- Add `BODYFAT_ROUTE_SPECS` and a module-level canonical bodyfat router in
  `app/routers/bodyfat.py`.
- Register the bodyfat static family from `app/main.py` through
  `RouteMemberContract` and `ensure_route_family_registered(...)`.
- Keep `app.routers.bodyfat.get_router()` as a fresh unprefixed `/bodyfat`
  compatibility adapter for old direct-inclusion callers.
- Remove bodyfat import/include ownership from `legacy_app.py`.
- Shrink the legacy growth guard allowlist and add bodyfat-specific negative
  tests for factory, direct, aliased, and module-qualified re-registration.
- Update backend routing documentation and backlog a P1 follow-up for future
  BMI-engine derivation delegation.

## Out Of Scope

No bodyfat math, BMI derivation semantics, schema, response-shape, auth/tier,
rate-limit, generated OpenAPI/client, DB, frontend runtime, iOS, or migration
changes.

## Implementation Commits

- `d8c2313fc157ca39109268e262af7644056e028b` - moves bodyfat route
  registration to canonical bootstrap, removes legacy ownership, adds guards
  and tests, and records premortem/backlog evidence.
- `44bc4440a` - rejects direct dynamic bodyfat imports assigned to allowlisted
  legacy router names.
- `90c185114` - closes security-auditor dynamic import bypasses for alias,
  destructuring, and walrus assignment shapes.
- `bf5436342` - preserves the security-auditor guard fix while satisfying the
  changed-file mypy pre-push hook.

## Lane Start Provenance

- Base branch: `main`
- Branch: `codex/move-bodyfat-registration-to-canonical-bootstrap`
- Packet: `artifacts/orchestration/task_packets/b1f4071b1aa9.json`
- Role order executed pre-open:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed mapping artifact created after GitHub assigned PR number `#2021`.
- [x] Post-open `qa-engineer-agent` pass completed: no actionable findings.
- [x] Post-open `bug-hunter` pass completed; actionable finding fixed and
  dispositioned below.
- [x] Post-open `security-auditor` pass completed; actionable finding fixed and
  dispositioned below.
- [x] Codex Security diff scan completed: 5/5 reviewed, 0 findings.
- [x] `pulseplate-pr-review` completed; advisory large-diff note dispositioned
  below.
- [ ] Post-open discussion-thread pass pending final current-head bot/CI refresh.
- [ ] CodeRabbit comments/actionables inspected on final current head.
- [ ] Sourcery comments/actionables inspected on final current head.
- [ ] Cubic comments/actionables inspected on final current head.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Mapping Notes

Initial PR open: no human review threads existed at artifact creation. Any
post-open actionable bot or human findings must be fixed, mapped in
`## Fixed in Commit Mapping` with disposition proof, mirrored in the PR body,
and only then resolved.

## Post-Open Role Findings

Role: `qa-engineer-agent`

Disposition: NOT-A-BUG

Evidence: Post-open QA pass found no actionable findings. Residual risk was
limited to intentionally deferred full local `make verify`, pending current-head
CI at review time, and external bot rate-limit/no-actionable states.

Role: `bug-hunter`

Disposition: FIXED

Finding: `scripts/ci/check_legacy_growth_guard.py` could miss bodyfat route
ownership reintroduced through a dynamic import assigned to an already
allowlisted router name, for example
`business_router = importlib.import_module("app.routers.bodyfat").router`.

Commit: `44bc4440a`

Evidence: `scripts/ci/check_legacy_growth_guard.py` now records dynamic
`app.routers.*` imports assigned to local names as `router_import:dynamic`
facts, while preserving the existing plan-export dynamic alias baseline.
`tests/test_legacy_growth_guard.py` adds `importlib.import_module(...)` and
`__import__(...)` bodyfat regressions hidden as `business_router`. Focused
validation passed:
`python3 scripts/ci/check_legacy_growth_guard.py`,
`VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_legacy_growth_guard.py`, and
`make validate-changed`.

Role: `security-auditor`

Disposition: FIXED

Finding: `scripts/ci/check_legacy_growth_guard.py` still missed dynamic bodyfat
route re-registration when `import_module` was aliased, when the imported router
was assigned through tuple/list destructuring, or when a walrus assignment wrote
the router into the already allowlisted `business_router` name.

Commit: `90c185114`

Evidence: `scripts/ci/check_legacy_growth_guard.py` now tracks aliases to
`importlib.import_module` and `__import__`, pairs dynamic `app.routers.*` imports
with concrete assignment targets, and records `ast.NamedExpr` targets.
`tests/test_legacy_growth_guard.py` covers aliased import-module calls,
simple aliases, destructuring, and walrus assignment hidden behind
`business_router`. Validation passed:
`python3 scripts/ci/check_legacy_growth_guard.py`,
`VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_legacy_growth_guard.py`,
focused bodyfat/bootstrap/API suite (`39 passed`), `make validate-changed`,
`VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; make openapi-check DEV_PYTHON="$VENV_PYTHON"`,
`pre-commit run --all-files`, and `git diff --check`.
Follow-up hook fix commit `bf5436342` only renames an internal accumulator in
the same helper to satisfy changed-file mypy; behavior remains covered by
`tests/test_legacy_growth_guard.py` (`68 passed`),
`python3 scripts/ci/check_legacy_growth_guard.py`, and
`pre-commit run --hook-stage pre-push mypy --files scripts/ci/check_legacy_growth_guard.py`.

Role: Codex Security diff scan

Disposition: NOT-A-BUG

Evidence: Codex Security scan `d9f75240-8a67-4c76-b8d6-e2062323022a`
completed for range
`8a637a9ad2ab618ec2e7e550132f5a615146d968..90c1851147c806761a776ee4821cc39b7b88a64c`.
Report:
`/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-i7T2Pe/bodyfat-canonical-bootstrap/90c1851147c806761a776ee4821cc39b7b88a64c_20260625T090928Z_01vnvpd2/report.md`.
Coverage: 5/5 reviewed surfaces, 0 reportable findings. Reviewed surfaces:
`app/__init__.py`, `app/main.py`, `app/routers/bodyfat.py`, `legacy_app.py`,
and `scripts/ci/check_legacy_growth_guard.py`.

Role: `pulseplate-pr-review`

Disposition: NOT-A-BUG

Finding: advisory `large-diff-risk` note because the PR diff exceeds the
review-risk threshold.

Evidence: The diff is intentionally cohesive despite size: one bodyfat
route-ownership migration, its bootstrap/legacy guard tests, review artifact,
premortem, routing docs, and one backlog follow-up. Local narrow gates selected
the changed backend tests and passed: focused bodyfat/bootstrap/API suite
(`39 passed`), `tests/test_legacy_growth_guard.py` (`68 passed`),
`python3 scripts/ci/check_legacy_growth_guard.py`, `make validate-changed`,
`make openapi-check` via repo venv, `pre-commit run --all-files`, and
`git diff --check`. Report artifacts:
`/tmp/pulseplate_pr_2021_review_report.md` and
`/tmp/pulseplate_pr_2021_review_report.json`.

## Premortem Findings

Artifact: `docs/review/BODYFAT_CANONICAL_BOOTSTRAP_PREMORTEM.md`

Disposition: FIXED

Finding: legacy bodyfat ownership could return through a different import shape.

Commit: `d8c2313fc157ca39109268e262af7644056e028b`

Evidence: `legacy_app.py` no longer imports/includes `app.routers.bodyfat`;
`scripts/ci/check_legacy_growth_guard.py` no longer allowlists the bodyfat
factory import/registration facts; `tests/test_legacy_growth_guard.py` rejects
factory, direct, aliased, and module-qualified bodyfat re-registration.

Disposition: FIXED

Finding: direct `get_router()` compatibility callers could get the wrong route
prefix after canonicalization.

Commit: `d8c2313fc157ca39109268e262af7644056e028b`

Evidence: `app/routers/bodyfat.py` keeps the canonical router at
`/api/v1/bodyfat` and keeps `get_router()` as an unprefixed `/bodyfat`
compatibility adapter; `tests/test_main_paywall_bootstrap.py` covers direct
adapter `/bodyfat` success and `/api/v1/bodyfat` absence.

Disposition: FIXED

Finding: moving ownership could leak `/api/v1/bodyfat` into published OpenAPI or
generated client artifacts.

Commit: `d8c2313fc157ca39109268e262af7644056e028b`

Evidence: `tests/test_main_paywall_bootstrap.py` covers source/final OpenAPI
visibility behavior, and
`VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" make openapi-check DEV_PYTHON="$VENV_PYTHON"`
passed with no generated artifact diff.

Disposition: FIXED

Finding: `make validate-changed` could false-green before commit because the
branch diff selector had no committed diff.

Commit: `d8c2313fc157ca39109268e262af7644056e028b`

Evidence: the pre-commit `make validate-changed` no-selection run was treated as
non-sufficient; focused pytest, full `tests/test_legacy_growth_guard.py`,
`pre-commit run --all-files`, and post-commit `make validate-changed` all
passed. The post-commit run selected `tests/test_api.py`,
`tests/test_app_public_surface.py`, `tests/test_bodyfat.py`,
`tests/test_legacy_growth_guard.py`, and `tests/test_main_paywall_bootstrap.py`.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/bodyfat-canonical-bootstrap-oracle-packet.json`
- Artifact:
  `artifacts/orchestration/experiments/results/bodyfat-canonical-bootstrap-oracle-result.json`
- Experiment id: `exp-7c4838ebc835`
- Status: accepted
- Runner mode: `oracle_only_governance_reviewer`
- Oracles passed:
  - `python3 -m pytest -q tests/test_main_paywall_bootstrap.py -k bodyfat`
  - `python3 -m pytest -q tests/test_legacy_growth_guard.py`
  - `python3 scripts/ci/check_legacy_growth_guard.py`
- Result: 3/3 oracle commands passed; `mutated_paths=[]`;
  `shared_tree_untouched=true`; source diff was applied in the isolated
  checkout.
- Contribution kind: `oracle_review`
- Co-author required: yes
- Co-author trailer is present on implementation commit
  `d8c2313fc157ca39109268e262af7644056e028b`.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_paywall_bootstrap.py -k bodyfat`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_legacy_growth_guard.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_api.py::test_v1_bodyfat tests/test_api.py::test_v1_bodyfat_missing_hip tests/test_api.py::test_bodyfat_router_export_uses_canonical_package_path tests/test_app_bodyfat_v1.py tests/test_bodyfat_labels_coverage.py tests/edges/test_bodyfat_edges.py tests/test_bodyfat_shim.py tests/test_docker_workflow_build_path_contract.py::test_docker_entrypoint_keeps_bodyfat_hidden_but_routable tests/test_app_public_surface.py::test_app_public_surface_smoke`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" make openapi-check DEV_PYTHON="$VENV_PYTHON"`
- PASS: `pre-commit run --all-files`
- PASS: `make validate-changed`
- PASS: `git show --check --oneline HEAD`
- PASS after security-auditor fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_legacy_growth_guard.py`
- PASS after security-auditor fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_paywall_bootstrap.py -k bodyfat tests/test_api.py::test_v1_bodyfat tests/test_api.py::test_v1_bodyfat_missing_hip tests/test_api.py::test_bodyfat_router_export_uses_canonical_package_path tests/test_app_bodyfat_v1.py tests/test_bodyfat_labels_coverage.py tests/edges/test_bodyfat_edges.py tests/test_bodyfat_shim.py tests/test_docker_workflow_build_path_contract.py::test_docker_entrypoint_keeps_bodyfat_hidden_but_routable tests/test_app_public_surface.py::test_app_public_surface_smoke tests/test_legacy_growth_guard.py`
- PASS after security-auditor fix: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS after security-auditor fix: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS after security-auditor fix: `make validate-changed`
- PASS after security-auditor fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; make openapi-check DEV_PYTHON="$VENV_PYTHON"`
- PASS after security-auditor fix: `pre-commit run --all-files`
- PASS after security-auditor fix: `git diff --check`
- PASS after mypy hook fix:
  `pre-commit run --hook-stage pre-push mypy --files scripts/ci/check_legacy_growth_guard.py`
- PASS after mypy hook fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_legacy_growth_guard.py`
- PASS after mypy hook fix: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS after mypy hook fix: `pre-commit run --all-files`
- PASS: Codex Security scan `d9f75240-8a67-4c76-b8d6-e2062323022a`
  completed, 5/5 reviewed, 0 findings.
- PASS: `pulseplate-pr-review` dry-run report generated; only advisory
  `large-diff-risk` note, dispositioned above.
- PASS on push hook: changed-files mypy, pre-push backend pytest, full-repo
  Bandit, and Docker build test.

Full local `make verify` was not run per operator CPU constraint. This PR does
not claim merge readiness from local gates alone.

## Security Notes

No auth, billing, secrets, LLM, quota, rate-limit, entitlement, or tier policy
changes. The security-relevant change is a stricter legacy growth guard that now
rejects bodyfat route registration returning to `legacy_app.py`.

## Risks / Rollback

Risk: duplicate route ownership, OpenAPI visibility drift, or compatibility
prefix regression.

Mitigation: static route-family guard tests, legacy growth guard tests, direct
router compatibility tests, focused API parity tests, and OpenAPI check.

Rollback: revert this PR to restore the prior `legacy_app.py` bodyfat include
path. No migration, generated client, or persisted data rollback is required.

## Deferred / Follow-Ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-bodyfat-bmi-engine-delegation`:
  delegate bodyfat missing-BMI derivation to the canonical BMI engine in a
  separate parity-reviewed PR.

## Merge Readiness

Not merge-ready.

Required before merge:

- [ ] Current-head CI passes.
- [x] Post-open role passes completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan / finding discovery run.
- [x] `pulseplate-pr-review` completed.
- [ ] CodeRabbit/Sourcery/Cubic comments inspected and dispositioned on final
  current head.
- [ ] PR body mirrors this fixed-mapping artifact after artifact commit lands.
- [ ] Strict merge-readiness checks pass.
