# PR #2135 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2135

Branch: `codex/fix-apple-runner-canary-mismatch-20260714`

## Summary

Make strict Apple Container host-control selection deterministic and preserve
the exact material Experiment Runner attribution tuple across the host/guest
dispatcher boundary. Keep zero-network isolation, backend selection, retry
policy, product runtime, and public contracts unchanged.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/a8844263c77f.json`
  (local-only, gitignored).
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> cursor-specialist-agent`.
- The actual-diff premortem closed all forecast failure scenarios before PR
  open.
- Rebase to current `origin/main` preserved pre-review patch-id
  `51dbab38c84d9684fdbe244ab22c59f929732d53`; its material-diff SHA-256 was
  `26018c59265205b564780f2f5297fce4152d333d7a800c4ebd39c475c054cb11`.
- The post-open cleanup remediation changed the final material-diff SHA-256 to
  `ef206556097fbaf4c67d9859f3278fb0e8c78bf3e5bbf394fd79759e4de2ea7a`.
- Fresh Apple Container capability and attributed oracle artifacts were
  accepted after the rebase with one attempt and no retry.

## Implementation Commits

- `28888c0dba8c04f898092d8e15b706792fa4e5d6` - select one fail-closed Apple
  host-control address, preserve capability blocker parity, and bind accepted
  result attribution to the host-validated oracle request.
- `a42a36ca0b7ab2be6180ee0daf0a742f2574b5ed` - make initializer cleanup
  failure dominant and stop automatic backend fallback while cleanup integrity
  is unknown.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Pre-open packet and declared role order completed.
- [x] Actual-diff premortem completed with no open blocker.
- [x] Experiment Runner Apple Container capability and oracle evidence accepted.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed.
- [x] Required cursor-specialist and architecture follow-up roles completed.
- [ ] One sealed Codex Security diff scan completed for the final material diff.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI completed after this governance artifact is pushed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

- No actionable review comments

## Mapping Maintenance

This statement reflects the initial PR publication state. If a post-open role,
bot, human, or security review creates an actionable finding, fix or explicitly
disposition it first, then replace this no-actionable entry with the required
thread URL and commit/evidence/backlog proof before resolving the thread.

## Post-open Role Findings

### Initializer cleanup failure was masked

Disposition: FIXED

Commit: `a42a36ca0b7ab2be6180ee0daf0a742f2574b5ed`

Evidence:

- `scripts/orchestration/experiment_runner_dispatch.py:606` now promotes failed
  init-container cleanup over execution exceptions and nonzero exits.
- `scripts/orchestration/experiment_runner_dispatch.py:1198` stops `auto`
  selection before Docker when the Apple probe reports
  `container_cleanup_failed`.
- `tests/test_experiment_runner_dispatch.py:188` proves Docker is not probed
  after cleanup failure while ordinary rejection fallback remains covered.
- `tests/test_experiment_runner_dispatch.py:1178` and
  `tests/test_experiment_runner_dispatch.py:1201` cover exception and nonzero
  initializer outcomes with failed cleanup.

## Experiment Runner Evidence

Capability artifact:
`artifacts/orchestration/experiments/capabilities/combined-strict-dispatch-a42a36ca-capability.json`

Packet:
`artifacts/orchestration/experiments/packets/combined-strict-dispatch-a42a36ca-oracle-packet.json`

Artifact:
`artifacts/orchestration/experiments/results/combined-strict-dispatch-a42a36ca-oracle-result.json`

The capability artifact reports `strict_isolation=true`, no blockers, and all
probe flags true. The result is `accepted` on Apple Container 1.1.0 with one
attempt, zero retries, one successful immutable oracle command,
`shared_tree_untouched=true`, and the exact requested material attribution
tuple. Because the four-file diff is committed, the dispatcher cloned exact
HEAD and required no uncommitted overlay (`source_diff_applied=false`). No
temporary `pp-er-*` container, network, or volume remained.

## Premortem

- Ambiguous address selection: closed by requiring exactly one validated
  hostname-derived AF_INET/SOCK_STREAM candidate outside the runtime subnet.
- False-positive isolation: closed by the reachable host listener plus outer
  and inner host/DNS/direct-IP canaries.
- Bind race or candidate loss: closed by fail-closed
  `host_listener_unavailable` without fallback or retry.
- Host identity leakage: closed by never serializing the selected address.
- Attribution laundering: closed by pre-probe tuple validation and exact
  accepted/reset rejected result validation.
- Candidate-mode authority drift: closed by rejecting material attribution
  before runtime probing.
- Resource leakage: closed by forced container/network/volume cleanup and the
  fresh post-run resource inspection.

## Validation Evidence

- PASS: orchestration preflight and agent consistency.
- PASS: 177 focused dispatcher/runner tests after the P1 remediation.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS: full pre-push hooks, including MyPy, `pip-audit`, backend tests,
  Bandit, and Docker build test.
- PASS: `git diff --check origin/main...HEAD`.
- PASS: current-base strict Apple capability probe.
- PASS: one current-base attributed Experiment Runner oracle run.
- PENDING: canonical current-head GitHub CI after this mapping commit.
- NOT RUN: local full `make verify`; prohibited by the repository local budget
  rule.

## Security Review

- PASS: pre-open security-auditor and local Bandit/pre-commit checks found no
  actionable issue on the pre-review patch-id.
- PASS: the mandatory post-open security-auditor confirmed the cleanup P1; it
  was fixed in `a42a36ca0` and covered by deterministic regressions.
- PENDING: one sealed Codex Security diff scan on the final post-review
  material diff. Per operator direction, do not repeat it unless a
  security-relevant material change invalidates the seal.
- PENDING: `pulseplate-pr-review`.

## Risks / Rollback

Hosts with zero or multiple eligible addresses fail closed intentionally.
Schema parity is protected by closed validation and deterministic tests.
Attribution mismatch fails as `result_validation_failed` without exposing raw
metadata. Rollback is a revert of the single material commit; no DB, OpenAPI,
provider, cache, deployment, or client rollback is required.

## Deferred / Follow-ups

- PR #2117 remains a separate non-overlapping Caddy/deploy lane.
- Resume the approved RAG confidence-provenance product outcome after this
  strict-dispatch prerequisite is merged.
- Evidence Graph, transition statistics, shadow Bayesian calibration, learned
  Markov behavior, semantic-cache serving, and OCW projection remain separate
  later lanes.
