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
- Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed in
  the declared order; the QA and bug-hunter final-head follow-ups found no new
  actionable defect.
- Sealed Codex Security scan `c28f183e-577c-42ea-8a9a-525f20e170d3` and
  `pulseplate-pr-review` completed for material head `a0696db25`.

## Implementation Commit

- `f4efdc36306588a4825f1ff049bf8eda565cdb57` - replace whole-root output
  deltas with strict receipt ownership, add deterministic foreign-sibling and
  parser regressions, and prove lineage failures never reach publication.
- `a0696db25d0ce31ea5a7bc1bcd69ee078d65d345` - add a fail-fast
  `Path.mkdir` oracle so lineage rejection proves that neither run-owned
  staging nor final publication can be created before failure.

Last validated material head:
`a0696db25d0ce31ea5a7bc1bcd69ee078d65d345`. Any later tracked commits in this
lane are governance-only updates to this canonical artifact.

## Governance Remediation Commit

- `b3b0decf4a31d2f29cf5b3a85e2cb41b769243f1` - bind all mandatory local,
  role-review, security, and CI evidence to final material head `a0696db25`,
  replacing the stale prior-head artifact accepted by the pre-refresh parser.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Current issue comments and reviews inspected at material head
  `a0696db25d0ce31ea5a7bc1bcd69ee078d65d345`.
- [x] Current bot capacity notices dispositioned below.
- [x] Both actionable review threads dispositioned below.
- [x] Mandatory post-open role-agent chain completed.
- [x] Codex Security diff scan and `pulseplate-pr-review` completed.
- [x] Current-head CI at the final material head inspected; strict
  authenticated merge readiness remains pending thread resolution and the
  final governance-only review cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#discussion_r3583378560
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor f4efdc36306588a4825f1ff049bf8eda565cdb57 a0696db25d0ce31ea5a7bc1bcd69ee078d65d345` exits `0`; current PR history is `f4efdc363 -> b438acff8 -> a0696db25`, and `f4efdc363` carries the required Experiment Runner co-author trailer.
Reason: The cited implementation commit is an ancestor of the actual published material head; the comment's synthetic `adbaa974` snapshot is not the current PR head, and this artifact also names the later review-fix commit explicitly.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#discussion_r3583378562 -> a0696db25d0ce31ea5a7bc1bcd69ee078d65d345
Disposition: FIXED
Commit: a0696db25d0ce31ea5a7bc1bcd69ee078d65d345
Evidence: `tests/test_creative_pilot_workspace.py:1700` installs a fail-fast `Path.mkdir` spy for direct staging/output creation under `spec_root` while preserving the independent publisher spy; the focused pack passed 12 tests and the full file passed 78 tests, and the post-comment commit is not trigger-only.

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
  FIXED by fail-fast spies on both direct `Path.mkdir` staging/output creation
  under `spec_root` and `_atomic_publish_directory_noreplace`, while retaining
  exit-code, error-text, traceback, and byte-stability assertions.
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
  attach/reentry, and source-fingerprint pack; 12 selected tests.
- PASS: full `tests/test_creative_pilot_workspace.py`; 78 tests.
- PASS: branch-scoped `make validate-changed`; selected and completed the full
  changed test file.
- PASS: `pre-commit run --all-files` after the first Black pass formatted the
  changed file; no hook-produced tracked change remained.
- PASS: commit and pre-push hooks, including secrets, Black, Ruff, Bandit,
  pip-audit, backend tests, and applicable policy checks.
- PASS: `git diff --check`.
- NOT RUN: local full `make verify`; prohibited by repository local budget
  policy.
- PASS at material head `a0696db25`: canonical CI `lint`, `security`, Python
  3.13 `test-pr`, `coverage-pr`, `diff-coverage`, CodeQL, Codecov patch,
  governance, and applicable build checks.
- EXPECTED SKIP: `test-main`, `test-feature`, `coverage-main`, and
  `coverage-feature` were not selected by the canonical changed-path router;
  the applicable Python 3.13 `test-pr` job passed.
- EXPECTED BLOCKER: the current-head `Merge readiness gate` failed only because
  the two review threads were still unresolved when it ran.

## Security Review

- The material diff is test-only and adds no auth, secret, network,
  subprocess, quota, persistence, deploy, or runtime trust boundary.
- Strict canonical evidence-ID parsing rejects traversal-like, malformed,
  idempotent, missing-directory, and multi-line ownership receipts.
- PASS: post-open `security-auditor` found no runtime-security actionable in
  the test-only material diff.
- PASS: sealed Codex Security scan
  `c28f183e-577c-42ea-8a9a-525f20e170d3` covered 2/2 changed files for
  `b432aeb78a6b18cdedf760bb7872daf9241dacd6..a0696db25d0ce31ea5a7bc1bcd69ee078d65d345`.
  The adaptive-resume ownership/lineage surface had no finding.
- The scan reported one Low/P3 governance finding,
  `csf_68bf70902fb8efcc7b18f6d9`: prior-head evidence remained in this mapping
  after the later material review fix. Disposition: FIXED. Commit:
  `b3b0decf4a31d2f29cf5b3a85e2cb41b769243f1`. Evidence: that governance-only
  commit binds every mandatory evidence claim to material head `a0696db25`;
  this follow-up records its immutable proof without changing the material
  surface.
- The scan's structural head-binding option is advisory design guidance for a
  separately authorized governance lane. It is not needed to close this
  concrete stale artifact instance and is not implemented in this test-only
  hotfix.
- PASS: final-material-head `pulseplate-pr-review` and its 11 calibration tests.
  Its only `NEEDS-HUMAN` note was the 336-line review threshold.
  Disposition: NOT-A-BUG. The diff is two coherent files: one functional test
  file plus this mandatory numbered governance artifact; splitting either
  would remove required evidence from the same PR. Focused, full-file,
  `make validate-changed`, and pre-commit gates passed.

## Risks / Rollback

The test now intentionally depends on the canonical one-line CLI publication
receipt. If that receipt changes, update the focused parser contract instead
of relaxing ownership back to substring or shared-directory inference.
Rollback is the single functional commit, but reverting it restores the
confirmed main flake; prefer a narrow follow-up receipt-contract update.

## Merge Readiness

- [x] Functional diff is limited to one test file.
- [x] Required local narrow validation passed at final material head.
- [x] Pre-open role order, premortem, and Experiment Runner completed.
- [x] Mandatory post-open review/security chain completed.
- [x] Sealed Codex Security scan and `pulseplate-pr-review` completed at the
  final material head.
- [x] Applicable current-head CI at material head `a0696db25` is terminal PASS;
  the Python 3.13 `test-pr` lane ran, while `test-main` was canonically skipped.
- [ ] Both review threads resolved only after their dispositions are published.
- [ ] CodeRabbit, Sourcery, and Cubic are checked for actionable findings after
  the final governance-only activity.
- [ ] Strict authenticated merge-readiness and mandatory final review window
  completed.

## Deferred / Follow-ups

- None.
