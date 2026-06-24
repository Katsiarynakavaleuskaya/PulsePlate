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

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial PR open: no GitHub review threads existed at artifact creation.
- [x] Pre-open role findings fixed or dispositioned before PR open.
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2017`.
- [ ] Post-open role pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] Later bot/human review comments are fixed or dispositioned before merge
  readiness.
- [ ] Current-head CI is complete before merge readiness.
- [ ] Strict merge-readiness check runs after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Additional Fixed Findings

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

## Not Merge-Ready Yet

- PR #2014 dependency lane must merge to `main`.
- This branch must sync/rebase after #2014 reaches `main`.
- Rotated non-root devpi CI read credentials must be available as secrets.
- Credentialed `scripts/ci/install_locked_python_requirements.py --preflight-only`
  must pass on current head.
- Docker build package-host proof must pass on current head because Docker
  build paths consume package-index secrets separately from `python-setup`.
- Current-head CI must pass after sync.
- Post-open role pass, Codex Security diff scan / finding discovery,
  `pulseplate-pr-review`, review-thread disposition, strict merge-readiness,
  and mandatory wait-window remain required.

## Governance Evidence

- Isolated worktree:
  `worktrees/devpi-package-index-rollout`.
- Branch:
  `codex/devpi-package-index-rollout`.
- Lane packet:
  `artifacts/orchestration/task_packets/a4943868c687.json` (local artifact).
- Dispatch order completed before PR open:
  `agent-coordinator -> dev-operator -> security-auditor -> qa-engineer-agent -> bug-hunter`.
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
- PASS: pre-push hooks during
  `git push -u origin codex/devpi-package-index-rollout`, including `mypy`,
  `pip-audit`, backend pytest, full-repo Bandit, and Docker build test.
- PASS: `git diff --cached --check origin/main`
- PASS: static credential scan for exposed devpi root password,
  credentialed `packages.pulseplate.app` URLs, and public PyPI extra-index
  fallback returned no matches.

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. This is a CI/tooling/security lane where
the operator direction is to use focused gates, `make validate-changed`,
pre-commit, pre-push hooks, current-head CI, and strict merge-readiness after
PR #2014/main sync. This deferral does not permit merge-ready claims while
current-head CI, credentialed proof, Docker package-host proof, review
disposition, or strict merge-readiness are pending.
