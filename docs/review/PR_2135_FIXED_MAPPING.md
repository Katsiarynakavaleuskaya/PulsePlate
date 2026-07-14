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
- Rebase to current `origin/main` preserved stable patch-id
  `51dbab38c84d9684fdbe244ab22c59f929732d53`; the exact material-diff SHA-256
  is `26018c59265205b564780f2f5297fce4152d333d7a800c4ebd39c475c054cb11`.
- Fresh Apple Container capability and attributed oracle artifacts were
  accepted after the rebase with one attempt and no retry.

## Implementation Commits

- `28888c0dba8c04f898092d8e15b706792fa4e5d6` - select one fail-closed Apple
  host-control address, preserve capability blocker parity, and bind accepted
  result attribution to the host-validated oracle request.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Pre-open packet and declared role order completed.
- [x] Actual-diff premortem completed with no open blocker.
- [x] Experiment Runner Apple Container capability and oracle evidence accepted.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed.
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

## Experiment Runner Evidence

Capability artifact:
`artifacts/orchestration/experiments/capabilities/combined-strict-dispatch-b432aeb7-capability.json`

Packet:
`artifacts/orchestration/experiments/packets/combined-strict-dispatch-b432aeb7-oracle-packet.json`

Artifact:
`artifacts/orchestration/experiments/results/combined-strict-dispatch-b432aeb7-oracle-result.json`

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
- PASS: 174 focused dispatcher/runner tests.
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
  actionable issue on the exact stable patch-id.
- PENDING: the mandatory post-open security-auditor pass.
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
