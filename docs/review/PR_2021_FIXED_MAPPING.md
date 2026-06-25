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
- [ ] Post-open discussion-thread pass pending.
- [ ] CodeRabbit comments/actionables inspected.
- [ ] Sourcery comments/actionables inspected.
- [ ] Cubic comments/actionables inspected.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Mapping Notes

Initial PR open: no human review threads existed at artifact creation. Any
post-open actionable bot or human findings must be fixed, mapped in
`## Fixed in Commit Mapping` with disposition proof, mirrored in the PR body,
and only then resolved.

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
- Result:
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
- [ ] Post-open role passes completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [ ] Codex Security diff scan / finding discovery run if available.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit/Sourcery/Cubic comments inspected and dispositioned.
- [ ] PR body mirrors this fixed-mapping artifact after artifact commit lands.
- [ ] Strict merge-readiness checks pass.
