# PR #2136 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136

Branch: `codex/fix-adaptive-resume-output-ownership`

## Summary

Bind adaptive-resume tests to the exact canonical `resume_id` emitted by their
own successful CLI invocation. This removes cross-shard ownership inference
from the shared `spec_bridge` directory while preserving the production CLI,
publication locks, schemas, workflows, shard runner, and fail-closed lineage
contracts.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/9776c3e6375e.json`
  (local-only, gitignored).
- Starter: `scripts/orchestration/start_pr_lane.sh`.
- Pre-open runtime order completed:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter`.
- The actual-diff 48-hour hotfix premortem completed with decision `proceed`;
  every concrete finding is dispositioned below.
- Experiment Runner result `exp-2561c6a43b19` was accepted after both local
  immutable oracles passed and the shared tree remained untouched.
- Post-open `qa-engineer-agent -> bug-hunter -> security-auditor`, Codex
  Security, and `pulseplate-pr-review` remain mandatory before readiness.

## Implementation Commit

- `f4efdc36306588a4825f1ff049bf8eda565cdb57` - replace whole-root output
  deltas with strict receipt ownership, add deterministic foreign-sibling and
  parser regressions, and prove lineage failures never reach publication.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Current issue comments and reviews inspected at functional head
  `f4efdc36306588a4825f1ff049bf8eda565cdb57`.
- [x] Current bot capacity notices dispositioned below.
- [x] No actionable review thread existed when this artifact was created.
- [ ] Mandatory post-open role-agent chain completed.
- [ ] Codex Security diff scan and `pulseplate-pr-review` completed.
- [ ] Current-head CI and strict authenticated merge readiness completed.

## Fixed in Commit Mapping

- No actionable review comments

## Bot Capacity Notices

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#issuecomment-4974875390

Disposition: NOT-A-BUG

Evidence: Cursor reports that Bugbot is not enabled and explicitly states that
no review was performed. The comment requests no repository change.

Reason: Reviewer availability is external service state, not a code defect,
approval, or merge-readiness signal.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#issuecomment-4974875914

Disposition: NOT-A-BUG

Evidence: CodeRabbit reports a temporary review-capacity limit and identifies
the exact one-file range it would review. It provides no code, test, security,
or governance finding.

Reason: A rate-limit notice is external capacity state, not an actionable PR
finding or approval. Review availability must be checked again after the
documented wait window.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#pullrequestreview-4699268097

Disposition: NOT-A-BUG

Evidence: Sourcery reports only its weekly diff-character limit and requests
no repository change.

Reason: The COMMENTED quota notice is external capacity state, not a code
finding or merge-readiness evidence.

- Cubic completed with a neutral status and did not publish an actionable
  finding. This is recorded as no-actionable status evidence, not substantive
  approval.

## Premortem

- Wrong output selected under concurrent publication: FIXED by strict
  schema-shaped stdout parsing, direct `spec_root / resume_id` lookup, and a
  regression that creates two foreign siblings after the real publisher runs.
- Captured output contaminated or ambiguous: FIXED by exact one-line
  `re.fullmatch`, negative parser cases, and immediate capture reset/consume at
  both callers.
- Foreign regression artifacts leak across shards: FIXED by unique sibling
  identities and `finally` cleanup of every recorded publication path.
- Invalid lineage reaches publication after removing whole-tree equality:
  FIXED by a fail-fast spy on `_atomic_publish_directory_noreplace` while
  retaining exit-code, error-text, traceback, and byte-stability assertions.
- Runtime/governance scope silently widens: NOT-A-BUG. The material commit
  changes one test file; this numbered artifact is mandatory governance
  overhead and does not alter runtime behavior.
- Deferred findings: none.

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/exp-2561c6a43b19.json`

- Mode: `oracle_only_governance_reviewer`.
- Result: `accepted`; failure class `null`.
- Source diff applied only to `tests/test_creative_pilot_workspace.py`.
- Focused ownership/lineage oracle: return code `0`, `10 passed`.
- `git diff --check`: return code `0`.
- `shared_tree_untouched=true`, `mutated_paths=[]`.
- Contribution kind: `commit_decision`; `coauthor_required=true`.
- Commit `f4efdc363` carries the canonical Experiment Runner co-author trailer.

The zero-network packet `exp-bdf382a24e91` was rejected before oracle
execution because this macOS host lacks Linux `unshare`. A second packet using
the bare `pytest` console command, `exp-cc1369843e1d`, was rejected because the
isolated checkout did not bind that command to the repo interpreter. Neither
rejected artifact is used as evidence or attribution. The accepted packet uses
the repo-approved `python -m pytest` command and bounded `network_budget=1`;
both oracle commands are local and grant no product, provider, runtime, or
network authority.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --path
  tests/test_creative_pilot_workspace.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: focused parser, foreign-sibling, exact-publication, lineage,
  attach/reentry, and source-fingerprint pack.
- PASS: full `tests/test_creative_pilot_workspace.py`.
- PASS: branch-scoped `make validate-changed`; selected and completed the full
  changed test file.
- PASS: `pre-commit run --all-files` after the first Black pass formatted the
  changed file; no hook-produced tracked change remained.
- PASS: commit and pre-push hooks, including secrets, Black, Ruff, Bandit,
  pip-audit, backend tests, and applicable policy checks.
- PASS: `git diff --check`.
- NOT RUN: local full `make verify`; prohibited by repository local budget
  policy.
- PENDING: canonical current-head GitHub CI, including Python 3.13 `test-main`
  and diff coverage at or above 97%.

## Security Review

- The material diff is test-only and adds no auth, secret, network,
  subprocess, quota, persistence, deploy, or runtime trust boundary.
- Strict canonical evidence-ID parsing rejects traversal-like, malformed,
  idempotent, missing-directory, and multi-line ownership receipts.
- PENDING: mandatory post-open security-auditor pass.
- PENDING: one sealed Codex Security diff scan / finding discovery pass.
- PENDING: `pulseplate-pr-review` on the published diff.

## Risks / Rollback

The test now intentionally depends on the canonical one-line CLI publication
receipt. If that receipt changes, update the focused parser contract instead
of relaxing ownership back to substring or shared-directory inference.
Rollback is the single functional commit, but reverting it restores the
confirmed main flake; prefer a narrow follow-up receipt-contract update.

## Merge Readiness

- [x] Functional diff is limited to one test file.
- [x] Required local narrow validation passed at functional head.
- [x] Pre-open role order, premortem, and Experiment Runner completed.
- [ ] Mandatory post-open review/security chain completed.
- [ ] All current-head required checks are terminal PASS.
- [ ] CodeRabbit, Sourcery, and Cubic are checked for actionable findings after
  the final material activity.
- [ ] Strict authenticated merge-readiness and mandatory final review window
  completed.

## Deferred / Follow-ups

- None.
