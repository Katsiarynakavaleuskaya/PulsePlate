# PR #1948 Fixed in Commit Mapping

PR: `#1948` (https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1948)

Lane: `codex/propose-fix-for-github_token-exposure`

## Scope Boundary

PR #1948 closes one narrow CI security boundary: on `pull_request` runs, the
Docker telemetry baseline is copied from the checked-in production baseline
instead of invoking checked-out PR code with `GH_TOKEN` / `GITHUB_TOKEN`.
Trusted non-PR runs continue to use the token-backed remote baseline resolver.

Scope note: this PR does not claim broad workflow token isolation, does not
change `actions/checkout` credential persistence, does not change Docker
BuildKit secret-env handling for package index secrets, and does not change
backend, client, OpenAPI, database, app runtime, or release behavior.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/pr1948_post_open_packet.json`
- Packet id: `4d21ca87ac9c`
- PR phase: `post_open_review`
- Task class: `Security`
- Base reviewed: `b20f807a5c61cb166f909d9aacbe86b3044ee31e`
- Implementation head reviewed before closeout commit:
  `099a067bc8d25d4be7a403c049a9be9fbe65cac1`
- Startup evidence: `python3 scripts/orchestration/check_preflight.py` -> PASS.
- Startup evidence: `python3 scripts/orchestration/check_agent_consistency.py` -> PASS.
- Role dispatch evidence:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/pr1948_post_open_packet.json --pretty`
  -> PASS; declared order was `agent-coordinator -> dev-operator ->
  qa-engineer-agent -> bug-hunter -> security-auditor ->
  architecture-specialist`.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/pr1948-token-exposure-oracle-result.json`
- Packet: `artifacts/orchestration/experiments/pr1948-token-exposure-oracle-packet.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Contribution: `fixed_mapping_review`
- Co-author required: `true`
- Evidence: 2/2 oracle commands passed:
  `python3 scripts/orchestration/check_agent_consistency.py` and
  `python3 -m pytest -q tests/test_docker_workflow_build_path_contract.py`.
- Boundary: `mutated_paths=[]`, `source_diff_paths=[]`, and
  `shared_tree_untouched=true`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## External Bot And Review Dispositions

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1948#issuecomment-4683580025
Disposition: NOT-A-BUG
Evidence: Codex usage-limit notice contains no code-actionable finding.
Reason: External reviewer availability notice only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1948#pullrequestreview-4479343049
Disposition: NOT-A-BUG
Evidence: Sourcery weekly diff-character rate-limit notice contains no code-actionable finding.
Reason: External reviewer availability notice only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1948#issuecomment-4683580468
Disposition: NOT-A-BUG
Evidence: CodeRabbit review-rate/usage-credit notice contains no code-actionable finding.
Reason: External reviewer availability notice only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1948#pullrequestreview-4479377780
Disposition: NOT-A-BUG
Evidence: Cubic review for head `099a067bc8d25d4be7a403c049a9be9fbe65cac1`
reported "No issues found" across the two changed files.
Reason: External reviewer completed without code-actionable findings.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1948#issuecomment-4683763227
Disposition: NOT-A-BUG
Evidence: Codecov reported all modified and coverable lines are covered by tests.
Reason: Coverage status notice, not a code-actionable review finding.

## Role-Agent Findings

| Role | Result | Evidence |
| --- | --- | --- |
| `agent-coordinator` | No implementation blocker; governance artifact/body was the blocker. | Scope locked to `.github/workflows/build.yml` and `tests/test_docker_workflow_build_path_contract.py`; review threads count was zero; current head was `099a067bc8d25d4be7a403c049a9be9fbe65cac1`. |
| `dev-operator` | Proceed with governance artifact, PR-body mirror, and narrow gate path. | Confirmed current CI failures were `PR Body Phase2 gates` and `Merge readiness gate` due to missing `docs/review/PR_1948_FIXED_MAPPING.md`; no replacement PR required. |
| `qa-engineer-agent` | No QA code blocker for the narrow regression contract. | `.github/workflows/build.yml:80`, `.github/workflows/build.yml:86`, and `tests/test_docker_workflow_build_path_contract.py:81` lock the PR fallback/non-PR resolver split. |
| `bug-hunter` | No code-blocking bug found; avoid broad token-isolation claims. | `scripts/ci/fetch_docker_image_baseline.py:41` requires `GH_TOKEN` / `GITHUB_TOKEN`; `.github/workflows/build.yml:80` avoids that script on PR runs; `.github/workflows/build.yml:29` checkout credentials remain out of scope. |
| `security-auditor` | No additional security fix required for the narrow baseline-fetch exposure. | `.github/workflows/build.yml:88` scopes token env to the non-PR resolver; `tests/test_docker_workflow_build_path_contract.py:101` asserts PR fallback has no token env. |
| `architecture-specialist` | No architecture blocker. | Docker build/validation ownership remains in `.github/workflows/build.yml`; no `app/`, `core/`, web, iOS, OpenAPI, DB, or route surface changed. |

## Premortem Evidence

- Skill: `pulseplate-premortem-risk-review`
- Mode: `pr-premortem`
- Artifact: `artifacts/orchestration/premortem/pr-1948-token-exposure-premortem.md`
- Decision: `proceed with changes`.
- Closed risks:
  - Missing fixed-mapping artifact -> fixed by this closeout artifact.
  - Stale PR body commit evidence -> fixed by PR body mirror update after push.
  - Overbroad security wording -> closed by narrow scope note in this artifact
    and PR body.
  - Full local `make verify` deferral ambiguity -> closed by the explicit
    operator-approved deferral below.

## Codex Security Diff Scan

- Scan status: PASS, no reportable findings.
- Base: `b20f807a5c61cb166f909d9aacbe86b3044ee31e`
- Head: `099a067bc8d25d4be7a403c049a9be9fbe65cac1`
- Reviewed surfaces:
  - `.github/workflows/build.yml`
  - `tests/test_docker_workflow_build_path_contract.py`
- Evidence: the work ledger recorded completed/no-findings receipts for both PR
  files. The workflow receipt cites `.github/workflows/build.yml:80-84` and
  `.github/workflows/build.yml:86-98`; the test receipt cites
  `tests/test_docker_workflow_build_path_contract.py:81-113`.
- Limitation: the Codex Security worklist helper excludes `.github/` and
  `tests/` by default, so the two PR files were manually added to the scan
  input to preserve exact PR diff coverage.

## PulsePlate PR Review Evidence

- Context artifact: `/tmp/pulseplate_pr_review_1948_context.json`
- Markdown report: `/tmp/pulseplate_pr_review_1948.md`
- JSON report: `/tmp/pulseplate_pr_review_1948.report.json`
- Result: advisory dry-run report found two governance notes before this
  closeout: missing fixed-mapping artifact and warning-bearing context. This
  artifact resolves that blocker.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` -> PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS.
- `.venv/bin/python -m pytest -q tests/test_docker_workflow_build_path_contract.py`
  via the repo/shared Python resolver -> PASS (`...... [100%]`).
- `python3 scripts/orchestration/experiment_runner.py --packet artifacts/orchestration/experiments/pr1948-token-exposure-oracle-packet.json --output pr1948-token-exposure-oracle-result.json --contribution-kind fixed_mapping_review --coauthor-required --coauthor-reason "Experiment Runner oracle-only evidence shaped PR 1948 fixed mapping, validation evidence, and commit decision."`
  -> PASS.
- `make validate-changed` -> PASS; selected
  `tests/test_docker_workflow_build_path_contract.py` and reported `6 passed`.
- `pre-commit run --all-files` -> PASS on rerun; hooks included
  `check-github-workflows`, `ruff`, changed-file Bandit, frontend tests,
  changed-file backend tests, and iOS syntax check.
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1948 --body "$(gh pr view 1948 --repo Katsiarynakavaleuskaya/PulsePlate --json body -q .body)"`
  -> pending rerun after PR body mirror update.
- `GITHUB_TOKEN="$(gh auth token)" GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_merge_ready.py --pr-number 1948 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`
  -> pending rerun after push/current-head CI.

## Local Full Verify Deferral

- Full local `make verify`: deferred by operator approval for this machine-heavy
  PR because the full suite is too large for this lane.
- Replacement local gate path: preflight, agent consistency, focused workflow
  contract test, `make validate-changed`, `pre-commit run --all-files`, Phase2
  PR body gate, and strict merge-readiness wrapper with auth.
- Heavy parity signal: current-head GitHub CI must provide lint, diff coverage,
  workflow/security checks, PR Body Phase2 gates, Merge readiness gate, and the
  Docker/build surface checks attached to the changed workflow.
- This deferral does not permit ignored failures, weakened coverage,
  `continue-on-error`, unresolved review threads, or merge-readiness claims
  while narrow gates or current-head CI are pending.

## Merge Readiness

- [ ] PR body mirror updated with this artifact and current pushed head.
- [x] `make validate-changed` passed after this artifact was added.
- [x] `pre-commit run --all-files` passed before push.
- [ ] Phase2 PR body gate passed against the live PR body.
- [ ] Strict merge-readiness wrapper passed with auth.
- [ ] Current-head CI is terminal with required checks passing.
- [ ] No unresolved review threads or actionable bot comments remain.
- [ ] Mandatory wait-window completed after latest review/bot activity.
