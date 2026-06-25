# PR #2017 - Fixed in Commit Mapping SoT

## Scope

Wire the live devpi private Python package index into PulsePlate CI/local
bootstrap while keeping `PULSEPLATE_PYTHON_INDEX_URL` credential-free,
preserving the no-public-fallback supply-chain rule, and preventing root or
URL-embedded credentials from reaching CI, repository variables, tracked files,
or logs.

This PR does not move FastAPI, PyTorch, `transformers`, or
`sentence-transformers` between dependency profiles. It does not change
OpenAPI, backend runtime behavior, Docker API, generated clients, app routes,
frontend runtime contracts, iOS, DB migrations, billing, or entitlements.

## Implementation Commits

- `1dc92f2a0278caf3d72f4b28cc2307c92a895cdb` - add devpi URL/docs/tests,
  reject credentialed package-index URLs, add `.netrc` Basic Auth support for
  non-root devpi CI reads, and keep the backlog mirror-parity item open.
- `f6d212fc12efd1fd977baf10b994e2d529139796` - close PR-triggered workflow
  secret-boundary gaps, add scoped Safety install auth cleanup, add offline
  `.netrc` lifecycle tests, and refresh `.secrets.baseline` metadata.
- `11ee04235745b4083aa818ee68970c0ab1281bda` - guard empty devpi
  `.netrc` hostnames and add regression coverage for the Sourcery review
  finding.
- `f04d2baf9eacf44b4a5d8faae52933df2e630ab1` - sync PR #2017 with
  `origin/main` after PR #2014 merged, preserving the devpi hardening and
  dependency-lane lockfile updates together.
- `80db1bdf2f6927c02a0ce084ff14e192c804247f` - preserve non-root devpi
  `.netrc` auth for Docker BuildKit installs, redact URL credentials through
  the last userinfo separator, and remove bare `python` from the subprocess
  wrapper test input.
- `a4b0b1405a203119e2ee4f307acd2ca6e0461d97` - clean up Docker BuildKit
  devpi `.netrc` files after use, select emergency wheels using target
  interpreter tags, tighten exact-version proxy preflight matching, broaden the
  direct-pip workflow guard, and keep final merge-readiness checklist items
  unchecked until the final merge cycle.
- `823b10d53c63b77990401f1e1ab2383861ecd2ab` - keep the target wheel-tag probe
  payload validation explicit enough for local and pre-push mypy.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial PR open: no GitHub review threads existed at artifact creation.
- [x] Pre-open role findings fixed or dispositioned before PR open.
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2017`.
- [x] Post-open role pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [ ] Later bot/human review comments are fixed or dispositioned before merge
  readiness.
- [ ] Current-head CI is complete before merge readiness.
- [ ] Strict merge-readiness check runs after the final review/check cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2017#pullrequestreview-4562642386 -> 11ee04235745b4083aa818ee68970c0ab1281bda
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2017#discussion_r3467464705 -> 11ee04235745b4083aa818ee68970c0ab1281bda
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2017#pullrequestreview-4563199452 -> 80db1bdf2f6927c02a0ce084ff14e192c804247f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2017#discussion_r3467943722 -> 80db1bdf2f6927c02a0ce084ff14e192c804247f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2017#discussion_r3467943730 -> 80db1bdf2f6927c02a0ce084ff14e192c804247f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2017#discussion_r3467943759 -> 80db1bdf2f6927c02a0ce084ff14e192c804247f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2017#pullrequestreview-4567713068 -> a4b0b1405a203119e2ee4f307acd2ca6e0461d97
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2017#pullrequestreview-4567713857 -> a4b0b1405a203119e2ee4f307acd2ca6e0461d97
Disposition: FIXED
Commit: 11ee04235745b4083aa818ee68970c0ab1281bda
Evidence: scripts/ci/install_locked_python_requirements.py:952 and tests/test_install_locked_python_requirements.py:426

Disposition: FIXED
Commit: 80db1bdf2f6927c02a0ce084ff14e192c804247f
Evidence: .github/workflows/build.yml:54, Dockerfile:58, scripts/ci/install_locked_python_requirements.py:1019, tests/test_install_locked_python_requirements.py:1748, tests/test_python_supply_chain_controls.py:1325

Disposition: FIXED
Commit: a4b0b1405a203119e2ee4f307acd2ca6e0461d97
Evidence: .github/workflows/build.yml:120, .github/workflows/build.yml:538, scripts/ci/install_locked_python_requirements.py:612, scripts/ci/install_locked_python_requirements.py:1218, tests/test_install_locked_python_requirements.py:202, tests/test_install_locked_python_requirements.py:876, tests/test_python_supply_chain_controls.py:157, tests/test_python_supply_chain_controls.py:1371

## Additional Fixed Findings

Sourcery post-open review found that `_netrc_basic_auth_header` should guard
against falsy hostnames before looking up `.netrc` credentials.

Disposition: FIXED

Commit: `11ee04235745b4083aa818ee68970c0ab1281bda`

Evidence:

- `scripts/ci/install_locked_python_requirements.py` now accepts
  `str | None` hostnames and returns `None` without reading `.netrc` when the
  hostname is empty.
- `tests/test_install_locked_python_requirements.py` covers `None` and empty
  string hostnames without `.netrc` access.

CodeRabbit post-sync review found that protected Docker builds did not receive
the non-root devpi `.netrc` auth path, URL credential redaction stopped at the
first `@`, and a subprocess-wrapper test still used bare `python`.

Disposition: FIXED

Commit: `80db1bdf2f6927c02a0ce084ff14e192c804247f`

Evidence:

- `.github/workflows/build.yml` now prepares
  `$RUNNER_TEMP/pulseplate-docker-netrc` in both Docker build jobs, with
  secrets withheld from `pull_request`, root/whitespace credential rejection,
  and credential-free `PULSEPLATE_PYTHON_INDEX_URL` enforcement.
- Docker build steps pass that file as BuildKit `secret-files` using
  `pp_netrc=${{ runner.temp }}/pulseplate-docker-netrc`.
- `Dockerfile` consumes optional `pp_netrc` only inside install `RUN` layers,
  copies it to `/root/.netrc` with `0600`, and removes it with an `EXIT` trap.
- `scripts/ci/install_locked_python_requirements.py` redacts through the last
  userinfo separator before the host.
- `tests/test_install_locked_python_requirements.py` and
  `tests/test_python_supply_chain_controls.py` cover the regressions.

Coordinator pre-open review found that workflow-level `ci.yml` package-index
env still resolved `PULSEPLATE_PYTHON_INDEX_URL` from `secrets || vars`, which
could be inherited by PR-executed jobs.

Disposition: FIXED

Commit: `f6d212fc12efd1fd977baf10b994e2d529139796`

Evidence:

- `.github/workflows/ci.yml` now uses repository `vars` for top-level
  `PULSEPLATE_PYTHON_INDEX_URL` and `PULSEPLATE_PYTHON_TRUSTED_HOST`.
- The protected `test-main` resolver still permits `secrets || vars` only under
  `github.event_name != 'pull_request'` and still rejects credentialed URLs.
- `tests/test_ci_workflow_pr_size_governance_contract.py` guards the top-level
  `ci.yml` env against secret-backed package-index values.

Dev-operator pre-open review found that adjacent PR-triggered workflows also
used secret-backed package-index expressions.

Disposition: FIXED

Commit: `f6d212fc12efd1fd977baf10b994e2d529139796`

Evidence:

- `.github/workflows/frontend-ci.yml` now uses repository `vars` for
  package-index env and passes `DEVPI_CI_USER` / `DEVPI_CI_PASSWORD` only when
  `github.event_name != 'pull_request'`.
- `.github/workflows/build.yml` now uses repository `vars` for Docker build
  package-index env.
- `tests/test_python_supply_chain_controls.py` treats `ci.yml`,
  `frontend-ci.yml`, and `build.yml` as PR-triggered package-index workflows
  and rejects `secrets.*` in their PR-visible package-index env values.

QA pre-open review found that the direct `Install Safety` step ran after the
composite `python-setup` action had removed its temporary `.netrc`, leaving no
deterministic auth source for `requirements-security.txt` if devpi requires
Basic Auth.

Disposition: FIXED

Commit: `f6d212fc12efd1fd977baf10b994e2d529139796`

Evidence:

- `.github/workflows/ci.yml` now wraps `Install Safety` with
  `Configure private Python index authentication for Safety` and
  `Remove private Python index authentication for Safety`.
- The Safety auth wrapper rejects partial credentials, whitespace, root user,
  credentialed index URLs, and pre-existing `.netrc`.
- Cleanup is marker-gated and runs with `always()` before
  `Dependency audit with Safety`.
- `tests/test_python_supply_chain_controls.py` asserts the Safety auth/install
  /cleanup/audit ordering and cleanup script shape.

QA pre-open review found that `.netrc` lifecycle behavior in the composite
action was guarded mainly by string assertions rather than behavior.

Disposition: FIXED

Commit: `f6d212fc12efd1fd977baf10b994e2d529139796`

Evidence:

- `tests/test_python_supply_chain_controls.py` now executes the actual
  `python-setup` configure/cleanup shell blocks with temporary `HOME` and
  `RUNNER_TEMP`.
- Tests cover no-credential no-op, valid non-root `.netrc` creation and cleanup,
  partial credential rejection, whitespace rejection, root rejection,
  credentialed URL rejection, and pre-existing `.netrc` refusal.

Bug-hunter pre-open review found a P2 lifecycle edge: the cleanup marker was
touched after writing `.netrc`, so a pathological write failure after file
creation but before marker creation could leave `.netrc` until job teardown.

Disposition: FIXED

Commit: `f6d212fc12efd1fd977baf10b994e2d529139796`

Evidence:

- `.github/actions/python-setup/action.yml` now touches the cleanup marker
  before writing `$HOME/.netrc`.
- `.github/workflows/ci.yml` applies the same marker-before-write ordering for
  the Safety-specific `.netrc` wrapper.
- `tests/test_python_supply_chain_controls.py` asserts marker creation precedes
  `.netrc` writes in both wrappers.

Post-open `pulseplate-pr-review` reported one advisory `note` for large diff
review risk because the diff is above the dry-run heuristic threshold.

Disposition: NOT-A-BUG

Evidence:

- Scope is still one narrow CI/devpi rollout lane: package-index env contract,
  `.netrc` auth lifecycle, installer health probes, docs, backlog, and tests.
- Focused gates passed: `check_preflight`, `check_agent_consistency`, focused
  pytest for the changed surfaces, `make validate-changed`,
  `pre-commit run --all-files`, and pre-push hooks.
- Full local `make verify` remains explicitly deferred under the
  machine-heavy CI/tooling exception below; current-head CI is not green and no
  merge-ready claim is made.

Post-open role pass (`qa-engineer-agent -> bug-hunter -> security-auditor`)
found no PR-owned P0/P1 blocker after the Sourcery fix. All three passes kept
the current-head CI package-host timeout/root-pypi path as an external blocker
for PR #2017 rather than an in-diff BMI/application defect.

Codex Security diff scan completed for
`827eee384a4fd7fa9e80b993d503b3183a6312db..0be6ace526fb2908d7d3dcf6aae25aba63695d2c`.

Disposition: NOT-A-BUG

Evidence:

- Scan ID: `c10dfb9f-70b4-48f8-8712-6eee38af52cf`.
- Coverage: 14/14 changed files reviewed, 0 reportable findings.
- Finalized artifacts: `scan-manifest.json`, `coverage.json`,
  `findings.json`, `report.md`, and SARIF under the Codex Security scan
  directory.
- The scan recorded the default diff-rank helper limitation: the helper emitted
  zero rows for this workflow/docs/scripts/tests diff, so the parent scan used
  the explicit `git diff --name-status` changed-file list as the canonical
  manual worklist.

## Not Merge-Ready Yet

- Rotated non-root devpi CI read credentials must be available as secrets.
- Credentialed `scripts/ci/install_locked_python_requirements.py --preflight-only`
  must pass on current head.
- Docker build package-host proof must pass on current head because Docker
  build paths consume package-index secrets separately from `python-setup`.
- Current-head CI must pass after the final push.
- Post-open role pass, Codex Security diff scan / finding discovery,
  and `pulseplate-pr-review` are complete.
- Review-thread disposition, strict merge-readiness, current-head CI, and the
  mandatory wait-window remain required.

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/a4943868c687.json
Starter: manual coordinator flow (`check_preflight.py` ->
`task_bootstrap.py` -> `role_dispatch_bridge.py`)

## Governance Evidence

- Isolated worktree:
  `worktrees/devpi-package-index-rollout`.
- Branch:
  `codex/devpi-package-index-rollout`.
- Lane packet:
  `artifacts/orchestration/task_packets/a4943868c687.json` (local artifact).
- Merge-readiness sync packet:
  `artifacts/orchestration/task_packets/78cafe802402.json` (local artifact).
- Dispatch order completed before PR open:
  `agent-coordinator -> dev-operator -> security-auditor -> qa-engineer-agent -> bug-hunter`.
- Post-#2014 sync completed:
  PR #2014 merged to `main` as
  `2201390000120b54e987fec937511a8ad7b6a4ba`, and this branch merged
  `origin/main` as `f04d2baf9eacf44b4a5d8faae52933df2e630ab1`.
- Premortem:
  `artifacts/orchestration/premortem/devpi-package-index-rollout-premortem.md`
  (local artifact), decision `proceed with changes`.
- Experiment Runner oracle-only evidence:
  `artifacts/orchestration/experiments/results/exp-dbfa4b2cc9e1.json`
  (local artifact), status `accepted`, runner mode
  `oracle_only_governance_reviewer`, shared tree untouched, failure class
  `null`, mutated paths `[]`, promotion ready `false`.
- Experiment Runner attribution:
  commit `f6d212fc12efd1fd977baf10b994e2d529139796` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because
  accepted oracle evidence shaped PR opening, validation, and governance
  mapping decisions.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS:
  `python3 scripts/orchestration/task_bootstrap.py --goal "Wire live devpi private Python index into PulsePlate CI/local bootstrap" --task-class infra --path docs/DEPENDENCY_MANAGEMENT.md --path RUNBOOK_AGENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path scripts/ci/install_locked_python_requirements.py --path tests/test_install_locked_python_requirements.py --path tests/test_python_supply_chain_controls.py --path tests/test_ci_workflow_pr_size_governance_contract.py --requested-agent dev-operator --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase pre_open`
- PASS:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/a4943868c687.json --pretty`
- PASS:
  `python3 scripts/orchestration/check_preflight.py --path .github/actions/python-setup/action.yml --path .github/workflows/ci.yml --path .github/workflows/frontend-ci.yml --path .github/workflows/build.yml --path docs/DEPENDENCY_MANAGEMENT.md --path RUNBOOK_AGENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path scripts/ci/install_locked_python_requirements.py --path tests/test_install_locked_python_requirements.py --path tests/test_python_supply_chain_controls.py --path tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS:
  workflow/action YAML parse for `.github/workflows/ci.yml`,
  `.github/workflows/frontend-ci.yml`, `.github/workflows/build.yml`, and
  `.github/actions/python-setup/action.yml`.
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS:
  `python3 scripts/orchestration/check_preflight.py --path .github/workflows/build.yml --path Dockerfile --path scripts/ci/install_locked_python_requirements.py --path tests/test_install_locked_python_requirements.py --path tests/test_python_supply_chain_controls.py --path tests/test_docker_workflow_build_path_contract.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" make validate-changed`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" pre-commit run --all-files`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: pre-push hooks during
  `git push -u origin codex/devpi-package-index-rollout`, including `mypy`,
  `pip-audit`, backend pytest, full-repo Bandit, and Docker build test.
- PASS: `git diff --cached --check origin/main`
- PASS: static credential scan for exposed devpi root password,
  credentialed `packages.pulseplate.app` URLs, and public PyPI extra-index
  fallback returned no matches.
- PASS: Codex Security diff scan `c10dfb9f-70b4-48f8-8712-6eee38af52cf`
  finalized with 14/14 coverage rows and 0 findings.
- PASS: `pulseplate-pr-review` dry-run report; its only advisory note was
  dispositioned as NOT-A-BUG above.

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. This is a CI/tooling/security lane where
the operator direction is to use focused gates, `make validate-changed`,
pre-commit, pre-push hooks, current-head CI, and strict merge-readiness after
PR #2014/main sync. This deferral does not permit merge-ready claims while
current-head CI, credentialed proof, Docker package-host proof, review
disposition, or strict merge-readiness are pending.
