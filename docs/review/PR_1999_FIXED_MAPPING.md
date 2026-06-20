# PR 1999 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1999

Branch: `codex/extract-route-family-bootstrap-guard`

## Summary

This PR extracts a shared static route-family bootstrap guard and migrates only
plan/shoplist export registration to it. Runtime route behavior, API-key
dependency, plan signed-token dependency, export 429 metadata, source route
OpenAPI visibility, final public OpenAPI hiding, reload idempotency, and
duplicate/foreign handler rejection are preserved.

## Scope

- Add `app/bootstrap/route_family.py` with `RouteMemberContract`,
  `ensure_route_family_registered(...)`, module+qualname callable matching, and
  recursive dependency traversal.
- Migrate only `app/main.py` plan export and shoplist export bootstrap wrappers
  to the shared static helper.
- Tighten plan source-router validation so unexpected source `APIRoute`s fail
  closed like shoplist.
- Keep dynamic legacy export aliases on their existing dedicated helper.
- Update `app/AGENTS.md` and `docs/architecture/backend_routing_map.md` for the
  canonical static-helper pattern.
- Remediate current-head CI security blockers introduced by the scanner/tooling
  surface: pin Trivy to `v0.71.2`, document and track the temporary Faraday
  Fastlane suppression, and isolate the Trivy action's transient upstream
  checkout from the PulsePlate filesystem scan.

## Out Of Scope

No `legacy_app.py` change, dynamic legacy alias migration, route migration, DB
migration, frontend/iOS change, generated OpenAPI/client diff, restaurant
moderation runtime work, or broad legacy refactor.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/0c79d0ade1a0.json`
- Runtime dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/0c79d0ade1a0.json --pretty`
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> qa-engineer-agent -> security-auditor -> bug-hunter`
- Starter: `check_preflight.py`, `check_agent_consistency.py`, and
  `task_bootstrap.py`; packet creation was treated as provenance only, not role
  execution.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `. .venv/bin/activate && python -m pytest -q tests/test_route_family_bootstrap.py tests/test_main_paywall_bootstrap.py tests/test_plan_export_additional.py tests/test_shoplist_export.py tests/test_export_signed.py tests/test_rate_limit_llm_and_exports_api.py tests/test_legacy_growth_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/test_pro_vip_route_dependency_guard.py tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py`
- PASS: `. .venv/bin/activate && python -m mypy app/bootstrap/route_family.py app/main.py`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `make openapi-check`
- PASS: `git diff --check`
- PASS: `pre-commit run --all-files`
- PASS after commit: `make validate-changed` selected
  `tests/test_main_paywall_bootstrap.py`,
  `tests/test_route_family_bootstrap.py`, and `tests/test_shoplist_export.py`
- PASS on push hook: changed-file mypy, pre-push backend pytest, full-repo
  Bandit, and Docker build test
- PASS: `. .venv/bin/activate && python -m pytest -q tests/test_trivy_ignore_policy_expiry.py tests/test_ci_workflow_pr_size_governance_contract.py -k 'faraday or trivy'`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-54297-faraday-fastlane.md`
- PASS: local Trivy `v0.71.2` filesystem scan with
  `--ignore-policy trivy/ignore-policy.rego`, `.trivyignore`,
  HIGH/CRITICAL severities, and JSON result count `0`.
- PASS: clean CI-style Trivy action reproduction with upstream
  `aquasecurity/trivy` checkout under `trivy/`, Docker workflow
  `skip-dirs: trivy`, `.trivy-ignore-policy.rego`, and JSON result count `0`.
- PASS: PR merge-ref Trivy action reproduction for GitHub synthetic merge commit
  `891d0f9f` with upstream `aquasecurity/trivy` checkout under `trivy/`, Docker
  workflow `skip-dirs: trivy`, `.trivy-ignore-policy.rego`, and JSON result
  count `0`.
- PASS after CI-remediation commits: `make validate-changed` selected
  `tests/test_ci_workflow_pr_size_governance_contract.py`,
  `tests/test_main_paywall_bootstrap.py`,
  `tests/test_route_family_bootstrap.py`,
  `tests/test_shoplist_export.py`, and
  `tests/test_trivy_ignore_policy_expiry.py`.
- PASS after CI-remediation commits: `pre-commit run --all-files`
- Not run: full `make verify`; this PR is not claiming merge readiness from
  local gates alone.

## Premortem Findings

Disposition: FIXED

Finding: static helper could accidentally absorb dynamic legacy export aliases.

Commit: `df9f7b0a0`

Evidence: `app/main.py` keeps `_include_legacy_export_alias_router_if_needed`
on the existing helper path; `app/AGENTS.md` documents that request-time rebound
aliases must not use the static helper; `docs/architecture/backend_routing_map.md`
records hidden legacy export aliases as separate compatibility routing.

Disposition: FIXED

Finding: auth, signed-token, 429 metadata, or OpenAPI hiding could drift during
deduplication.

Commit: `df9f7b0a0`

Evidence: `app/bootstrap/route_family.py` validates source route visibility and
429 metadata plus existing-route dependencies/status/visibility; `app/main.py`
declares plan CSV/PDF `_require_valid_token` only for those members; focused
pytest and `make openapi-check` passed.

Disposition: FIXED

Finding: pre-commit `make validate-changed` could false-green before first
commit because it selected no changed Python files.

Commit: `df9f7b0a0`

Evidence: the first `make validate-changed` run was treated as advisory only;
after commit, `make validate-changed` selected the changed route bootstrap tests
and passed.

## Experiment Runner Evidence

- Initial rejected artifact:
  `artifacts/orchestration/experiments/results/pr7-route-family-bootstrap-oracle-result.json`
  was rejected before oracle execution because the packet context omitted two
  changed paths. It is not used as readiness evidence.
- Artifact: `artifacts/orchestration/experiments/results/pr7-route-family-bootstrap-oracle-result-v3.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Oracles passed:
  - `python -m pytest -q tests/test_route_family_bootstrap.py tests/test_main_paywall_bootstrap.py tests/test_plan_export_additional.py tests/test_shoplist_export.py tests/test_export_signed.py tests/test_rate_limit_llm_and_exports_api.py tests/test_legacy_growth_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/test_pro_vip_route_dependency_guard.py tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py`
  - `python -m mypy app/bootstrap/route_family.py app/main.py`
  - `python3 scripts/ci/check_legacy_growth_guard.py`
  - `make openapi-check`
- Result: 4/4 oracle commands passed; `mutated_paths=[]`;
  `shared_tree_untouched=true`.
- Attribution: co-author trailer required and present on implementation commit
  `df9f7b0a0`.

## Post-Open Review Evidence

- PASS: post-open packet
  `artifacts/orchestration/task_packets/2ff0d1204c68.json` and dispatch
  manifest from
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/2ff0d1204c68.json --pretty`.
- PASS: post-open role order executed through the dispatch-declared sequence:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> backend-engineer -> architecture-specialist`.
- PASS: `qa-engineer-agent` post-open pass found no actionables and reran the
  focused plan/shoplist/static helper slice.
- PASS: `bug-hunter` post-open pass found no bugs and confirmed the PR stayed
  open, non-draft, and scoped.
- PASS: `security-auditor` post-open pass found no actionable security
  vulnerabilities and confirmed no `legacy_app.py`, DB, OpenAPI/client,
  subprocess, nosec, or secret-handling changes.
- PASS: `backend-engineer` post-open pass found no implementation blocker and
  reran focused pytest, auth/OpenAPI route probes, mypy, and diff-check
  evidence.
- PASS: `architecture-specialist` post-open pass found no architecture blocker
  and confirmed the helper is bounded to exact static route families while
  dynamic legacy aliases remain on their dedicated helper.
- PASS: Codex Security diff scan / finding discovery completed for
  `origin/main...HEAD` at `45958e10e3fd`.
  - Scan bundle:
    `/tmp/codex-security-scans/BMI-App_2025_clean/45958e10e3fd_20260620T092927Z`
  - Work ledger:
    `/tmp/codex-security-scans/BMI-App_2025_clean/45958e10e3fd_20260620T092927Z/artifacts/02_discovery/work_ledger.jsonl`
  - Report:
    `/tmp/codex-security-scans/BMI-App_2025_clean/45958e10e3fd_20260620T092927Z/report.md`
  - HTML report:
    `/tmp/codex-security-scans/BMI-App_2025_clean/45958e10e3fd_20260620T092927Z/report.html`
  - Result: 2/2 `deep_review_input.csv` rows reviewed; no candidates emitted;
    report format validation and HTML rendering passed.
- PASS / NOT-A-BUG: `pulseplate-pr-review` dry-run completed and emitted one
  advisory `note` for diff size (`large-diff-risk`, 1038 changed lines).
  Evidence: PR body now has a `## PR Size Justification` explaining that this
  is one coherent static-helper + wrapper + focused-test/doc slice; local
  focused gates, post-open role passes, Codex Security, and review artifacts
  cover the slice. No code defect or merge-blocking finding was emitted by the
  dry-run report.
- External review state:
  - CodeRabbit GitHub app reported one actionable line-anchor comment after
    the Faraday CI remediation; disposition is recorded below as FIXED.
  - CodeRabbit CLI: attempted with authenticated CLI `0.6.0`, command
    `coderabbit review --agent -t committed -c AGENTS.md`; failed with service
    timeout `77b7b770-2afd-427d-a68a-0a6cf34fcb1d`, so CLI output is not used
    as CodeRabbit review evidence.
  - Sourcery: PASS / no actionable review; generated reviewer guide and
    "looks great" review comment.
  - Cubic: skipped/neutral; no actionable comment available.
- Current-head CI note: after head `45958e10e3fd`, `pr_scope_guard` failed
  because the PR body had `## Tests / Validation` instead of the literal
  required `## Tests`; PR body was edited to add exact `## Tests` and
  `## PR Size Justification`.

## CI Security Remediation Evidence

- FIXED: Docker Build and Push `security-scan` initially failed on Trivy
  `CVE-2026-54297` for `faraday@1.10.5` in `ios/Gemfile.lock`, fixed version
  `2.14.3`.
  - Commit: `879d25145`
  - Evidence: `.github/workflows/build.yml` and `.github/workflows/trivy.yml`
    pin Trivy `v0.71.2`; `trivy/ignore-policy.rego` contains an exact,
    temporary Faraday suppression; `docs/security/CVE-2026-54297-faraday-fastlane.md`
    records Fastlane resolver evidence and removal conditions;
    `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-faraday-cve-2026-54297`
    tracks removal.
- FIXED: Docker filesystem scan failed again because
  `aquasecurity/setup-trivy` checks out the upstream Trivy repository into
  workspace path `trivy`, causing the PulsePlate filesystem scan to report
  transient upstream `trivy/go.mod` vulnerabilities that are not part of the
  repository checkout or product runtime.
  - Commit: `abc0c9e67`
  - Evidence: `.github/workflows/build.yml:324` sets `skip-dirs: trivy` for
    the Docker filesystem scan; `docs/security/CVE-2026-54297-faraday-fastlane.md`
    documents the action checkout collision; clean CI-style local reproduction
    with the upstream `trivy` checkout and `skip-dirs: trivy` returned zero
    HIGH/CRITICAL JSON findings.
- FIXED: CodeRabbit reported stale Evidence Anchor lines in
  `docs/security/CVE-2026-54297-faraday-fastlane.md`.
  - Commit: `1113689fe`
  - Evidence: `docs/security/CVE-2026-54297-faraday-fastlane.md:118` points to
    the exact CVE match, `:120` points to the stable identifier set, and
    `:125` points to the backlog anchor line; `tests/test_trivy_ignore_policy_expiry.py`
    asserts these anchors.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open actionables are recorded below with FIXED / NOT-A-BUG / DEFERRED
disposition evidence before thread resolution or merge-readiness claims.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1999#discussion_r3447050572 -> 1113689fe
Disposition: FIXED
Commit: 1113689fe
Evidence: docs/security/CVE-2026-54297-faraday-fastlane.md:118; docs/security/CVE-2026-54297-faraday-fastlane.md:120; docs/security/CVE-2026-54297-faraday-fastlane.md:125; tests/test_trivy_ignore_policy_expiry.py line-anchor assertions.

## Merge Readiness

- [ ] Required current-head CI complete and passing
- [x] Post-open role lane complete:
  `qa-engineer-agent -> bug-hunter -> security-auditor -> backend-engineer -> architecture-specialist`
- [x] Codex Security diff scan / finding discovery complete
- [x] `pulseplate-pr-review` complete
- [x] CodeRabbit/Sourcery/Cubic actionables dispositioned
- [ ] Strict merge readiness wrapper passes after latest review activity
