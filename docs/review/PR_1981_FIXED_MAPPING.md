# PR 1981 Fixed Mapping

## Summary

Replacement PR for raw Dependabot PRs #1972, #1973, and #1974. This lane refreshes Python testing / quality / dev-tool pins while preserving the full lock graph, removing the invalid Dependabot assignee config, and keeping #1975 / RAG-vector plus torch alerts #160-#162 out of scope.

Implementing commit:

- `e34a357f25d2aba717465c675595581e64301126` - `chore(deps): refresh python tooling pins`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open review state at artifact creation:

- CodeRabbit PR #1981 comment: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1981#issuecomment-4707519810`
  - Disposition: NOT-A-BUG
  - Evidence: `gh pr checks 1981` reported `CodeRabbit pass` at head `e34a357f25d2aba717465c675595581e64301126`.
  - Reason: The comment is an operational rate-limit notice and finishing-touch UI, not a code finding against this diff. If later CodeRabbit review comments appear, they must be mapped before merge readiness.

Pre-existing Dependabot comments superseded by this replacement PR:

- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1972#issuecomment-4700551979`
  - Disposition: FIXED
  - Commit: `e34a357f25d2aba717465c675595581e64301126`
  - Evidence: `.github/dependabot.yml:8` now goes directly from `open-pull-requests-limit` to `commit-message`; the invalid `assignees` block was removed.
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1973#issuecomment-4700554400`
  - Disposition: FIXED
  - Commit: `e34a357f25d2aba717465c675595581e64301126`
  - Evidence: `.github/dependabot.yml:8` now goes directly from `open-pull-requests-limit` to `commit-message`; the invalid `assignees` block was removed.
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1974#issuecomment-4700556503`
  - Disposition: FIXED
  - Commit: `e34a357f25d2aba717465c675595581e64301126`
  - Evidence: `.github/dependabot.yml:8` now goes directly from `open-pull-requests-limit` to `commit-message`; the invalid `assignees` block was removed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e34a357f25d2aba717465c675595581e64301126

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1972#issuecomment-4700551979 -> e34a357f25d2aba717465c675595581e64301126
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1973#issuecomment-4700554400 -> e34a357f25d2aba717465c675595581e64301126
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1974#issuecomment-4700556503 -> e34a357f25d2aba717465c675595581e64301126

## Dependency Delta Proof

- `requirements-dev.in:4` pins `pytest~=9.1.0`.
- `requirements-dev.in:11` pins `faker~=40.23.0`.
- `requirements-dev.in:19` sets `pip-audit>=2.10.1`.
- `requirements-dev.in:34` pins `ruff~=0.15.17`.
- `requirements-test.txt` contains `pytest==9.1.0` and `faker==40.23.0`.
- `requirements-ci-lite.txt` contains `pytest==9.1.0`.
- `requirements-dev.txt` and `requirements-lock.txt` contain only the intended direct-tooling pin deltas for `faker`, `pip-audit`, `pytest`, and `ruff`.
- `scripts/ci/emergency_python_wheels.json:64` through `scripts/ci/emergency_python_wheels.json:68` tracks the active `pytest 9.1.0` emergency artifact and SHA256.
- `tests/test_python_supply_chain_controls.py:491` asserts the test profile uses `pytest==9.1.0`.

Negative controls:

- `git diff --name-only | rg 'requirements-rag-vector|torch|transformers'` returned no files.
- `rg '^pip==' requirements*.txt scripts/ci/emergency_python_wheels.json` returned no repo-managed lock offenders.

## Premortem Closure

- PM-1981-001: Lockfiles update but emergency fallback manifest stays on `pytest 9.0.3`.
  - Disposition: FIXED
  - Commit: `e34a357f25d2aba717465c675595581e64301126`
  - Evidence: `scripts/ci/emergency_python_wheels.json:64`, `REQUIREMENTS.md`, `docs/roadmap/BACKLOG_LEDGER.md`, and focused tests.
- PM-1981-002: `pip-tools --allow-unsafe` reintroduces a forbidden `pip==...` pin.
  - Disposition: FIXED
  - Commit: `e34a357f25d2aba717465c675595581e64301126`
  - Evidence: `rg '^pip==' requirements*.txt scripts/ci/emergency_python_wheels.json` returned no repo-managed lock offenders after removing the generated `pip==26.1.2` unsafe stanzas.
- PM-1981-003: Replacement PR accidentally widens into #1975 / RAG-vector or torch remediation.
  - Disposition: NOT-A-BUG
  - Evidence: `git diff --name-only | rg 'requirements-rag-vector|torch|transformers'` returned no files; Dependabot alerts #160-#162 still report `first_patched_version=null`.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-700647086d5e.json`
- Result: accepted
- Runner mode: `oracle_only_governance_reviewer`
- Shared tree untouched: `true`
- Oracle commands:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url https://packages.pulseplate.app/root/pypi/+simple/`
- Co-author: Not applicable; the artifact is evidence-only and did not materially shape the committed code/test/doc decisions.

## Validation

Local narrow gates:

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
- PASS: `python3 verify_requirements.py`
- PASS: `. .venv/bin/activate && python -m pytest -q tests/test_dependency_security_guard.py tests/test_python_supply_chain_controls.py tests/test_install_locked_python_requirements.py tests/guards/test_security_devtooling_regression_guards.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during push: pre-push hooks, including `pip-audit`, backend pre-push pytest, full-repo Bandit, and docker build test.

Deferred heavy gate:

- `make verify` was not run. This PR uses the operator-approved machine-heavy exception for a dependency/tooling lane; current-head CI parity remains required before any merge-readiness claim.

## Merge Readiness

Not ready at artifact creation. Required before merge:

- Post-open role pass: `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Codex Security diff scan / finding discovery.
- `pulseplate-pr-review`.
- Current-head CI parity, including PR body / merge-readiness gates.
- Strict `check_merge_ready.py --require-auth`.
- No unresolved review threads or unmapped actionable bot comments.
- Mandatory wait-window after latest review activity.
