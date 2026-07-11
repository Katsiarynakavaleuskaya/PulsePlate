# PR #2098 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098

Branch: `codex/fix-unicode-lowercase-expansion-issue-in-bmi-parser`

## Summary

Preserve BMI unit offsets in the original Unicode string, use a bounded
candidate-position-first matcher, and remove the cross-process test race caused
by a guard fixture mutating the real repository `app/` directory. Public BMI
outputs, artifact-reader policy, OpenAPI, workflows, runtime lifecycle, and
Creative-Code authority remain unchanged.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/3b4abac6528b.json`
- Required order executed before implementation:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`.
- Experiment Runner stayed `oracle_only_governance_reviewer`; it received no
  patch, repository, GitHub, runtime, or promotion authority.

## Implementation Commits

- `df6a9b9cd` - preserve original-string BMI unit offsets after the rebase onto
  `6fab2e4ce`.
- `af3e960e9` - replace units-first matching with bounded candidate-first
  traversal and close Unicode, case, boundary, and branch-coverage gaps.
- `989882c80` - isolate the BMI guard fixture under `tmp_path/app` and remove
  the exact transient-read exception and filters while preserving fail-closed
  source-read errors.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial discussion-thread pass found no inline review threads.
- [x] Initial fixed-in-commit mapping covers the material code/test fixes.
- [x] Mandatory post-push `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed.
- [x] Codex Security current-diff scan completed.
- [x] `pulseplate-pr-review` completed.
- [ ] CodeRabbit, Sourcery, and Cubic current-head reviews contain no actionables.
- [ ] Current-head CI completed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

Future actionable human, bot, role, or security findings must be fixed or
dispositioned here before thread resolution or merge-readiness claims.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: af3e960e97a55bcc2152cdfdf29fce39b1f6c04c
Evidence: `core/bmi/query.py:81` scans source positions before fixed unit aliases; `tests/test_bmi_query_redos_guard.py:23`, `:40`, `:49`, `:59`, and `:70` cover invalid candidates, Unicode expansion, mixed Latin/Cyrillic case, punctuation boundaries, short/no-match inputs, and the exact 256/257 limit.
Reason: The Sourcery performance concern is closed by bounded `O(N * U * L)` traversal, and its boundary concern is closed without changing the case-independent `isalnum()`/underscore contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#pullrequestreview-4674848518 -> af3e960e97a55bcc2152cdfdf29fce39b1f6c04c

Disposition: FIXED
Commit: af3e960e97a55bcc2152cdfdf29fce39b1f6c04c
Evidence: A local branch-coverage run over `tests/test_bmi_query_redos_guard.py` reports `core/bmi/query.py` at 100% line and branch coverage with 0 partial branches; canonical current-head CI remains required after publication.
Reason: The old Codecov comment reported one partial branch on the superseded head; the post-comment regression commit exercises every new matcher branch.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#issuecomment-4939439428 -> af3e960e97a55bcc2152cdfdf29fce39b1f6c04c

Disposition: NOT-A-BUG
Evidence: The listed sources contain availability, summary, or no-issues output and no code or governance actionable.
Reason: Cursor Bugbot was unavailable, Sourcery's guide and CodeRabbit's comment were generated summaries, and Cubic reported `No issues found` on the superseded two-file head; current-head review is still required after push.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#issuecomment-4939338218
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#issuecomment-4939339330
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#issuecomment-4939340205
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#pullrequestreview-4674863560

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor af3e960e97a55bcc2152cdfdf29fce39b1f6c04c a44cdf714cc41e620c0d771678776908a469290e` passes, and the published branch history contains `af3e960e`, `989882c80`, `49f02322a`, and `a44cdf714`.
Reason: The review analyzed a stale alternate commit `70c598d`; on the actual current branch, the mapped parser fix is reachable and remains valid proof.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#discussion_r3564256704

Disposition: FIXED
Commit: a44cdf714cc41e620c0d771678776908a469290e
Evidence: At exact head `a44cdf714`, the focused four-file pytest bundle, `make validate-changed`, `pre-commit run --all-files`, and `git diff --check` all pass after the review comment.
Reason: The current-head rerun supplies the exact validation evidence requested by the thread without weakening or skipping a gate.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#discussion_r3564256708 -> a44cdf714cc41e620c0d771678776908a469290e

Disposition: NOT-A-BUG
Evidence: Current reachable material commits `af3e960e97a55bcc2152cdfdf29fce39b1f6c04c` and `989882c80846984285435f268ba6d0373f54ba04`, plus mapping commit `49f02322ae936d5949e44d340234fa1fdfa769e7`, contain the exact `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer.
Reason: The review inspected stale commit `70c598d`; the actual material commits that will land satisfy the Experiment Runner attribution invariant.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#discussion_r3564256710

Disposition: NOT-A-BUG
Evidence: GitHub reports PR `headRefOid=aba5be27e3391e4715414a360051c9b58ad020b2`, while repository commit lookup for synthetic review id `d28766e` returns HTTP 422 `No commit found`; the real head contains the mapped commits.
Reason: The reviewer treated a connector-local synthetic patch id as the PR branch head, so its ancestry conclusion does not apply to the GitHub commit graph enforced by the repository guard.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#discussion_r3564318817

Disposition: NOT-A-BUG
Evidence: The claimed reviewed id `d28766e` is not a GitHub commit; actual head `aba5be27e` contains only mapping changes after exact material head `a44cdf714`, and its current-head CI passed lint, security, OpenAPI, `test-pr (3.13)`, and 100% diff coverage.
Reason: The validation evidence names the real tested SHA and does not certify the nonexistent connector-local synthetic id.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#discussion_r3564318818

Disposition: NOT-A-BUG
Evidence: GitHub commit `6fab2e4ceaf39b8afeb539070bbec448b3bf625e` shows that merge commits are available, while material commits `af3e960e` and `989882c80` retain the canonical Experiment Runner trailer; PR #2098 has an explicit merge-commit-only precondition and must stop rather than use squash or rebase if that method is unavailable.
Reason: PR #2099's topology is precedent, not proof of PR #2098's future result; preserving the material commits is an explicit merge-time gate for this PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2098#discussion_r3564318819

## Synthetic Reviewer Commit Evidence

- GitHub PR head at the second Codex review: `aba5be27e3391e4715414a360051c9b58ad020b2`.
- GitHub REST commit lookup for `70c598d` and `d28766e`: HTTP 422,
  `No commit found for SHA`.
- Actual PR commit history is the canonical ancestry source for fixed-mapping,
  exact-head validation, and Experiment Runner attribution.
- PR #2099 landed as `6fab2e4ce` with two parents, proving merge-commit support.
  PR #2098 must use a merge commit; squash/rebase is forbidden for this merge
  because it would require a separately attributed landed material commit.

## Pre-Implementation Role Findings

### Agent Coordinator

Disposition: NOT-A-BUG
Evidence: Packet `3b4abac6528b` bounded the implementation to the parser, two
test files, and this mapping artifact and preserved the required review order.
Reason: No scope, architecture, or routing blocker remained after the exact-SHA
rebase.

### QA Engineer Agent

Disposition: FIXED
Commit: `af3e960e9`, `989882c80`
Evidence: The parser regression matrix covers original-index Unicode behavior,
mixed case, actual suffix semantics, recovery, and exact query limits; the
guard fixture uses `tmp_path/app` and five paired xdist runs pass.
Reason: The QA role's candidate-first and test-isolation requirements are
implemented and deterministic.

### Bug Hunter

Disposition: FIXED
Commit: `af3e960e9`, `989882c80`
Evidence: `core/bmi/query.py:95` now uses candidate-position-first traversal;
`tests/test_no_bmi_math_outside_core.py:418` proves real source read errors
propagate, and `:600` proves threshold detection using only an isolated root.
Reason: The reproduced units-first blocker and shared-filesystem race are both
closed without weakening production or guard behavior.

### Security Auditor

Disposition: FIXED
Commit: `af3e960e9`, `989882c80`
Evidence: `_MAX_BMI_QUERY_CHARS` remains 256 and is checked before scanning;
the matcher remains bounded and original-indexed; no transient source-read
suppression remains; Experiment Runner immutable security/guard oracles pass.
Reason: No remaining availability, Unicode-index, boundary-bypass, TOCTOU, or
fail-open finding was identified in the implemented scope.

## Post-Push Current-Diff Review

### QA Engineer Agent

Disposition: NOT-A-BUG
Evidence: Exact published code head `49f02322a` passed 37 focused parser/guard tests, five 82-test xdist runs, 100% line and branch coverage with zero partials, four-file scope, and clean-worktree verification.
Reason: No current-diff QA defect was found; the later `a44cdf714` change is mapping-only.

### Bug Hunter

Disposition: FIXED
Commit: `a44cdf714`
Evidence: The only finding was stale merge-readiness prose claiming force-with-lease publication remained pending; the Merge Readiness section now records the completed publication and only real remaining gates.
Reason: Production implementation passed; the mapping-truth defect was corrected and reverified.

### Security Auditor

Disposition: NOT-A-BUG
Evidence: Exact head `a44cdf714` retained the 256-character cap, bounded `O(N * U * L)` traversal, original-index reads, fail-closed source errors, isolated `tmp_path/app` fixtures, and consistent governance attribution.
Reason: No availability, boundary-bypass, Unicode-integrity, TOCTOU, or fail-open actionable survived.

### Codex Security

Disposition: NOT-A-BUG
Evidence: Sealed scan `70e61556-5359-4b18-9f8b-992fbbc42873` covered 1/1 source-like worklist row at `a44cdf714` and completed with zero reportable findings.
Reason: No technically plausible security candidate survived full-file and exact-diff discovery.

### PulsePlate PR Review

Disposition: NOT-A-BUG
Evidence: The dry-run report found only the advisory 443-line review-risk threshold; the operator-approved `Why not split` rationale, four-file scope, focused gates, and exact-head reruns provide the required human decision and deterministic evidence. Its 22 calibration/context tests pass through the repository virtual environment.
Reason: Large-diff risk is review-planning evidence, not a defect or merge-readiness claim, and the explicitly approved combined BMI scope has already received the full required review chain.

## Premortem

- Alias ordering or recovery changes: FIXED in `af3e960e9`; earliest valid
  Latin/Cyrillic aliases and invalid-then-valid candidates are regression-tested.
- Boundary semantic drift: FIXED in `af3e960e9`; alphanumeric/underscore
  suffixes remain invalid while punctuation, including `*`, remains valid.
- Guard becomes false-green after removing the race workaround: FIXED in
  `989882c80`; all real source read errors propagate and the isolated violation
  is still detected.
- Scope mixes production parsing and test stabilization: NOT-A-BUG; the
  operator explicitly approved this bounded three-file implementation because
  both defects are BMI-related and one blocks trustworthy `main` CI.
- A stochastic `main` rerun hides the race: NOT-A-BUG; attempt 1 reproduced the
  exact shared-file failure, while merge remains blocked on new PR-head and
  post-merge `main` evidence.

Decision: `proceed`; no premortem finding remains open.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-5101dc885b1d.json`

- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution: `commit_decision`
- Source diff paths: the three implementation files only
- Immutable oracles: 3/3 passed
- `mutated_paths: []`; `shared_tree_untouched: true`
- Co-author required: true; the canonical trailer is present on both material
  commits shaped by the result
- `promotion_ready: false`; no candidate patch or promotion authority was used

## Validation Evidence

- PASS: execute-mode preflight and agent consistency.
- PASS: focused parser/philosophical-runtime/BMI-guard/artifact-boundary bundle.
- PASS: five separate `-n 2 --dist=loadfile` guard/artifact-boundary runs.
- PASS: artifact-reader contract CLI.
- PASS: MyPy for `core/bmi/query.py`.
- PASS: local line/branch coverage for `core/bmi/query.py`: 100%, 0 partial branches.
- PASS: branch-diff backend pre-commit selector.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`; no hook modifications.
- PASS: `git diff --check`.
- PASS at exact head `a44cdf714`: focused four-file pytest bundle,
  `make validate-changed`, full pre-commit, and ancestry/trailer verification.
- PASS: 22 `pulseplate-pr-review` calibration/context tests via repo `.venv`.
- PASS: sealed Codex Security diff scan `70e61556-5359-4b18-9f8b-992fbbc42873`;
  1/1 worklist rows closed and zero findings.
- PASS: final implementation diff contains only the parser and two test files;
  no OpenAPI/generated-client artifact is changed.
- Not run: local full `make verify`, per repository machine-budget policy.

## Merge Readiness

Not claimed. Exact-lease publication and the post-push role, Codex Security,
and PR-review chain are complete through `a44cdf714`; the remaining gates are
publication of this mapping update, refreshed final-head bot reviews and CI,
strict authenticated merge readiness, and the final wait window.

Merge method precondition: merge commit only. If GitHub does not permit a merge
commit at merge time, stop; do not fall back to squash or rebase.

## Deferred / Follow-ups

None introduced by this PR. The next legacy compatibility-cutover remains a
separate production PR after PR #2098 merge and post-merge `main` stabilization.
