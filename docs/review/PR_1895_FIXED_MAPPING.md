# PR #1895 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1895>

## Summary

This PR adds Private Pilot Activation Evidence v1 for the Experiment Runner
operator plane. It converts redacted manual live-smoke output into a typed local
activation evidence contract, imports that evidence into the operator
ledger/report layer, and projects label-only state through the existing
`/pulseplate-runner status` surface.

## Lane Start Provenance

- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/private-pilot-activation-evidence-v1`
- Packet: `artifacts/orchestration/task_packets/66dfccd2211f.json`
- Role dispatch command executed: `scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/66dfccd2211f.json --mode runtime --implementation-owner security-auditor --pretty`
- Pre-implementation role order executed: `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`

## Scope

- Typed exact-key redacted private-pilot activation evidence contract.
- Manual Slack Socket Mode smoke workflow evidence artifact upload.
- Local-only activation evidence import/reporting under
  `artifacts/orchestration/experiments/private_pilot_activation/`.
- Additive existing `/pulseplate-runner status` labels for activation state,
  last smoke, next operator action, dispatch outcome, evidence status, and
  display-only authority.
- Governed non-human identity policy, operator runbook, backlog, and focused
  guard tests.

## Out of Scope

- No new Slack command or public Slack expansion.
- No token minting, JWT/private-key handling, or repo-stored GitHub App
  credentials.
- No `repository_dispatch`, arbitrary workflow/ref, PR or review-thread
  mutation, merge authority, `contents:write`, or `workflows:write`.
- No semantic-cache runtime, GraphRAG, backend/API/OpenAPI, product runtime,
  frontend, or iOS changes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Notes: initial pass completed for currently visible review comments; no
  actionable review comments were present when this artifact was created.
- Final thread resolution and bot-actionable pass remain pending until
  post-open agents, Codex Security, `pulseplate-pr-review`, CodeRabbit, Cubic,
  Sourcery, and current-head CI settle.

## Fixed in Commit Mapping

- No actionable review comments

## Premortem Findings

- Activation JSON could become hidden runtime or merge authority.
  - Disposition: FIXED
  - Evidence: exact-key validation, false authority boundary labels, identity
    policy false booleans, and runbook language keep the artifact
    contract-only and display-only.
- Workflow artifact upload could leak raw workflow inputs, logs, tokens, Slack
  identifiers, branch refs, hypotheses, approval digests, local paths, oracle
  output, or patch text.
  - Disposition: FIXED
  - Evidence: workflow writes only the redacted JSON evidence shape, keeps
    `permissions: contents: read`, uses pinned artifact upload, and tests
    assert forbidden content is absent.
- Malformed local artifacts could poison operator reports.
  - Disposition: FIXED
  - Evidence: ingestion validates exact evidence keys and projects malformed
    evidence as `invalid_local_artifact` with fail-closed summary labels.
- Operator docs could imply manual smoke equals merge readiness.
  - Disposition: FIXED
  - Evidence: runbook and policy state manual smoke evidence is local
    operator evidence only, not review, merge, or runtime authority.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-01225ceda776.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution kind: `oracle_review`
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `promotion_ready=false`
- `coauthor_required=true`
- Co-author trailer is present on
  `839b90967a82d6cd3bca76003766f246f89655f4`.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path scripts/orchestration/experiment_private_pilot_activation.py --path scripts/orchestration/experiment_operator_ledger.py --path tests/test_experiment_operator_ledger.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python -m pytest -q tests/test_experiment_slack_socket_bridge.py tests/test_experiment_operator_ledger.py tests/test_experiment_runner_identity_policy.py`
- PASS: `python3 scripts/orchestration/check_experiment_runner_identity.py`
- PASS: `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: `python3 -m scripts.orchestration.experiment_slack_socket_bridge --activation-readiness-report --dispatch-mode dry-run`
- PASS: `python3 scripts/orchestration/experiment_operator_ledger.py --write-report-set`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hook, including changed-file mypy, pip-audit, backend tests,
  full-repo Bandit, and Docker build test.

## Machine-Heavy Verify Exception

Full local `make verify` is operator-deferred for this coordination/tooling lane
because it runs the machine-heavy project-wide suite. This PR uses focused
local gates plus canonical current-head GitHub CI parity before any
merge-readiness claim.

## Post-Open Review Gates

- [x] `qa-engineer-agent`
  - Disposition: FIXED
  - Commit: `1171d9314830102c4e20a73ffb6c5de9d38d1016`
  - Evidence: QA found the pushed head was missing the canonical
    `docs/review/PR_1895_FIXED_MAPPING.md` artifact and PR-body Phase2 mirror.
    The mapping artifact was committed, local
    `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1895`
    passed, `make validate-changed` passed, `pre-commit run --all-files`
    passed, and pre-push hooks passed. The PR-body mirror is refreshed from
    this artifact after push.
  - Disposition: FIXED
  - Commit: `c1f8a31ad6a17e3f7fde0d8c4da21990f8eaa155`
  - Evidence: QA found live-smoke validation could fail before redacted
    activation evidence was written or uploaded. The workflow now captures the
    live-smoke exit status without printing live command output, writes
    `smoke_failed_safely` evidence on nonzero smoke/readiness status, uploads
    the redacted artifact with `if: always()`, and then fails the job. The
    workflow contract test asserts the failure-safe status, output suppression,
    upload-on-failure, and continued absence of `continue-on-error`, `|| true`,
    raw Slack/GitHub identifiers, PR/review/merge mutation, and
    `repository_dispatch`.
- [ ] `bug-hunter`
- [ ] `security-auditor`
- [ ] Codex Security diff scan / finding discovery
- [ ] `pulseplate-pr-review`

## Merge Readiness

Not claimed.

Required before merge readiness:

- Complete post-open role-agent review and Codex Security / PR review passes.
- Fix or disposition every actionable human or bot finding.
- Refresh this artifact and the PR-body mirror after any fixes or dispositions.
- Wait for current-head CI and external bot state to settle.
- Run strict merge-readiness checks with no unresolved actionable comments.
