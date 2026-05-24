# PR #1823 Fixed Mapping

Status: IN PROGRESS

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1823

Replacement for: Dependabot PR #1807 (`diff-cover` 10.2.0 -> 10.2.1)

## Lane Start Provenance

- Pre-open packet: `artifacts/orchestration/task_packets/241888f27a4c.json`
- Post-open packet: `artifacts/orchestration/task_packets/710566d1fae2.json`
- Dispatch manifest command:
  `python3 scripts/orchestration/qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/710566d1fae2.json --pretty`
- Experiment Runner artifact:
  `artifacts/orchestration/experiments/results/pr1807-diff-cover-oracle-result.json`

## Scope

Human-owned replacement PR #1823 updates only the CI-lite/dev `diff-cover`
tooling surfaces and intentionally does not carry raw Dependabot #1807's
generated `pip==26.1.1` unsafe lock output.

Changed dependency surfaces:

- `constraints.txt:28` - `diff-cover>=10.2.1`
- `requirements-ci-lite.in:48` - `diff-cover~=10.2.1`
- `requirements-ci-lite.txt:70` - `diff-cover==10.2.1`
- `requirements-dev.in:14` - `diff-cover~=10.2.1`
- `requirements-dev.txt:60` - `diff-cover==10.2.1`

## Agent Execution Log

Pre-open packet roles:

- `agent-coordinator`: PASS_WITH_FOLLOWUP. Block raw #1807 because it
  reintroduced `pip==26.1.1`; use a human replacement.
- `architecture-specialist`: PASS. Scope is CI/dev dependency tooling only.
- `security-auditor`: PASS for supply-chain diff; require private-index proof
  and no unsafe pip pin.
- `qa-engineer-agent`: PASS_WITH_FOLLOWUP. Require CLI smoke, installer
  preflight, and bounded `.venv` gates.
- `bug-hunter`: PASS_WITH_FOLLOWUP. Check stale base, unsafe pin recurrence,
  profile widening, and false-green CI/body gates.
- `dev-operator`: PASS_WITH_FOLLOWUP. Rebase onto current `origin/main`, add
  mapping/body evidence, then rerun current-head checks.

Explicit post-open subagent executions:

- `agent-coordinator` subagent `019e5bc8-f306-7f53-898d-0efd246e9a49`:
  FOUND governance blockers `AC-1823-001` through `AC-1823-003`; mapping/body
  follow-up required.
- `architecture-specialist` subagent `019e5bcb-0a66-7d30-85ba-7604ddd082f7`:
  PASS for dependency/profile architecture; governance follow-up required.
- `dev-operator` subagent `019e5bcb-2fcc-7841-8278-345d8e3d1bd3`: PASS for
  private-index, installer, CLI smoke, no-pip, and scope; found stale-base and
  mapping/body blockers.
- `security-auditor` subagent `019e5bcb-5680-7322-8420-f84bd60e3e2d`: PASS for
  the diff-scoped supply-chain change; found missing mapping/body evidence and
  noted pre-existing Mako emergency fallback expiry.

Mandatory ordered post-open pass:

- `qa-engineer-agent` subagent `019e5bd2-3ba4-7582-8945-81152cde2a46`:
  PASS for dependency behavior; FIXED_REQUIRED for unpushed mapping/body state.
- `security-auditor` subagent `019e5bd5-06ce-7f72-8489-d49dc5096f4f`:
  PASS for the supply-chain diff; FIXED_REQUIRED for unpushed mapping/body
  state.
- `bug-hunter` subagent `019e5bd7-57c9-7923-b7ab-0c59cf72d6b6`: PASS for
  dependency behavior; FIXED_REQUIRED for unpushed mapping/body/current-head CI
  state.
- Ordered chain `qa-engineer-agent -> security-auditor -> bug-hunter`:
  COMPLETED.

## Skill Execution Log

- `pulseplate-orchestration-dispatch`: used for post-open packet manifest.
- `pulseplate-premortem-risk-review`: applied to actual diff, lock surfaces,
  private-index installer path, emergency wheel manifest, and CI risk.
- `pulseplate-pr-review`: applied to raw #1807 and replacement diff.
- `pulseplate-gates`: bounded `.venv` gates and installer checks executed.
- `codex-security:security-scan`: phases recorded below.
- `pulseplate-ledger`: no new ledger entry added; the pre-existing Mako
  emergency fallback expiry is already tracked by
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mako-private-index-sync`.

## Codex Security Scan

Target: PR #1823 diff against `origin/main`.

Phases:

1. Threat model: dependency supply-chain lane. Critical assets are private
   package proxy, deterministic source/lock surfaces, installer fallback
   policy, and emergency wheel manifest controls.
2. Finding discovery: raw #1807 reintroduced a forbidden `pip==26.1.1` unsafe
   pin. Replacement PR #1823 does not.
3. Validation: private-index exact wheel proof, installer preflight,
   `.venv` pip check, and `diff-cover` CLI smoke passed.
4. Attack-path analysis: no public-index fallback, emergency expansion,
   runtime drift, CI workflow edit, or guard weakening is introduced.
5. Final report: no surviving reportable security finding in the PR #1823
   diff. Pre-existing Mako fallback expiry is tracked as DEFERRED below.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/pr1807-diff-cover-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- `coauthor_required=true`
- Commit trailer required:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Premortem Risk Fix Matrix

| Risk ID | Failure mode | Fix | Regression test | Evidence command | Disposition |
| --- | --- | --- | --- | --- | --- |
| `PM-DEPS-001` | Source constraints and compiled locks drift. | Updated `.in` and `.txt` diff-cover surfaces together. | Source/lock audit. | `rg -n "^diff-cover" requirements*.txt requirements*.in constraints.txt` | FIXED |
| `PM-DEPS-002` | Private Python index cannot serve new pinned wheel. | Verified exact wheel through private proxy. | Private proxy download. | `pip download --isolated --index-url $PULSEPLATE_PYTHON_INDEX_URL --only-binary=:all: --no-deps diff-cover==10.2.1` | FIXED |
| `PM-DEPS-003` | Emergency wheel manifest becomes stale for newly pinned versions. | Audited manifest; `diff-cover` is not an emergency fallback. Pre-existing `mako==1.3.12` expiry is separately tracked. | Manifest audit. | `rg -n "diff-cover|diff_cover" scripts/ci/emergency_python_wheels.json`; `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mako-private-index-sync` | NOT-A-BUG for diff-cover; DEFERRED for pre-existing Mako expiry |
| `PM-DEPS-004` | PR silently widens profile surface. | Scope limited to CI-lite/dev diff-cover files. | Diff audit. | `git diff --name-only origin/main...HEAD` | FIXED |
| `PM-DEPS-005` | Local `.venv` and CI diverge. | Ran installer preflight and `.venv` checks. | pip check. | `.venv/bin/python -m pip check` | FIXED |
| `PM-DEPS-006` | Dependency update breaks CLI smoke. | Installed 10.2.1 and ran diff-cover/diff-quality help. | CLI smoke. | `.venv/bin/python -m diff_cover.diff_cover_tool --help`; `.venv/bin/python -m diff_cover.diff_quality_tool --help` | FIXED |
| `PM-DEPS-007` | Dependabot PR conflicts after another dependency PR lands. | Replaced stale raw branch, then rebased #1823 onto current `origin/main`. | PR metadata/diff audit. | `git rev-list --left-right --count HEAD...origin/main` | FIXED locally; push pending |
| `PM-DEPS-008` | Unsafe package pin appears unintentionally. | Did not carry `pip==26.1.1`; ran no-pip guard. | Pip-pin guard. | `pytest -q tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip tests/test_install_locked_python_requirements.py` | FIXED |
| `PM-DEPS-009` | Full `make verify` deferred without sufficient bounded evidence. | Ran profile checks, focused tests, validate-changed, pre-commit. | Bounded gates + CI required. | `make validate-changed`; `pre-commit run --all-files` | FIXED |

## Review Thread / Bot Dispositions

- Sourcery review guide:
  - Disposition: NOT-A-BUG.
  - Evidence: no inline review comment was returned by
    `gh api repos/Katsiarynakavaleuskaya/PulsePlate/pulls/1823/comments`;
    the issue comment is a reviewer guide, not an actionable change request.
    The guide describes `diff-cover>=10.2.1` in `constraints.txt`, which is
    already the implemented repo policy at `constraints.txt:28`.
- CodeRabbit:
  - Disposition: NOT-A-BUG.
  - Evidence: CodeRabbit issue comment says no actionable comments were
    generated.
- Codecov/Sentry:
  - Disposition: NOT-A-BUG.
  - Evidence: Codecov issue comment says all modified and coverable lines are
    covered.

## Deferred / Follow-Ups

- DEFERRED: pre-existing `mako==1.3.12` emergency fallback expiry in
  `scripts/ci/emergency_python_wheels.json:179`.
  - Backlog:
    `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mako-private-index-sync`
  - Reason: not introduced by #1823 and not needed for `diff-cover==10.2.1`,
    but it blocks any broad claim that the entire emergency manifest is fresh.

## Tests / Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open` -
  PASS, packet `artifacts/orchestration/task_packets/241888f27a4c.json`
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review` -
  PASS, packet `artifacts/orchestration/task_packets/710566d1fae2.json`
- `python3 scripts/orchestration/qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/710566d1fae2.json --pretty` -
  PASS
- `pip download --isolated --index-url $PULSEPLATE_PYTHON_INDEX_URL --only-binary=:all: --no-deps diff-cover==10.2.1` -
  PASS
- `python scripts/ci/install_locked_python_requirements.py --python-executable .venv/bin/python --requirements-file requirements-dev.txt --constraints-file constraints.txt --install-dev --preflight-only` -
  PASS
- `python scripts/ci/install_locked_python_requirements.py --python-executable .venv/bin/python --requirements-file requirements-ci-lite.txt --constraints-file constraints.txt --preflight-only` -
  PASS
- `.venv/bin/python -m diff_cover.diff_cover_tool --help` - PASS
- `.venv/bin/python -m diff_cover.diff_quality_tool --help` - PASS
- `.venv/bin/python -m pip check` - PASS
- `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip tests/test_install_locked_python_requirements.py` -
  PASS
- `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py -k "emergency or manifest or stale or expiry"` -
  PASS
- `make validate-changed` - PASS
- `pre-commit run --all-files` - PASS

## Merge Readiness

Not merge-ready yet.

Pending before readiness:

- Push rebase + mapping artifact.
- Update PR body to reference `docs/review/PR_1823_FIXED_MAPPING.md`.
- Rerun Phase2 body gate.
- Wait for current-head CI.
- Run review-thread disposition guard with auth.
- Run strict merge-readiness wrapper with auth.
- Complete final wait-window.

## Rollback

Revert PR #1823 to restore `diff-cover==10.2.0` in dev and CI-lite tooling
surfaces. No runtime migration, API change, CI workflow change, or emergency
fallback expansion is involved.
