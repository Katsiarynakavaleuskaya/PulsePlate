# PR 1981 Fixed Mapping

## Summary

Replacement PR for raw Dependabot PRs #1972, #1973, and #1974. This lane refreshes Python testing / quality / dev-tool pins while preserving the full lock graph, removing the invalid Dependabot assignee config, and keeping #1975 / RAG-vector plus torch alerts #160-#162 out of scope.

Operator approval: approved
Privileged scope exception: approved for dependency tooling lane generated baseline and mapping artifact.

Rationale: the 16-file count includes mandatory governance and generated security artifacts: `docs/review/PR_1981_FIXED_MAPPING.md` for Phase2 mapping and `.secrets.baseline` for detect-secrets line-number drift after removing the retired pytest emergency wheel artifact.

Implementing commit:

- `e34a357f25d2aba717465c675595581e64301126` - `chore(deps): refresh python tooling pins`

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/2cb4f886db38.json`
- Starter: `python3 scripts/orchestration/task_bootstrap.py --goal "Refresh Python testing/quality/dev-tool dependency pins and fix Dependabot assignee warning" --task-class "security" --path requirements-dev.in --path requirements-test.in --path requirements-ci-lite.in --path constraints.txt --path .github/dependabot.yml --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent dev-operator --pr-phase pre_open --native-bridge-transport codex-native-subagents`
- Role order: `agent-coordinator -> security-auditor -> qa-engineer-agent -> dev-operator -> architecture-specialist`

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

Supersession closeout:

- PR #1972 closed as superseded by #1981; branch `dependabot/pip/testing-912befbf98` deleted.
- PR #1973 closed as superseded by #1981; branch `dependabot/pip/quality-65aa614161` deleted.
- PR #1974 closed as superseded by #1981; branch `dependabot/pip/dev-tools-35ffa26218` deleted.

Post-open Codex review:

- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1981#discussion_r3413175721`
  - Disposition: FIXED
  - Commit: `f5482ba1999ab6d1452884b7644be13fe751bea6`
  - Evidence: `scripts/ci/emergency_python_wheels.json` no longer carries the immediately expiring pytest fallback; approved proxy preflight and focused supply-chain tests passed after the removal.
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1981#discussion_r3413397670`
  - Disposition: NOT-A-BUG
  - Evidence: `git rev-parse HEAD origin/codex/python-tooling-deps-1972-1974` returned `8ed1b89ed7ee20900b9cfa1ed068e845ca39ebe5` for both local and remote head; `git merge-base --is-ancestor e34a357f25d2aba717465c675595581e64301126 8ed1b89ed7ee20900b9cfa1ed068e845ca39ebe5` and `git merge-base --is-ancestor f5482ba1999ab6d1452884b7644be13fe751bea6 8ed1b89ed7ee20900b9cfa1ed068e845ca39ebe5` both exited 0.
  - Reason: The PR branch preserves the original commit stack; the referenced proof SHAs are reachable ancestors of the actual PR head.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e34a357f25d2aba717465c675595581e64301126
Evidence: `.github/dependabot.yml:8` removes the invalid Dependabot `assignees` block while the replacement PR carries the intended dependency deltas from #1972, #1973, and #1974.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1972#issuecomment-4700551979 -> e34a357f25d2aba717465c675595581e64301126
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1973#issuecomment-4700554400 -> e34a357f25d2aba717465c675595581e64301126
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1974#issuecomment-4700556503 -> e34a357f25d2aba717465c675595581e64301126

Disposition: FIXED
Commit: f5482ba1999ab6d1452884b7644be13fe751bea6
Evidence: `scripts/ci/emergency_python_wheels.json` no longer carries the immediately expiring pytest fallback; approved proxy preflight and focused supply-chain tests passed after the removal.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1981#discussion_r3413175721 -> f5482ba1999ab6d1452884b7644be13fe751bea6

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor` confirms both mapped proof commits are ancestors of current PR head `8ed1b89ed7ee20900b9cfa1ed068e845ca39ebe5`.
Reason: The review comment describes a squashed synthetic head, but the active PR branch is not squashed and the strict local disposition guard can resolve the mapped commits.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1981#discussion_r3413397670

## Dependency Delta Proof

- `requirements-dev.in:4` pins `pytest~=9.1.0`.
- `requirements-dev.in:11` pins `faker~=40.23.0`.
- `requirements-dev.in:19` sets `pip-audit>=2.10.1`.
- `requirements-dev.in:34` pins `ruff~=0.15.17`.
- `requirements-test.txt` contains `pytest==9.1.0` and `faker==40.23.0`.
- `requirements-ci-lite.txt` contains `pytest==9.1.0`.
- `requirements-dev.txt` and `requirements-lock.txt` contain only the intended direct-tooling pin deltas for `faker`, `pip-audit`, `pytest`, and `ruff`.
- `scripts/ci/emergency_python_wheels.json` no longer carries a pytest emergency artifact because the approved private proxy serves `pytest==9.1.0` directly.
- `tests/test_python_supply_chain_controls.py:491` asserts the test profile uses `pytest==9.1.0`.

Negative controls:

- `git diff --name-only | rg 'requirements-rag-vector|torch|transformers'` returned no files.
- `rg '^pip==' requirements*.txt scripts/ci/emergency_python_wheels.json` returned no repo-managed lock offenders.

## Premortem Closure

- PM-1981-001: Lockfiles update but emergency fallback manifest stays on `pytest 9.0.3` or carries an immediately expiring replacement.
  - Disposition: FIXED
  - Commit: `f5482ba1999ab6d1452884b7644be13fe751bea6`
  - Evidence: `scripts/ci/emergency_python_wheels.json` removes the pytest fallback after approved proxy validation for `pytest==9.1.0`; `REQUIREMENTS.md`, `docs/roadmap/BACKLOG_LEDGER.md`, and focused tests stay aligned.
- PM-1981-002: `pip-tools --allow-unsafe` reintroduces a forbidden `pip==...` pin.
  - Disposition: FIXED
  - Commit: `e34a357f25d2aba717465c675595581e64301126`
  - Evidence: `rg '^pip==' requirements*.txt scripts/ci/emergency_python_wheels.json` returned no repo-managed lock offenders after removing the generated `pip==26.1.2` unsafe stanzas.
- PM-1981-003: Replacement PR accidentally widens into #1975 / RAG-vector or torch remediation.
  - Disposition: NOT-A-BUG
  - Evidence: `git diff --name-only | rg 'requirements-rag-vector|torch|transformers'` returned no files; Dependabot alerts #160-#162 still report `first_patched_version=null`.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-3f84655ac268.json`
- Result: accepted
- Runner mode: `oracle_only_governance_reviewer`
- Shared tree untouched: `true`
- Oracle commands:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url https://packages.pulseplate.app/root/pypi/+simple/`
- Co-author: Not applicable; the artifact is evidence-only and did not materially shape the committed code/test/doc decisions.

## Post-Open Review Closure

- PASS: `qa-engineer-agent` found the pytest fallback expiry and Phase2/parser risks; the fallback was removed and the mapping artifact repaired.
- PASS: `bug-hunter` found stale mapping evidence for PM-1981-001; the evidence was refreshed to commit `f5482ba1999ab6d1452884b7644be13fe751bea6`.
- PASS: `security-auditor` found no supply-chain/security blockers after the parser-safe mapping repair; remaining readiness risk is current-head CI / bot-governance only.
- PASS: Codex Security diff scan / finding discovery at `/tmp/codex-security-scans/BMI-App_2025_clean/pr1981_ef3afc6ef2e6_20260615T120425Z/report.md`; 16/16 worklist receipts completed and candidate ledger is empty.
- PASS: `pulseplate-pr-review` dry-run report at `/tmp/pulseplate_pr1981_review_report.md` produced no deterministic findings; `tests/test_pr_review_report.py` and `tests/test_pr_review_context.py` passed.

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
- PASS: `GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1981 --require-auth`
- PASS: `. .venv/bin/activate && python -m pytest -q tests/test_pr_review_report.py tests/test_pr_review_context.py`

Deferred heavy gate:

- `make verify` was not run. This PR uses the operator-approved machine-heavy exception for a dependency/tooling lane; current-head CI parity remains required before any merge-readiness claim.

## Merge Readiness

Not ready at latest artifact update. Required before merge:

- Current-head CI parity on the latest pushed commit, including PR body / merge-readiness gates.
- Strict `check_merge_ready.py --require-auth`.
- No unresolved review threads or unmapped actionable bot comments; CodeRabbit's rate-limit notice is mapped as NOT-A-BUG unless new actionable comments appear.
- Mandatory wait-window after latest review activity.
