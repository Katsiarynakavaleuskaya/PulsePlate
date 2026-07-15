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
- `7448523de72a9b74ba90c582a77b7203ca1c726e` - restore the fail-closed final
  cycle by leaving every merge-readiness checkbox unchecked until the final
  current-head CI, bot, wait-window, and strict-wrapper pass.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Current issue comments and reviews inspected through published governance
  head `0294f0a55c49dde056e490fd087985a5d59126da`.
- [x] Current bot capacity and status notices dispositioned below.
- [x] All four actionable review threads and their actionable review summaries
  dispositioned below.
- [x] Mandatory post-open role-agent chain completed.
- [x] Codex Security diff scan and `pulseplate-pr-review` completed.
- [x] Current-head CI and bot activity at published governance head `0294f0a55`
  inspected; a transient package-proxy reset and the two newly dispositioned
  threads keep strict authenticated merge readiness pending.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#discussion_r3583378560
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor f4efdc36306588a4825f1ff049bf8eda565cdb57 a0696db25d0ce31ea5a7bc1bcd69ee078d65d345` exits `0`; current PR history is `f4efdc363 -> b438acff8 -> a0696db25`, and `f4efdc363` carries the required Experiment Runner co-author trailer.
Reason: The cited implementation commit is an ancestor of the actual published material head; the comment's synthetic `adbaa974` snapshot is not the current PR head, and this artifact also names the later review-fix commit explicitly.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#discussion_r3583378562 -> a0696db25d0ce31ea5a7bc1bcd69ee078d65d345
Disposition: FIXED
Commit: a0696db25d0ce31ea5a7bc1bcd69ee078d65d345
Evidence: `tests/test_creative_pilot_workspace.py:1700` installs a fail-fast `Path.mkdir` spy for direct staging/output creation under `spec_root` while preserving the independent publisher spy; the focused pack passed 12 tests and the full file passed 78 tests, and the post-comment commit is not trigger-only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#pullrequestreview-4703167417 -> 7448523de72a9b74ba90c582a77b7203ca1c726e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#discussion_r3586417559 -> 7448523de72a9b74ba90c582a77b7203ca1c726e
Disposition: FIXED
Commit: 7448523de72a9b74ba90c582a77b7203ca1c726e
Evidence: The review summary has exactly one actionable inline thread. `docs/review/PR_2136_FIXED_MAPPING.md:255` now leaves every item under `Merge Readiness` unchecked until the final current-head CI, bot, wait-window, and strict-wrapper cycle completes; the artifact-first Phase 2 parser passes, and the post-comment commit is not trigger-only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#discussion_r3586429963
Disposition: NOT-A-BUG
Evidence: GitHub anchors the review comment to actual commit `0294f0a55c49dde056e490fd087985a5d59126da`; the PR commits API returns the linear history `f4efdc363 -> b438acff8 -> a0696db25 -> b3b0decf4 -> 0294f0a55`, and `git merge-base --is-ancestor` exits `0` for every cited proof commit against `0294f0a55`.
Reason: The body-only `2d5fbaab` snapshot is not in the GitHub PR commit list, and the repository commit endpoint returns `No commit found for SHA: 2d5fbaab (HTTP 422)`. It cannot replace the authoritative GitHub review commit or the published branch history.

## Bot Capacity and Status Notices

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#issuecomment-4974875390

Disposition: NOT-A-BUG

Evidence: Cursor reports that Bugbot is not enabled and explicitly states that
no review was performed. The comment requests no repository change.

Reason: Reviewer availability is external service state, not a code defect,
approval, or merge-readiness signal.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#issuecomment-4974875914

Disposition: NOT-A-BUG

Evidence: CodeRabbit's current incremental status says there are no new commits
to review beyond its completed published-head pass. Its one actionable
governance thread is mapped as `FIXED` above.

Reason: The issue-level incremental status is not a separate code finding or
approval; the substantive inline result remains governed by its own thread.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2136#issuecomment-4979517794

Disposition: NOT-A-BUG

Evidence: The explicit final CodeRabbit command completed and reports no new
commits to review; it introduced no additional inline finding beyond the
published-head thread mapped above.

Reason: This is a completion status for the requested review cycle, not an
actionable repository change or independent approval.

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
- EXPECTED BLOCKER: the governance-head `Merge readiness gate` failed only
  because the two earlier review threads were still unresolved when it ran;
  both were dispositioned and resolved afterward, before the final bot cycle.
- RETRY REQUIRED at governance head `0294f0a55`: CI run `29407857373` failed
  `lint` during locked dependency installation with
  `ConnectionResetError(104, 'Connection reset by peer')` from the approved
  package proxy. This is external transport state, not a passing signal; the
  failed job must succeed on retry before strict readiness.

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
- PASS: final-material-head `pulseplate-pr-review`, its published-governance-head
  follow-up, and 11 calibration tests. The only `NEEDS-HUMAN` note was the
  393-line review threshold after governance evidence expanded.
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

- [ ] Functional diff is limited to one test file.
- [ ] Required local narrow validation passed at final material head.
- [ ] Pre-open role order, premortem, and Experiment Runner completed.
- [ ] Mandatory post-open review/security chain completed.
- [ ] Sealed Codex Security scan and `pulseplate-pr-review` completed at the
  final material head.
- [ ] Applicable current-head CI at material head `a0696db25` is terminal PASS;
  the Python 3.13 `test-pr` lane ran, while `test-main` was canonically skipped.
- [ ] All review threads resolved only after their dispositions are published.
- [ ] CodeRabbit, Sourcery, and Cubic are checked for actionable findings after
  the final governance-only activity.
- [ ] Strict authenticated merge-readiness and mandatory final review window
  completed.

## Deferred / Follow-ups

- None.
