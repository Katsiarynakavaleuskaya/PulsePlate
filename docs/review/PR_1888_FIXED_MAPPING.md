# PR #1888 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888>

## Summary

This PR adds Private Pilot Operator Readiness v1 for the Experiment Runner
GitHub App dispatch seam. It reports label-only GitHub dispatch readiness
through the existing Slack/Experiment Runner status and readiness surfaces,
adds a local operator-ledger evidence projection, and updates governed
identity/runbook evidence without adding live merge authority, PR/review
mutation, token minting, arbitrary workflow selection, semantic-cache runtime,
or broader Slack command power.

## Lane Start Provenance

- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/private-pilot-operator-readiness-v1`
- Packet: `artifacts/orchestration/task_packets/3971360f991c.json`
- Role dispatch command executed: `scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/3971360f991c.json --mode runtime --implementation-owner security-auditor --pretty`
- Pre-implementation role order executed: `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`

## Scope

- Label-only GitHub App dispatch readiness in activation JSON and
  `/pulseplate-runner status`.
- Target class, auth class, allowlist match, fixed workflow/ref, execute gate,
  live-approval state, and authority boundary labels.
- Operator observability report hook:
  `evidence_graph_admission_status=contract_only_not_runtime`.
- Governed non-human identity policy and operator runbook updates for the
  readiness/report evidence loop.

## Out of Scope

- No token minting, GitHub App JWT generation, private keys, or stored app
  credentials.
- No `repository_dispatch`.
- No arbitrary workflow file or ref selection.
- No PR creation/update, review-thread mutation, merge authority,
  `contents:write`, `workflows:write`, admin, or sensitive-store authority.
- No semantic-cache runtime, product runtime, OpenAPI, web, iOS, or public Slack
  expansion.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Notes: completed for currently visible review comments.
- [ ] Final thread resolution pass remains pending until PR-body mirror is
  updated and current-head bot state settles.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: post-open Codex and cubic false-green readiness findings are fixed by the commit mappings below; regression tests cover each false-green case without leaking private targets, token prefixes, Slack IDs, branch refs, or approval digests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#discussion_r3362845091 -> f7d5a3e5c1c9af74926749adf7e7dc9df003b098
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#discussion_r3362845098 -> f7d5a3e5c1c9af74926749adf7e7dc9df003b098
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#discussion_r3362845101 -> f7d5a3e5c1c9af74926749adf7e7dc9df003b098
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#discussion_r3363270522 -> 451b5c728
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#discussion_r3362876184 -> f7d5a3e5c1c9af74926749adf7e7dc9df003b098
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#discussion_r3362876187 -> f7d5a3e5c1c9af74926749adf7e7dc9df003b098
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#pullrequestreview-4436506435 -> f7d5a3e5c1c9af74926749adf7e7dc9df003b098
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#pullrequestreview-4436544874 -> f7d5a3e5c1c9af74926749adf7e7dc9df003b098

Disposition: NOT-A-BUG
Evidence: `GitHubDispatchAuth.is_installation_token`, `GitHubDispatchTarget.is_cross_repo`, and `GitHubDispatchTarget.is_allowlisted` are `@property` attributes in `scripts/orchestration/experiment_slack_bridge_models.py`, not methods. Using attribute access is correct.
Reason: Calling these properties as methods would be the runtime bug; the CodeRabbit suggestion is based on an incorrect model-shape assumption.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#discussion_r3362855738
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#pullrequestreview-4436520411

Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/experiment_slack_bridge_readiness.py` now checks `target.is_cross_repo and config.dispatch_mode != "execute"` before the cross-repo execute eligibility branch, and `tests/test_experiment_slack_socket_bridge.py::test_activation_readiness_report_labels_cross_repo_dry_run_without_dispatch_eligibility` proves allowlisted cross-repo dry-run reports `cross_repo_dry_run_available` instead of `eligible_for_private_pilot_dispatch`.
Reason: The Codex comment reviewed stale evidence from before `451b5c728`; current head already keeps dry-run readiness out of execute dispatch eligibility without changing authority.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#discussion_r3363308892

Disposition: NOT-A-BUG
Evidence: Sourcery and CodeRabbit reported service/rate-limit or optional finishing-touch status rather than a repository code defect. Repo-owned local gates and Codex Security discovery were run independently; no merge-readiness claim is made while external bot status is still pending or rate-limited.
Reason: These bot messages do not identify an actionable code defect in this PR diff.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#pullrequestreview-4436461188
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1888#issuecomment-4631789221

## Review Thread Dispositions

- `discussion_r3362845091`
  - Disposition: FIXED
  - Source: identified by Codex GitHub review.
  - Evidence: `scripts/orchestration/experiment_slack_bridge_readiness.py` now emits `blocked_by_missing_target` for execute-mode readiness without a dispatch target; `tests/test_experiment_slack_socket_bridge.py::test_activation_readiness_report_blocks_execute_without_dispatch_target` proves the report fails closed and remains redacted.
- `discussion_r3362845098`
  - Disposition: FIXED
  - Source: identified by Codex GitHub review.
  - Evidence: `scripts/orchestration/experiment_slack_bridge_readiness.py` now labels live approval as `present_unverified` and blocks eligibility as `blocked_by_live_approval_verification`; `tests/test_experiment_slack_socket_bridge.py::test_activation_readiness_report_blocks_unverified_live_approval_digest` covers the stale-digest case.
- `discussion_r3362845101`
  - Disposition: FIXED
  - Source: identified by Codex GitHub review.
  - Evidence: `scripts/orchestration/experiment_slack_bridge_readiness.py` now incorporates Slack allowlist label state before execute eligibility; `tests/test_experiment_slack_socket_bridge.py::test_activation_readiness_report_blocks_cross_repo_execute_without_slack_allowlists` proves cross-repo execute fails closed when Slack allowlists are absent.
- `discussion_r3363270522`
  - Disposition: FIXED
  - Source: identified by Codex GitHub review.
  - Evidence: `scripts/orchestration/experiment_slack_bridge_readiness.py` now reports `cross_repo_dry_run_available` for allowlisted cross-repo dry-run configuration instead of execute-dispatch eligibility; `tests/test_experiment_slack_socket_bridge.py::test_activation_readiness_report_labels_cross_repo_dry_run_without_dispatch_eligibility` covers the dry-run case without leaking target, token, Slack, branch, or digest values.
- `discussion_r3363308892`
  - Disposition: NOT-A-BUG
  - Source: identified by Codex GitHub review.
  - Evidence: current head already checks cross-repo dry-run before private-pilot execute eligibility and the dry-run regression test above proves the guarded label.
  - Reason: the review thread referenced stale evidence from before the dry-run fix commit and is not a surviving code defect.
- `discussion_r3362876184`
  - Disposition: FIXED
  - Source: identified by cubic.
  - Evidence: same stale-approval fix and regression test as `discussion_r3362845098`; cubic marked it addressed in `f7d5a3e5c`.
- `discussion_r3362876187`
  - Disposition: FIXED
  - Source: identified by cubic.
  - Evidence: same missing-target fix and regression test as `discussion_r3362845091`; cubic marked it addressed in `f7d5a3e5c`.
- `discussion_r3362855738`
  - Disposition: NOT-A-BUG
  - Evidence: `scripts/orchestration/experiment_slack_bridge_models.py` defines the referenced predicates with `@property`; invoking them with `()` would raise at runtime instead of improving correctness.

## Post-Open Role-Agent Findings

- `qa-engineer-agent`
  - Disposition: FIXED
  - Commit: `f7d5a3e5c`
  - Evidence: found execute/no-target, cross-repo/no-Slack-allowlist, and stale-live-approval false-green readiness cases. The fix commit adds fail-closed readiness states plus focused redaction regression coverage.
- `bug-hunter`
  - Disposition: FIXED
  - Commit: `f7d5a3e5c`
  - Evidence: confirmed the QA findings and identified the CodeRabbit predicate-method concern as a NOT-A-BUG candidate; focused regression tests now cover the three false-green states.
- `security-auditor`
  - Disposition: NOT-A-BUG
  - Evidence: retry completed as PulsePlate custom role `security-auditor` at `717cbd290ecd434ad0ec86abb9dc71e010bc049b` with no blocking security/governance findings. The role verified label-only readiness output, fixed workflow-dispatch boundaries, cross-repo execute gating, local/operator-plane ledger evidence, and `contract_only_not_runtime` Evidence Graph status.
- Codex Security diff scan / finding discovery
  - Disposition: NOT-A-BUG
  - Evidence: local Codex Security diff scan reviewed 3/3 changed source rows, wrote `work_ledger.jsonl`, validated `report.md`, rendered `report.html`, and found zero surviving reportable candidates after the readiness fix.
- `pulseplate-pr-review`
  - Disposition: NOT-A-BUG
  - Evidence: dry-run report produced one advisory large-diff planning note for a 9-file, 603-line coherent readiness slice. The operator explicitly chose this as one connected Private Pilot Operator Readiness v1 PR, and focused tests, `make validate-changed`, `pre-commit run --all-files`, and Codex Security discovery passed.
  - Reason: the advisory size note is review-planning evidence, not a code defect or merge-readiness claim.

## Premortem Findings

- Raw private target/token leakage through readiness/status/report output.
  - Disposition: FIXED
  - Evidence: label-only readiness fields and redaction assertions in `tests/test_experiment_slack_socket_bridge.py` and `tests/test_experiment_operator_ledger.py`.
- Readiness labels could be misread as PR, review-thread, or merge authority.
  - Disposition: FIXED
  - Evidence: `github_dispatch_authority=display_only`, `workflow_authority_changed=false`, identity policy assertions, and runbook authority language.
- Evidence Graph hook could imply semantic-cache or product runtime enablement.
  - Disposition: FIXED
  - Evidence: `evidence_graph_admission_status=contract_only_not_runtime` plus semantic-cache gate output.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-d20ac94a651a.json`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution: `oracle_review`
- `mutated_paths=[]`
- `promotion_ready=false`
- `coauthor_required=true`
- Co-author trailer is present on `a701c0c26`, the commit materially shaped by
  the oracle-only Experiment Runner review.

## Local Validation

- PASS: `python -m pytest -q tests/test_experiment_slack_socket_bridge.py tests/test_experiment_operator_ledger.py tests/test_experiment_runner_identity_policy.py`
- PASS: `python scripts/orchestration/check_preflight.py --mode analyze --path scripts/orchestration/experiment_slack_bridge_readiness.py --path scripts/orchestration/experiment_operator_ledger.py --path tests/test_experiment_slack_socket_bridge.py`
- PASS: `python scripts/orchestration/check_experiment_runner_identity.py`
- PASS: `python scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: `python -m pytest -q tests/test_experiment_slack_socket_bridge.py -k "activation_readiness_report_blocks_execute_without_dispatch_target or activation_readiness_report_blocks_cross_repo_execute_without_slack_allowlists or activation_readiness_report_blocks_unverified_live_approval_digest or activation_readiness_report_projects_cross_repo_private_pilot_without_values"`
- PASS: `python -m pytest -q tests/test_experiment_slack_socket_bridge.py -k "cross_repo_dry_run_without_dispatch_eligibility or activation_readiness_report_projects_cross_repo_private_pilot_without_values or activation_readiness_report_blocks_cross_repo_execute_without_slack_allowlists"`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files` after Black formatting pass
- PASS: commit hooks
- PASS: push hooks including changed-file mypy, pip-audit, backend pre-push tests, full Bandit, and docker build test
- PASS: Codex Security report format validation and HTML rendering
- PASS: mandatory post-open `security-auditor` role retry at `717cbd290ecd434ad0ec86abb9dc71e010bc049b`; no blocking security/governance findings
- PASS: `python scripts/orchestration/pr_review_context.py --pr 1888 --output /tmp/pulseplate_pr_1888_review_context.json`
- PASS: `python scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_1888_review_context.json --format markdown`
- PASS: `python scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_1888_review_context.json --format json`
- PASS: `python -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q` through the repo `.venv`

## Machine-Heavy Verify Exception

Full local `make verify` is operator-deferred for this coordination/tooling lane
because it runs the machine-heavy project-wide suite. This PR uses focused
local gates plus current-head GitHub CI as the heavy signal before any
merge-readiness claim.

## Merge Readiness

Not claimed.

Required before merge readiness:

- Wait for current-head CI and external bot state to settle.
- Run strict merge-readiness checks with current-head evidence and no unresolved
  actionable bot comments.
