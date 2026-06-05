# PR #1885 - Fixed in Commit Mapping

Branch: `codex/experiment-runner-github-app-adapter`

Title: `feat(orchestration): add GitHub App dispatch seam`

## Goal

Prepare Experiment Runner operator dispatch for cross-repo private pilots through
a typed GitHub App adapter seam for externally minted installation-class
workflow dispatch and explicit least-privilege repo targeting.

## Scope

- Typed GitHub dispatch auth, target, and adapter config contracts.
- Runtime `EXPERIMENT_GITHUB_DISPATCH_REPO_ALLOWLIST` for exact `owner/repo`
  private-pilot targets.
- Cross-repo execute-mode gate requiring both exact repo allowlist and
  installation-class GitHub auth.
- Fixed `workflow_dispatch` contract only: `experiment-runner-dispatch.yml` on
  `main`, with typed `branch_ref`, `hypothesis_sha256`, `dry_run`, and
  `approval_ref` inputs.
- Governed non-human identity policy docs/json/checker updates and deterministic
  tests.

## Out of Scope

- No `repository_dispatch`.
- No arbitrary workflow file or ref selection.
- No GitHub App JWT generation, app private keys, or installation credential
  minting inside the repo.
- No PR creation/update, review-thread mutation, merge authority,
  `contents:write`, `workflows:write`, admin, sensitive-store, or broader Slack
  command authority.
- No product runtime, semantic-cache implementation, OpenAPI, web, or iOS
  changes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Branch Commits

- `7b0bfb28780a702bc1d8925c0e0a11cbca60650` - typed GitHub App dispatch seam,
  exact repo allowlist enforcement, least-privilege identity policy contract, and
  deterministic tests.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/6f0e5c034dbf.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`

## Experiment Runner Evidence

- Mode: `oracle_only_governance_reviewer`
- Artifact: `artifacts/orchestration/experiments/results/github_app_adapter_oracle_result.json`
- Result: `exp-246a3727f1c3` accepted.
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- 3/3 oracle commands passed:
  - `python -m pytest -q tests/test_experiment_slack_socket_bridge.py tests/test_experiment_runner_identity_policy.py`
  - `python3 scripts/orchestration/check_experiment_runner_identity.py --json`
  - `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- Commit trailer required and used:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path ...`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_experiment_slack_socket_bridge.py tests/test_experiment_runner_identity_policy.py`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_experiment_slack_socket_bridge.py tests/test_experiment_runner_identity_policy.py tests/test_experiment_operator_ledger.py`
- PASS: `python3 scripts/orchestration/check_experiment_runner_identity.py --json`
- PASS: `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: `pre-commit run --all-files`
- PASS: `make validate-changed` after commit; selected
  `tests/test_experiment_runner_identity_policy.py tests/test_experiment_slack_socket_bridge.py`
- PASS: commit/pre-push hooks including changed-file mypy, backend tests, Bandit,
  pip-audit, and docker build test.
- PARTIAL / operator-approved machine-heavy exception: full `make verify` was
  started and passed `verify-env`, `flake8`,
  `mypy --no-incremental --cache-dir=/dev/null app core`, and smoke tests
  (`tests/edges tests/test_remaining_modules.py`), then was stopped during the
  full pytest/diff-cover phase after operator guidance that this full suite is
  machine-heavy for narrow lanes.

## Pre-Open Premortem Disposition

Decision: proceed with changes already applied.

Findings:

- Cross-repo dispatch could bypass intended private-pilot targeting if repo
  validation stayed syntactic only.
  - Disposition: FIXED
  - Evidence: `scripts/orchestration/experiment_slack_bridge_dispatch.py`
    enforces exact allowlist plus installation-class auth for cross-repo execute;
    `tests/test_experiment_slack_socket_bridge.py` covers missing allowlist,
    nonmatching allowlist, malformed allowlist, PAT rejection, and `GH_TOKEN`
    precedence.
- Opaque GitHub auth values or private-pilot repo names could leak through repr,
  audit, or ledger output.
  - Disposition: FIXED
  - Evidence: `GitHubDispatchAuth.token` and `GitHubDispatchTarget.repo` use
    `repr=False`; tests assert no raw target repo name or `ghs_` prefix appears
    in governance output.
- Machine-readable identity policy could drift from docs.
  - Disposition: FIXED
  - Evidence: `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.json`,
    `scripts/orchestration/check_experiment_runner_identity.py`, and
    `tests/test_experiment_runner_identity_policy.py` now enforce selected-repo,
    fixed workflow/ref, Actions write, and forbidden authority booleans.
- `make validate-changed` can give a false local signal before a branch commit.
  - Disposition: NOT-A-BUG
  - Evidence: the command was rerun after commit and selected the expected
    branch-diff tests.

## Post-Open Review Passes

Completed:

- `qa-engineer-agent`
  - Disposition: FIXED
  - Commit: `f323421e2`
  - Evidence: `scripts/orchestration/experiment_slack_bridge_models.py` keeps
    same-repo execute compatible when `GITHUB_REPOSITORY` is absent;
    `tests/test_experiment_slack_socket_bridge.py` covers the regression, and
    Phase2 PR body/mapping validation passes.
- `bug-hunter`
  - Disposition: FIXED
  - Commit: `b3d774e9a`
  - Evidence: `scripts/orchestration/experiment_slack_bridge_config.py` uses the
    canonical PulsePlate repository only as the same-repo fallback when
    `GITHUB_REPOSITORY` is absent; explicit non-default targets remain
    cross-repo, and `tests/test_experiment_slack_socket_bridge.py` covers the
    bypass regression.
- `security-auditor`
  - Disposition: NOT-A-BUG
  - Evidence: no actionable security findings at head `7a43cc010`; reviewed
    token classification/redaction, cross-repo gate before dispatch, fixed
    workflow dispatch, and identity-policy authority denials. Focused security
    tests and `check_experiment_runner_identity.py --json` pass.
- Codex Security diff scan / finding discovery
  - Disposition: NOT-A-BUG
  - Evidence: `/tmp/codex-security-scans/BMI-App_2025_clean/7a43cc010_pr1885_github_app_adapter/report.md`
    reports no actionable security findings; `deep_review_input.csv` contains
    6 source-like diff rows and `work_ledger.jsonl` has 6 completion receipts.
- `pulseplate-pr-review`
  - Disposition: NOT-A-BUG
  - Evidence: advisory large-diff note was reviewed. The 12 changed files match
    the requested narrow lane (operator bridge config/contracts/tests/docs and
    canonical review artifact), no implementation scope was split across product
    runtime/web/iOS/OpenAPI, and `make validate-changed` plus focused tests pass.

## Merge Readiness

Not claimed. Pending current-head CI, bot review disposition, review-thread /
fixed-mapping gates, and strict merge-readiness checks.
