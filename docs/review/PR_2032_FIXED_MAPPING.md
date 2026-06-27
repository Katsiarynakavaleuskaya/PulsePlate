# PR 2032 Fixed Mapping

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/09866a6f8ccb.json`
- Branch: `codex/dependency-cleanup-faraday-runtime-drift`
- Base: `main`
- Worktree: isolated PR2 dependency cleanup worktree
- Role order executed pre-open:
  `agent-coordinator -> qa-engineer-agent -> security-auditor -> bug-hunter`
- Packet creation was treated as provenance only, not role execution.

## Scope Boundary

- In scope: Faraday lock remediation, exact Trivy scanner-lag policy, FastAPI
  and Pydantic runtime drift, Ruff drift, duplicate Pillow source cleanup,
  resolver-owned `pydantic-core` fallback metadata, and FastAPI lazy-router
  compatibility guards.
- Out of scope: PR #2025, PR #2026, direct PR #2028 segmentation-fault fix,
  full TestClient/httpx2 migration, and full local `make verify`.

## Emergency Operator Exception

- operator approval: approved for the combined PR2 dependency remediation scope
  requested by the operator.
- emergency exception: approved for PR2 dependency remediation scope.
- Scope note: PR2 intentionally keeps Faraday remediation, runtime dependency
  drift, lock/doc/test updates, and compatibility guards together; splitting
  this lane would leave scanner policy, dependency locks, and runtime contract
  proof inconsistent across temporary PR heads.
- Trusted labels applied to PR #2032: `scope/operator-approved`,
  `scope/emergency-approved`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Resolved review threads mapped with disposition proof: 6.
- [x] Pre-open premortem findings dispositioned.
- [x] Experiment Runner oracle-only governance evidence recorded.
- [x] Local focused gates, `make validate-changed`, and
  `pre-commit run --all-files` passed before PR open.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor`
  completed.
- [x] Codex Security diff scan for head
  `f28857f55e010c85d94dc4bdea8869239f69a362` completed; one finding was
  fixed in `e1531a004f`.
- [x] Fresh Codex Security diff scan for current head
  `89eac881f07996ca56c36f161134c8bdd906f716` completed with no findings.
- [x] `pulseplate-pr-review` completed; advisory large-diff note dispositioned.
- [ ] CodeRabbit, Sourcery, and Cubic current-head actionables must be
  checked and dispositioned after bot review completes.
- [ ] Strict merge-readiness wrapper with auth and the mandatory wait-window
  remain required before merge.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 97bba456fbda8fb26c878b9b439145b41b4f6b52
Evidence: `ios/Gemfile.lock`, `trivy/ignore-policy.rego`, `requirements*.in`, `requirements*.txt`, `constraints.txt`, `app/effective_routes.py`, route/metrics guards, focused dependency/runtime tests, `make validate-changed`, `pre-commit run --all-files`, Experiment Runner accepted result, and pre-push hooks all passed.
Reason: Implements PR2 dependency cleanup by remediating Faraday to `1.10.6`, refreshing FastAPI/Pydantic/Ruff drift narrowly, removing duplicate Pillow source declarations, updating resolver-owned `pydantic-core` fallback metadata, and preserving FastAPI lazy-router route contracts.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032 -> 97bba456fbda8fb26c878b9b439145b41b4f6b52

Disposition: FIXED
Commit: ddfb847d31e09991170c15363b1d3dcda3e81675
Evidence: `app/effective_routes.py`, `app/bootstrap/pro_contracts.py`, `app/routers/billing.py`, `app/routers/vip_registration.py`, `tests/test_main_paywall_bootstrap.py`, `tests/test_python_supply_chain_controls.py`, `tests/test_trivy_ignore_policy_expiry.py`, full `tests/test_main_paywall_bootstrap.py`, focused bug-hunter regression tests, `pre-commit run --all-files`, `make validate-changed`, dependency-surface validators, and fail-closed local Trivy `ios` scan all passed.
Reason: Closes post-open bug-hunter findings by rejecting foreign existing route owners for PRO contract, billing, and FitChef insight routes; asserting exact runtime dependency pins instead of accepting compatible ranges; and slicing the Faraday Trivy policy block to the specific CVE section.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032 -> ddfb847d31e09991170c15363b1d3dcda3e81675
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032#discussion_r3486513877 -> ddfb847d31e09991170c15363b1d3dcda3e81675
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032#discussion_r3486513878 -> ddfb847d31e09991170c15363b1d3dcda3e81675
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032#discussion_r3486513879 -> ddfb847d31e09991170c15363b1d3dcda3e81675

Disposition: FIXED
Commit: bc7fb204e06cd69606f558c5ecb30f97d0d2b8e0
Evidence: `app/effective_routes.py`, `app/middleware/metrics.py`, `app/routers/billing.py`, `app/routers/vip_registration.py`, `tests/test_main_paywall_bootstrap.py`, `tests/test_metrics.py`, focused CodeRabbit regression tests, full `tests/test_main_paywall_bootstrap.py tests/test_metrics.py`, `ruff`, `mypy`, `pre-commit run --all-files`, and `make validate-changed` all passed.
Reason: Closes CodeRabbit actionables by rejecting duplicate source route owners, failing closed on missing FitChef insight POST routes, rejecting partial preexisting billing route state, and normalizing metrics route labels before caching.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032#discussion_r3486513876 -> bc7fb204e06cd69606f558c5ecb30f97d0d2b8e0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032#discussion_r3486601869 -> bc7fb204e06cd69606f558c5ecb30f97d0d2b8e0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032#discussion_r3486601870 -> bc7fb204e06cd69606f558c5ecb30f97d0d2b8e0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032#pullrequestreview-4585986171 -> bc7fb204e06cd69606f558c5ecb30f97d0d2b8e0

Disposition: FIXED
Commit: e1531a004f2d4fadbb98260e1b996e664f80fc15
Evidence: Codex Security scan `4ccd9f2f-38f2-4f24-a669-8148cfea44d6` reported finding `csf_c6ff5339238662d1a8e3b294`; sealed report path `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-kx1ykF/dependency-cleanup-faraday-runtime-drift/f28857f55e010c85d94dc4bdea8869239f69a362_20260627T193438Z_sxo3irk9/report.md`; `app/bootstrap/pro_contracts.py` now requires same-endpoint existing PRO contract routes to preserve `require_pro_tier`; `tests/test_pro_contracts_bootstrap.py` adds a regression for direct same-endpoint routes without router-level dependencies. Focused `python -m pytest tests/test_pro_contracts_bootstrap.py tests/test_main_paywall_bootstrap.py -q` passed (`160 passed`, one known Starlette/httpx2 warning), `ruff check` passed, and `mypy app/bootstrap/pro_contracts.py --no-incremental --cache-dir=/dev/null` passed.
Reason: Closes Codex Security finding "PRO contract bootstrap accepts same-endpoint routes without paid-tier dependency" by validating the effective route dependency metadata before treating existing PRO contract routes as canonical.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032 -> e1531a004f2d4fadbb98260e1b996e664f80fc15

Disposition: DEFERRED
Evidence: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fastapi-compatibility-gates`
Reason: Starlette emits `StarletteDeprecationWarning` because `starlette.testclient` still uses the deprecated `httpx` backend when `httpx2` is absent; this PR tracks the migration decision instead of suppressing the warning broadly.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2032

## Premortem Closure

- Decision: proceed with changes.
- Finding PM-2032-001 FastAPI lazy-router route drift:
  - Disposition: FIXED
  - Evidence: `app/effective_routes.py`, route-family tests, OpenAPI namespace
    guards, metrics tests, and canonical bootstrap idempotency proof.
- Finding PM-2032-002 Faraday suppression hides stale vulnerable version:
  - Disposition: FIXED
  - Evidence: old `faraday@1.10.5` policy shape removed; exact
    `faraday@1.10.6` scanner-lag policy and lockfile tests added.
- Finding PM-2032-003 unsafe dependency-regeneration churn:
  - Disposition: FIXED
  - Evidence: lockfile diff is limited to expected FastAPI, Pydantic,
    `pydantic-core`, Ruff, and Faraday pins.
- Finding PM-2032-004 Starlette TestClient/httpx2 future drift:
  - Disposition: DEFERRED
  - Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fastapi-compatibility-gates`

## Post-Open Role Dispositions

- Post-open `qa-engineer-agent` pass: completed.
  - Disposition: FIXED
  - Evidence: PR body carries the exact operator/emergency exception text,
    trusted labels `scope/operator-approved` and `scope/emergency-approved`
    are applied, local PR size governance passed, Phase 1 docs gate passed,
    Phase 2 PR body gate passed, and mapping validator passed.
- Post-open `bug-hunter` pass: completed.
  - Finding BH-2032-001 PRO contract route-owner false green:
    - Disposition: FIXED
    - Commit: ddfb847d31e09991170c15363b1d3dcda3e81675
    - Evidence: `app/bootstrap/pro_contracts.py` rejects foreign or duplicate
      owners and
      `tests/test_main_paywall_bootstrap.py::test_pro_contract_registration_rejects_foreign_existing_handlers`
      passed.
  - Finding BH-2032-002 billing route-owner false green:
    - Disposition: FIXED
    - Commit: ddfb847d31e09991170c15363b1d3dcda3e81675
    - Evidence: `app/routers/billing.py` rejects foreign or duplicate owners
      and
      `tests/test_main_paywall_bootstrap.py::test_billing_registration_rejects_foreign_existing_handlers`
      passed.
  - Finding BH-2032-003 FitChef insight route-owner false green:
    - Disposition: FIXED
    - Commit: ddfb847d31e09991170c15363b1d3dcda3e81675
    - Evidence: `app/routers/vip_registration.py` rejects foreign or duplicate
      owners and
      `tests/test_main_paywall_bootstrap.py::test_vip_route_registration_rejects_foreign_existing_fitchef_insight_route`
      passed.
  - Finding BH-2032-004 runtime pin exactness:
    - Disposition: FIXED
    - Commit: ddfb847d31e09991170c15363b1d3dcda3e81675
    - Evidence:
      `tests/test_python_supply_chain_controls.py::test_runtime_dependency_profiles_pin_fastapi_pydantic_refresh`
      now asserts exact `==` pins and passed.
  - Finding BH-2032-005 Faraday policy block fragility:
    - Disposition: FIXED
    - Commit: ddfb847d31e09991170c15363b1d3dcda3e81675
    - Evidence:
      `tests/test_trivy_ignore_policy_expiry.py::test_faraday_fastlane_suppression_tracks_1_10_6_scanner_lag`
      uses the specific `# CVE-2026-54297` policy block and passed.
- Post-open `security-auditor` pass: completed for the pushed
  `f28857f55e010c85d94dc4bdea8869239f69a362` head; no additional
  security/correctness findings beyond the Codex Security discovery item below.
- Codex Security diff scan / finding discovery:
  - Scan: `4ccd9f2f-38f2-4f24-a669-8148cfea44d6`
  - Scanned head: `f28857f55e010c85d94dc4bdea8869239f69a362`
  - Report:
    `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-kx1ykF/dependency-cleanup-faraday-runtime-drift/f28857f55e010c85d94dc4bdea8869239f69a362_20260627T193438Z_sxo3irk9/report.md`
  - Finding `csf_c6ff5339238662d1a8e3b294`:
    - Disposition: FIXED
    - Commit: e1531a004f2d4fadbb98260e1b996e664f80fc15
    - Evidence:
      `app/bootstrap/pro_contracts.py` now checks `route_has_dependency_call`
      for `require_pro_tier`; `tests/test_pro_contracts_bootstrap.py`
      reproduces and rejects same-endpoint direct routes without the
      router-level PRO dependency.
  - New material head after `e1531a004f` was covered by the current-head
    follow-up scan below.
  - Current-head follow-up scan:
    - Scan: `99c1b779-1407-4f52-b799-280e56d5bc41`
    - Scanned head: `89eac881f07996ca56c36f161134c8bdd906f716`
    - Report:
      `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-kx1ykF/dependency-cleanup-faraday-runtime-drift/89eac881f07996ca56c36f161134c8bdd906f716_20260627T201257Z_ajo9b77e/report.md`
    - Manifest:
      `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-kx1ykF/dependency-cleanup-faraday-runtime-drift/89eac881f07996ca56c36f161134c8bdd906f716_20260627T201257Z_ajo9b77e/scan-manifest.json`
    - Findings:
      `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-kx1ykF/dependency-cleanup-faraday-runtime-drift/89eac881f07996ca56c36f161134c8bdd906f716_20260627T201257Z_ajo9b77e/findings.json`
    - Coverage:
      `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-kx1ykF/dependency-cleanup-faraday-runtime-drift/89eac881f07996ca56c36f161134c8bdd906f716_20260627T201257Z_ajo9b77e/coverage.json`
    - Result: no reportable findings; previous PRO contract route dependency
      finding no longer reproduces.
- `pulseplate-pr-review`: completed.
  - Report: `/tmp/pulseplate_pr2032_review.md`
  - Finding PPR-2032-001 large diff risk:
    - Disposition: NOT-A-BUG
    - Evidence: Operator-approved emergency scope keeps Faraday remediation,
      runtime dependency drift, lock/doc/test updates, and compatibility guards
      together; PR body and this mapping document the split rationale, local
      focused gates, `make validate-changed`, `pre-commit run --all-files`,
      pre-push hooks, role passes, and current-head Codex Security scan.
    - Reason: `pulseplate-pr-review` classified the finding as advisory
      `NEEDS-HUMAN` review-planning evidence, not a deterministic defect or
      auto-postable blocker. The required split rationale and targeted gates
      are already documented.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/pr2-dependency-cleanup-oracle-packet-v2.json`
- Artifact: `artifacts/orchestration/experiments/results/pr2-dependency-cleanup-oracle-result-v3.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Source diff applied: `true`.
- Failure class: `null`.
- Contribution kind: `commit_decision`.
- Co-author required: `true`.
- Commit trailer included in implementation commit
  `97bba456fbda8fb26c878b9b439145b41b4f6b52`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Oracle commands:
  - `python -m pytest tests/test_python_supply_chain_controls.py tests/test_install_locked_python_requirements.py tests/test_trivy_ignore_policy_expiry.py`
  - `python -m pytest tests/test_pro_vip_route_dependency_guard.py tests/test_shoplist_export.py tests/test_openapi_namespace_guards.py tests/test_route_family_bootstrap.py tests/test_main_paywall_bootstrap.py::test_route_member_contracts_reject_non_http_routes tests/test_main_paywall_bootstrap.py::test_route_member_contracts_reject_framework_only_route_methods tests/test_main_paywall_bootstrap.py::test_route_member_contracts_reject_empty_source_router tests/test_main_paywall_bootstrap.py::test_route_family_rejects_non_http_source_routes_for_static_tail_coverage tests/test_metrics.py`
  - `python scripts/ci/check_trivy_ignore_policy_expiry.py`
  - `python scripts/ci/check_python_dependency_surfaces.py`
  - `python verify_requirements.py`
  - `python -c 'from pathlib import Path; lock=Path("ios/Gemfile.lock").read_text(); assert "faraday (1.10.6)" in lock; assert "faraday (1.10.5)" not in lock; assert "fastlane (2.235.0)" in lock; print("ios lock verified")'`

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `python scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python verify_requirements.py`
- PASS:
  `python -m pytest tests/test_python_supply_chain_controls.py tests/test_install_locked_python_requirements.py tests/test_trivy_ignore_policy_expiry.py`
  (`224 passed`, one known Starlette/httpx2 warning).
- PASS: route/runtime compatibility pytest bundle
  (`85 passed`, one known Starlette/httpx2 warning).
- PASS: changed-surface `ruff check`.
- PASS: changed app-module `mypy --no-incremental --cache-dir=/dev/null`.
- PASS: canonical bootstrap idempotency script.
- PASS: `bundle check` in `ios`.
- PASS: Ruby lock verification for `faraday (1.10.6)`, no
  `faraday (1.10.5)`, and `fastlane (2.235.0)`.
- PASS: `pre-commit run --all-files`.
- PASS:
  `VENV_PYTHON=<repo>/.venv/bin/python DEV_PYTHON=<repo>/.venv/bin/python make validate-changed`.
- PASS: post-bug-hunter full `tests/test_main_paywall_bootstrap.py`
  (`154 passed`, one known Starlette/httpx2 warning).
- PASS: post-bug-hunter focused route-owner, runtime pin exactness, and
  Faraday policy block regression tests.
- PASS: fail-closed local Trivy scan for `ios` high/critical vulnerabilities
  (`0` findings in `Gemfile.lock`, `Package.resolved`, and Xcode workspace
  `Package.resolved`; scanner-lag suppression still reported as suppressed).
- PASS: post-bug-hunter `pre-commit run --all-files`.
- PASS: post-bug-hunter
  `VENV_PYTHON=<repo>/.venv/bin/python DEV_PYTHON=<repo>/.venv/bin/python make validate-changed`.
- PASS: CodeRabbit follow-up focused regression tests for duplicate source
  route lookup, partial billing state, missing FitChef insight route, and
  metrics trailing-slash normalization (`7 passed`, one known
  Starlette/httpx2 warning).
- PASS: full impacted `tests/test_main_paywall_bootstrap.py tests/test_metrics.py`
  (`196 passed`, one known Starlette/httpx2 warning).
- PASS: CodeRabbit follow-up `ruff check` and changed app-module
  `mypy --no-incremental --cache-dir=/dev/null`.
- PASS: CodeRabbit follow-up `pre-commit run --all-files`.
- PASS: CodeRabbit follow-up
  `VENV_PYTHON=<repo>/.venv/bin/python DEV_PYTHON=<repo>/.venv/bin/python make validate-changed`.
- PASS: pre-push hooks during `git push`, including `mypy`, `pip-audit`,
  backend pre-push pytest, full-repo Bandit, and docker build test.
- PASS: Codex Security finding fix focused pytest:
  `python -m pytest tests/test_pro_contracts_bootstrap.py tests/test_main_paywall_bootstrap.py -q`
  (`160 passed`, one known Starlette/httpx2 warning).
- PASS: Codex Security finding fix `ruff check app/bootstrap/pro_contracts.py tests/test_pro_contracts_bootstrap.py`.
- PASS: Codex Security finding fix
  `mypy app/bootstrap/pro_contracts.py --no-incremental --cache-dir=/dev/null`.
- PASS: post-fix current-head Codex Security diff scan
  `99c1b779-1407-4f52-b799-280e56d5bc41`
  (`0` findings, `7/7` reviewed surfaces).
- PASS: `pulseplate-pr-review` dry-run report completed; only advisory
  large-diff-risk note dispositioned as `NOT-A-BUG` with operator-approved
  split rationale and validation evidence.

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. The operator explicitly requested the
machine-heavy exception for this dependency lane, so this PR used focused local
dependency/runtime tests, Experiment Runner oracle evidence,
`make validate-changed`, `pre-commit run --all-files`, and pre-push hooks.
Merge readiness still requires current-head CI parity, review-thread
dispositions, post-open role passes, Codex Security diff scan / finding
discovery, `pulseplate-pr-review`, strict merge-readiness checks with auth, and
the mandatory wait-window.

## Dependency Delta Proof

- `ios/Gemfile.lock`: `faraday 1.10.5` -> `1.10.6`; Fastlane remains `2.235.0`.
- Python runtime pins: FastAPI `0.138.1`, Pydantic `2.13.4`, resolver-owned
  `pydantic-core 2.46.4`, Starlette unchanged at `1.3.1`.
- Dev tooling: Ruff `0.15.19`.
- Source requirements keep a single Pillow declaration and the existing
  `pillow 12.2.0` lock.

## Merge Readiness

- [ ] Current-head CI inspected and passing for the latest pushed head SHA.
- [ ] CodeRabbit PASS / no actionables confirmed.
- [ ] Sourcery PASS / no actionables confirmed.
- [ ] Cubic PASS / no actionables confirmed.
- [ ] Post-open role passes complete.
- [x] Codex Security diff scan / finding discovery complete once for the
  material PR head.
- [x] `pulseplate-pr-review` complete.
- [ ] Strict merge-readiness wrapper with auth passes.
- [ ] Mandatory wait-window satisfied.
