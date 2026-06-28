# PR 2036 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036
Title: `ci(deps): add private PyPI proxy health gate and mirror parity contract`
Branch: `codex/private-python-proxy-health-gate`

## Summary

This PR adds an early, stdlib-only private Python proxy health/parity gate for
`PULSEPLATE_PYTHON_INDEX_URL`. The gate fails before expensive Python setup when
the canonical packages host is down, a project page is empty, credentials are
embedded in the index URL, a public package index is used, or exact locked pins
are missing from representative Simple API project pages.

In scope:

- `scripts/ci/check_private_python_proxy_health.py`
- early `private_python_proxy_health` CI job
- URL, credential, project-page, `.netrc`, and exact-pin parity tests
- dependency/runbook/security/backlog documentation for the packages host
- test-only effective-route guard updates for the current `test-main`
  `_IncludedRouter` fallout blocking this PR

Out of scope:

- Cloudflare, DigitalOcean, or devpi origin configuration changes
- Starlette/httpx2 migration
- dependency lock refresh
- public PyPI fallback
- emergency wheel manifest retirement
- marketing apex changes
- application runtime changes

## Lane Start Provenance

- Worktree: `worktrees/private-python-proxy-health-gate-rebased`
- Branch: `codex/private-python-proxy-health-gate-rebased`
- PR branch published as: `codex/private-python-proxy-health-gate`
- Packet: `artifacts/orchestration/task_packets/f4c7e75bb9f3.json`
- Packet creation was treated as provenance only, not role execution.
- Pre-open role/review evidence was collected before the initial PR open.
- Post-open `bug-hunter` and `security-auditor` findings were fixed before this
  mapping artifact was added.

## Operator Recovery

- The operator recovered the DigitalOcean/devpi origin for
  `packages.pulseplate.app` out of band before the repo PR was finalized.
- Canonical project-page probe uses:
  `https://packages.pulseplate.app/root/pulseplate/+simple/<project>/`
- `pydantic-core` is intentionally not a default fast-gate probe because its
  Simple API page can be large enough to turn the health job into a timeout
  test. Native/security coverage is represented by `cryptography`; pure Python
  and CI-tool coverage are represented by `aiosqlite`, `requests`,
  `pytest-xdist`, `hypothesis`, and `pgvector`.

## Implementation Commits

- `eb99d3145` - `ci(deps): add private Python proxy health gate`
- `bc9c1868f` - `fix(ci): harden private proxy health gate`
- `c49b6de37` - `fix(ci): close proxy health review findings`
- `13c220165` - `fix(ci): redact netrc parser diagnostics`
- `987139987` - `fix(ci): require exact netrc proxy credentials`
- `cddea300b` - `fix(ci): align proxy health parity with installs`
- `c75462056` - `docs(review): map connector review fixes`
- `991399674` - `docs(runbook): fix private proxy triage headings`
- `51fecbb9f` - `test(api): align route guards with effective routes`
- `651ea0fc7` - `test(api): cover effective routes in remaining guards`
- `54669d629` - `docs(review): map remaining route guard fix`
- `fa3437b08` - `docs(review): remove local path evidence`
- `58c5881e2` - `test(api): use effective routes for runtime env guard`

## Discussion Thread Pass

- [x] Discussion-thread pass completed for local/review-agent findings known at
  mapping time.
- [x] Fixed in commit mapping completed for post-open review-agent findings.
- [x] Machine-heavy local `make verify` deferral documented.
- [x] Post-open `bug-hunter` findings fixed.
- [x] Post-open `security-auditor` findings fixed.
- [ ] CodeRabbit, Sourcery, Cubic, and current-head CI must be checked again
  after the rebased head is pushed.
- [ ] Strict merge-readiness wrapper with auth and the mandatory wait-window
  remain required before merge.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: eb99d3145
Evidence: `scripts/ci/check_private_python_proxy_health.py`, `.github/workflows/ci.yml`, `tests/test_private_python_proxy_health.py`, `tests/test_private_python_proxy_workflow_contract.py`, `tests/test_python_supply_chain_controls.py`, `RUNBOOK_AGENT.md`, `docs/DEPENDENCY_MANAGEMENT.md`, `docs/security/PRIVATE_PYTHON_PROXY_HEALTH_GATE.md`, `docs/roadmap/BACKLOG_LEDGER.md`, and `docs/review/PR_PRIVATE_PYPI_PROXY_HEALTH_GATE_PREMORTEM.md`.
Reason: Adds the private proxy health checker, early CI job, exact-pin mirror parity checks, URL/credential policy, and docs for the packages-host contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036 -> eb99d3145

Disposition: FIXED
Commit: bc9c1868f
Evidence: `scripts/ci/check_private_python_proxy_health.py`, `.github/workflows/ci.yml`, `tests/test_private_python_proxy_health.py`, `tests/test_private_python_proxy_workflow_contract.py`, and `tests/test_python_supply_chain_controls.py`.
Reason: Closes post-open review-agent findings by making protected credentials main-only and `.netrc`-based, enforcing the canonical same-host simple root, disabling checkout credential persistence in the health job, including `requirements-test.txt` / CI-tool representative projects, rejecting root devpi credentials, and strengthening log redaction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036 -> bc9c1868f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487777902 -> bc9c1868f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487777905 -> bc9c1868f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487777910 -> bc9c1868f

Disposition: FIXED
Commit: c49b6de37
Evidence: `scripts/ci/check_private_python_proxy_health.py`, `tests/test_private_python_proxy_health.py`, `tests/test_private_python_proxy_workflow_contract.py`, `docs/DEPENDENCY_MANAGEMENT.md`, `RUNBOOK_AGENT.md`, and `docs/security/PRIVATE_PYTHON_PROXY_HEALTH_GATE.md`.
Reason: Closes review findings by making exact-pin parsing fail closed on extra specifiers and conflicting pins, documenting the complete checker reason-code matrix, adding a docs Phase1 evidence anchor, and adding deterministic coverage that `pydantic-core` stays out of the fast proxy probe.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#pullrequestreview-4587443285 -> c49b6de37
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487778312 -> c49b6de37
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487777907 -> c49b6de37
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487777909 -> c49b6de37
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487777911 -> c49b6de37

Disposition: FIXED
Commit: 13c220165
Evidence: `scripts/ci/check_private_python_proxy_health.py` and `tests/test_private_python_proxy_health.py`.
Reason: Closes the latest CodeRabbit netrc diagnostic finding by replacing raw parser exception text with the exception class name while preserving exception chaining, and adds CLI failure-path plus netrc parser-redaction tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#pullrequestreview-4587464897 -> 13c220165
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487801734 -> 13c220165

Disposition: FIXED
Commit: 987139987
Evidence: `scripts/ci/check_private_python_proxy_health.py` and `tests/test_private_python_proxy_health.py`.
Reason: Closes the latest CodeRabbit exact-machine `.netrc` and test-fixture findings by rejecting `.netrc default` fallback for proxy credentials and decoupling Simple API HTML fixtures from production normalization helpers.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#pullrequestreview-4587510947 -> 987139987
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487852990 -> 987139987
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487852992 -> 987139987

Disposition: FIXED
Commit: cddea300b
Evidence: `.github/workflows/ci.yml`, `scripts/ci/check_private_python_proxy_health.py`, `tests/test_private_python_proxy_health.py`, `tests/test_private_python_proxy_workflow_contract.py`, and `tests/test_python_supply_chain_controls.py`.
Reason: Closes the latest connector findings by aligning protected-main proxy source with downstream vars-only setup jobs, rejecting `root` before writing `.netrc`, and requiring exact pinned wheel artifacts rather than sdist/zip links for mirror parity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487778311 -> cddea300b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487806508 -> cddea300b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487806509 -> cddea300b

Disposition: NOT-A-BUG
Evidence: `scripts/ci/check_private_python_proxy_health.py` supports exact-host `.netrc` authentication through `--netrc-file`/`PULSEPLATE_PYTHON_NETRC`, and `.github/workflows/ci.yml` writes protected read-only devpi credentials to `$HOME/.netrc` only on protected main. The checker intentionally does not implement a `PULSEPLATE_PYTHON_TRUSTED_HOST` TLS bypass because this gate verifies the canonical HTTPS packages origin before pip install; a cert/TLS failure is proxy health evidence, not a condition to skip.
Reason: The valid auth portion is implemented. Mirroring pip's trusted-host bypass in the stdlib probe would weaken the packages-origin health contract this PR is adding.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487778314

Disposition: NOT-A-BUG
Evidence: `tests/test_private_python_proxy_health.py::test_main_default_projects_exclude_large_pydantic_core_probe` pins the default fast probe list to `aiosqlite`, `cryptography`, `requests`, `pytest-xdist`, `hypothesis`, and `pgvector`; `docs/review/PR_2036_FIXED_MAPPING.md` records the operator decision that `pydantic-core` is too large for the fast health gate. Native/security representative parity is covered by `cryptography`.
Reason: `pydantic-core` remains intentionally out of the default fail-fast job so the health gate diagnoses proxy/mirror health instead of becoming another large-page timeout. It can still be supplied explicitly with `--project pydantic-core` for manual parity checks.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036#discussion_r3487806510

Disposition: FIXED
Commit: 991399674
Evidence: `RUNBOOK_AGENT.md`; local `npx --yes markdownlint-cli2 RUNBOOK_AGENT.md docs/DEPENDENCY_MANAGEMENT.md docs/security/PRIVATE_PYTHON_PROXY_HEALTH_GATE.md` returned `Summary: 0 error(s)`.
Reason: Closes the current-head Docs Phase1 markdownlint failure by converting private-proxy triage pseudo-headings from bold paragraphs to real markdown headings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28322567502/job/83906990954 -> 991399674

Disposition: FIXED
Commit: 51fecbb9f
Evidence: `tests/test_env_guards.py`, `tests/test_bmi_registration_router_coverage.py`, `tests/test_legacy_weekly_plan_alias_api.py`, `tests/test_restaurant_moderation_bootstrap.py`, `tests/test_test_router.py`, `tests/test_test_route_registration_bootstrap.py`, `tests/test_app_basic_combined.py`, and `tests/test_app_vip_comprehensive_97.py`.
Reason: Expands this PR to cover the current `test-main` route/effective-route fallout by replacing stale raw `FastAPI.routes` assumptions with `app.effective_routes` helpers. This is test-only and does not change production route registration, OpenAPI, dependencies, or proxy behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28322758721/job/83907568569 -> 51fecbb9f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28322758721/job/83907568573 -> 51fecbb9f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28322758721/job/83907568565 -> 51fecbb9f

Disposition: FIXED
Commit: 651ea0fc7
Evidence: `tests/test_legacy_export_aliases.py`, `tests/test_test_router.py`, and `tests/test_vip_api.py`.
Reason: Closes the next current-head `test-main (3.11, 60)` failure by moving the remaining raw route-table assertions to effective route helpers and making the test-router reload helper resilient when earlier tests remove `app.main` from `sys.modules`. This remains test-only and does not change runtime route registration.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28326828744/job/83918253209 -> 651ea0fc7

Disposition: FIXED
Commit: fa3437b08
Evidence: `docs/review/PR_2036_FIXED_MAPPING.md` and `tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths`.
Reason: Closes the current-head local-path leakage failure by replacing absolute local validation command paths with repo-relative commands.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28327495533/job/83919976404 -> fa3437b08

Disposition: FIXED
Commit: 58c5881e2
Evidence: `tests/test_legacy_runtime_env_canonicalization.py`.
Reason: Closes the current-head `test-main (3.11, 60)` failure by using effective route helpers for the staging test-router route assertion and making canonical bootstrap reload resilient to prior `sys.modules` cleanup. This remains test-only and does not change runtime route registration.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28327987035/job/83921248754 -> 58c5881e2

## Local Validation

Full local `make verify` was not run under the operator-approved machine-heavy
CI/tooling exception. The required local bundle for this PR is the focused proxy
health suite, supply-chain workflow guards, live proxy preflight, `make
validate-changed`, and `pre-commit run --all-files`, followed by current-head CI
parity after push.

Validated on the rebased mapping head:

- PASS: `python3 -m py_compile scripts/ci/check_private_python_proxy_health.py`
- PASS: `PYTHONPATH= python3 -I -S scripts/ci/check_private_python_proxy_health.py --help`
- PASS:
  `PULSEPLATE_PYTHON_INDEX_URL='https://packages.pulseplate.app/root/pulseplate/+simple/' python3 scripts/ci/check_private_python_proxy_health.py --requirements-file requirements.txt --requirements-file requirements-ci-lite.txt --requirements-file requirements-test.txt --project aiosqlite --project cryptography --project requests --project pytest-xdist --project hypothesis --project pgvector`
  - `aiosqlite==0.22.1`, `cryptography==48.0.1`,
    `requests==2.33.0`, `pytest-xdist==3.8.0`,
    `hypothesis==6.155.7`, and `pgvector==0.4.2` were found on
    non-empty project pages.
- PASS:
  `PULSEPLATE_PYTHON_INDEX_URL='https://packages.pulseplate.app/root/pulseplate/+simple/' python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
- PASS:
  `.venv/bin/python -m pytest -q tests/test_private_python_proxy_health.py tests/test_private_python_proxy_workflow_contract.py tests/test_python_supply_chain_controls.py`
  - Result after review fixes: `110 passed`; one existing Starlette/httpx2
    deprecation warning.
- PASS: `make validate-changed`
  - Selected:
    `tests/test_private_python_proxy_health.py`,
    `tests/test_private_python_proxy_workflow_contract.py`, and
    `tests/test_python_supply_chain_controls.py`.
- PASS: `pre-commit run --all-files`
- PASS:
  `npx --yes markdownlint-cli2 RUNBOOK_AGENT.md docs/DEPENDENCY_MANAGEMENT.md docs/security/PRIVATE_PYTHON_PROXY_HEALTH_GATE.md`
  - Result after current-head Docs Phase1 failure triage: `Summary: 0
    error(s)`.
- PASS:
  `.venv/bin/python -m pytest -q tests/test_env_guards.py tests/test_bmi_registration_router_coverage.py tests/test_legacy_weekly_plan_alias_api.py tests/test_restaurant_moderation_bootstrap.py tests/test_test_router.py tests/test_test_route_registration_bootstrap.py tests/test_app_basic_combined.py tests/test_app_vip_comprehensive_97.py`
  - Result after effective-route test expansion: `95 passed`; one existing
    Starlette/httpx2 deprecation warning.
- PASS:
  `.venv/bin/python -m pytest -q tests/test_private_python_proxy_health.py tests/test_private_python_proxy_workflow_contract.py tests/test_python_supply_chain_controls.py tests/test_env_guards.py tests/test_bmi_registration_router_coverage.py tests/test_legacy_weekly_plan_alias_api.py tests/test_restaurant_moderation_bootstrap.py tests/test_test_router.py tests/test_test_route_registration_bootstrap.py tests/test_app_basic_combined.py tests/test_app_vip_comprehensive_97.py`
  - Combined proxy + route guard suite: `205 passed`; one existing
    Starlette/httpx2 deprecation warning.
- PASS:
  `.venv/bin/python -m pytest -q tests/test_legacy_export_aliases.py::test_legacy_export_alias_routes_are_hidden_shim_owned_and_protected tests/test_test_router.py tests/test_vip_api.py::test_deprecated_weekly_plan_handles_dict_plan`
  - Fresh CI failure pack after commit `651ea0fc7`: `9 passed`; one existing
    Starlette/httpx2 deprecation warning.
- PASS:
  `.venv/bin/python -m pytest -q tests/test_legacy_export_aliases.py tests/test_test_router.py tests/test_vip_api.py`
  - Affected remaining route guard files: `39 passed`; one existing
    Starlette/httpx2 deprecation warning.
- PASS:
  `.venv/bin/python -m pytest -q tests/test_private_python_proxy_health.py tests/test_private_python_proxy_workflow_contract.py tests/test_python_supply_chain_controls.py tests/test_env_guards.py tests/test_bmi_registration_router_coverage.py tests/test_legacy_weekly_plan_alias_api.py tests/test_restaurant_moderation_bootstrap.py tests/test_test_router.py tests/test_test_route_registration_bootstrap.py tests/test_app_basic_combined.py tests/test_app_vip_comprehensive_97.py tests/test_legacy_export_aliases.py tests/test_vip_api.py`
  - Expanded proxy + route guard suite: passed; one existing Starlette/httpx2
    deprecation warning.
- PASS:
  `.venv/bin/ruff check tests/test_env_guards.py tests/test_bmi_registration_router_coverage.py tests/test_legacy_weekly_plan_alias_api.py tests/test_restaurant_moderation_bootstrap.py tests/test_test_router.py tests/test_test_route_registration_bootstrap.py tests/test_app_basic_combined.py tests/test_app_vip_comprehensive_97.py tests/test_private_python_proxy_health.py tests/test_private_python_proxy_workflow_contract.py tests/test_python_supply_chain_controls.py`
- PASS: `git diff --check`
- PASS:
  `VENV_PYTHON=.venv/bin/python make validate-changed`
  - Result after commit `651ea0fc7`: backend tests passed; one existing
    Starlette/httpx2 deprecation warning.
  - Note: `make validate-changed` did not select
    `tests/test_legacy_export_aliases.py` or `tests/test_vip_api.py`, so those
    files were covered by the focused pytest commands above.
- PASS:
  `.venv/bin/python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths`
  - Result after commit `fa3437b08`: passed; one existing Starlette/httpx2
    deprecation warning.
- PASS:
  `.venv/bin/python -m pytest -q tests/test_legacy_runtime_env_canonicalization.py tests/test_test_router.py`
  - Result after commit `58c5881e2`: `13 passed`; one existing Starlette/httpx2
    deprecation warning.
- PASS:
  `.venv/bin/ruff check tests/test_legacy_runtime_env_canonicalization.py tests/test_test_router.py`
- PASS:
  `VENV_PYTHON=.venv/bin/python make validate-changed`
  - Result after commit `58c5881e2`: backend tests passed; one existing
    Starlette/httpx2 deprecation warning.
  - Note: `make validate-changed` did not select
    `tests/test_legacy_runtime_env_canonicalization.py`, so that file was
    covered by the focused pytest command above.

## Security Notes

- No credentialed index URLs are allowed.
- Public PyPI, TestPyPI, and pythonhosted index URLs remain blocked for the
  canonical private proxy path.
- Authenticated protected-branch reads use read-only `.netrc` credentials, not
  inline Basic Auth URLs.
- Root devpi credentials are rejected.
- Emergency wheels remain a time-boxed mirror-lag exception only, not a fallback
  for a dead origin.

## Merge Readiness

- Current-head CI: pending after rebased push.
- CodeRabbit / Sourcery / Cubic actionables: pending after rebased push.
- Strict merge wrapper: pending.

Do not call this PR green, ready, or mergeable until all current-head checks,
review-thread disposition, and strict merge-readiness gates pass.
