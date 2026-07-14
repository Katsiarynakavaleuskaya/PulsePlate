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
- [x] One sealed Codex Security diff scan completed for the final material diff.
- [x] `pulseplate-pr-review` completed.
- [ ] Current-head CI completed after this governance artifact is pushed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2135#discussion_r3583221528
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_2135_FIXED_MAPPING.md` records the local `qa-engineer-agent -> bug-hunter -> security-auditor` finding separately in `Post-open Role Findings`, including remediation commit `a42a36ca0` and deterministic test proof.
Reason: the cleanup finding was created before this GitHub discussion existed, so it has no truthful historical thread URL; mapping this new comment to the earlier commit would violate commit-after-comment governance, while this thread is now listed with an evidence-backed disposition.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2135#pullrequestreview-4699236666
Disposition: NOT-A-BUG
Evidence: the sole actionable child thread https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2135#discussion_r3583221528 is separately mapped with proof in this section; the CodeRabbit review summary contains no independent defect.
Reason: this review-summary URL only aggregates the already-dispositioned child governance thread and contains no additional code, security, or test finding.

## Mapping Maintenance

This section now reflects the current GitHub discussion-thread state. If a
later bot, human, or security review creates another actionable finding, fix
or explicitly disposition it first, then add the required thread URL and
commit/evidence/backlog proof before resolving the thread.

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

## PulsePlate PR Review

Disposition: NOT-A-BUG

Evidence:

- Local gitignored report:
  `artifacts/orchestration/pr_reviews/pr-2135-45c65ee3/report.md`
  (`sha256:4ffe35775e0c1a63b26f714626c79640c3b86e75c17827c720228c1bc07796d0`).
- The report found no correctness, security, architecture, QA, or governance
  defect. Its only advisory note was the deterministic large-diff threshold.
- The PR body records the atomic split justification: 218 dispatcher lines and
  59 contract/runbook lines are coupled to 942 lines of deterministic negative,
  parity, forwarding, and cleanup tests.
- `177` focused dispatcher/runner tests, `make validate-changed`, and the full
  pre-commit pass provide the targeted evidence requested by that advisory.

Reason: the threshold note is review-planning evidence, not a code defect or a
merge-readiness claim; the required split rationale and focused validation are
already present.

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
- PASS: `22` focused `pr_review_context` / `pr_review_report` tests.
- PASS at scanned head `45c65ee3e8d8e9d8ae86dd71c4dab3215f1fa209`:
  canonical CI, lint, security, OpenAPI, test-pr 3.13, coverage, and diff
  coverage were terminal. A mapping-only follow-up commit requires fresh
  current-head CI before any readiness claim.
- PENDING: canonical current-head GitHub CI after this mapping commit.
- NOT RUN: local full `make verify`; prohibited by the repository local budget
  rule.

## Security Review

- PASS: pre-open security-auditor and local Bandit/pre-commit checks found no
  actionable issue on the pre-review patch-id.
- PASS: the mandatory post-open security-auditor confirmed the cleanup P1; it
  was fixed in `a42a36ca0` and covered by deterministic regressions.
- PASS: one Codex Security diff scan was sealed with zero findings and complete
  coverage for exact range
  `b432aeb78a6b18cdedf760bb7872daf9241dacd6...45c65ee3e8d8e9d8ae86dd71c4dab3215f1fa209`.
- Scan ID: `48fae63a-a7db-4db2-a1d5-01c5cd6fc92b`; snapshot digest:
  `codex-security-snapshot/v1:sha256:05487a0524fbc6c7de026619180ddeb646ab905fb49221b9e052925988bebe82`.
- Sealed report SHA-256:
  `cd5779e68c9ee6c73397534009df83821998625c60c3c8041c634e18eafc20c3`;
  local gitignored copy:
  `artifacts/security_lab/pr-2135-final-45c65ee3/report.md`.
- Per operator cost/noise policy, do not repeat the scan unless a
  security-relevant material change invalidates this seal. Governance-only
  mapping/body updates do not change the reviewed runtime, contract, runbook,
  or test material.

## External Review Sources

- Sourcery: PASS on the scanned head, with no blocking security issue.
- CodeRabbit: PASS / review completed on head
  `81a265e83247ed656fafdf186f9bded7b6077a3e`. Its sole governance thread is
  dispositioned above; it reported no runtime, security, architecture, or test
  defect.
- Cubic: SOURCE-DEGRADED / NEUTRAL because its monthly line quota was reached;
  no no-actionables proof exists:
  https://www.cubic.dev/pr/Katsiarynakavaleuskaya/PulsePlate/pull/2135
- Cursor Bugbot: SOURCE-DEGRADED because it is disabled; this is not a code
  finding:
  https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2135#issuecomment-4974134261
- GitHub review threads: zero total and zero unresolved at the scanned head.

Cubic remains an explicit merge-governance blocker under root `AGENTS.md`
until it provides PASS / no-actionables evidence. The local role chain, sealed
security scan, CodeRabbit review, and `pulseplate-pr-review` cannot replace
that hard gate.

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
