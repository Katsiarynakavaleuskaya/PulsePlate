# PR #1878 - Fixed in Commit Mapping

**Title:** `fix(tests): harden policy guard AST traversal`
**Branch:** `codex/main-ci-policy-ast-scan-node-modules`
**Scope:** Narrow main-CI guard-scanner hardening after run `26934350363`
failed in `test-main (3.11, 60)` while `Path.rglob("*.py")` traversed
`frontend/node_modules/@open-draft`.
**Implementation source commit:** `6c05ec31cfb9b62af970e27f4791424f9486fcbc`
**Branch-history proof commit:** `f1a272bf5a2daa531060d1d4033951555d590a73`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial fixed-mapping artifact created after PR #1878 opened.
- [x] PR body includes Discussion Thread Pass, Fixed in Commit Mapping, and
  Merge Readiness sections.
- [x] No review threads were present when this initial artifact was created.
- [x] Post-open role-agent sequence completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan / finding discovery completed with no findings.
- [x] `pulseplate-pr-review` completed with no deterministic findings.
- [ ] Final current-head CI and external bot review wait-window remain pending.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: f1a272bf5
Evidence: `docs/review/PR_1878_FIXED_MAPPING.md` records GitHub API proof that implementation commit `6c05ec31cfb9b62af970e27f4791424f9486fcbc` is reachable from the PR branch and that its commit message carries the canonical Experiment Runner co-author trailer.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355060599 -> f1a272bf5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355060602 -> f1a272bf5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355106818 -> f1a272bf5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355178562 -> f1a272bf5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355178566 -> f1a272bf5

Disposition: NOT-A-BUG
Evidence: GitHub PR commit-list proof at disposition time included `6c05ec31cfb9b62af970e27f4791424f9486fcbc`, `f1a272bf5a2daa531060d1d4033951555d590a73`, and `1fd1af54d7b0db2847fcc29d313e595d448b6143`; the implementation source commit message includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
Reason: These comments evaluate stale or synthetic reviewed heads `ab8a468fa4e84fd3d4247bd1bfb0eadf172ffabf`, `52b9d5f116e7cc903b32758e5457608d88218073`, `d840140368c7b44fe605fd06eb7a259134602f01`, and `9dd6f78df922a70848ccab5a0d67fe9b8b09dcb9`; the current PR branch history already contains the reachable implementation commit and required Experiment Runner trailer.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355201751
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355201759
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355254195
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355319263
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355319266
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355396444
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355396453

Disposition: NOT-A-BUG
Evidence: GitHub API proof at disposition time: `gh pr view 1878 --json commits` includes both `6c05ec31cfb9b62af970e27f4791424f9486fcbc` and `a8f40d4bc81ccef8c68685d88f0f676234476c05`; `gh api repos/Katsiarynakavaleuskaya/PulsePlate/compare/a8f40d4bc...947524673f712cac8c58a271274a396ce7835edd` returns `status=ahead, behind_by=0`; `gh api repos/Katsiarynakavaleuskaya/PulsePlate/compare/6c05ec31cfb9b62af970e27f4791424f9486fcbc...947524673f712cac8c58a271274a396ce7835edd` returns `status=ahead, behind_by=0`.
Reason: GitHub's PR commit list and compare API confirm the referenced FIXED proof commits are branch-history ancestors of the PR head; the reachability claim is not valid for the current GitHub PR state.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1878#discussion_r3355285162

## Mapping Update Protocol

GitHub review threads with actionable comments are recorded above.

Future resolved actionable comments must be appended here with one of:

- `Disposition: FIXED` plus branch-history commit SHA and evidence.
- `Disposition: NOT-A-BUG` plus repo evidence and reason.
- `Disposition: DEFERRED` plus backlog proof and PR-body follow-up note.

## Implementation Evidence

Disposition: FIXED
Commit: `6c05ec31cfb9b62af970e27f4791424f9486fcbc`
Evidence: `tests/test_repo_policy_guards.py` replaces recursive
`Path.rglob("*.py")` AST discovery with top-down `os.walk(..., onerror=...)`
pruning so skipped/generated directories are removed before descent.

Disposition: FIXED
Commit: `6c05ec31cfb9b62af970e27f4791424f9486fcbc`
Evidence: `tests/test_repo_policy_guards.py` preserves fail-closed traversal:
walk errors under skipped generated trees are ignored, while walk errors under
source paths such as `app/` are re-raised.

Disposition: FIXED
Commit: `6c05ec31cfb9b62af970e27f4791424f9486fcbc`
Evidence: Regression tests cover skipped dependency pruning, skipped generated
walk errors, source walk error re-raise, and the absolute-parent false-skip case
where the repo checkout sits under a parent named `frontend`.

## Branch-History Proof

- Branch-history proof commit:
  `f1a272bf5a2daa531060d1d4033951555d590a73`.
- Implementation source commit:
  `6c05ec31cfb9b62af970e27f4791424f9486fcbc`.
- GitHub PR commit-list evidence includes the implementation source commit and
  branch-history proof commit on this branch.
- Experiment Runner attribution evidence: the implementation source commit
  message includes the canonical
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer.

## Role-Agent / Premortem Pass

Pre-open role order completed from packet
`artifacts/orchestration/task_packets/c0cb821c2526.json`:

- `agent-coordinator` - PASS; scope locked to
  `tests/test_repo_policy_guards.py`, excluding backend runtime, OpenAPI,
  frontend runtime, iOS, dependency, and workflow changes.
- `qa-engineer-agent` - PASS; required generated dependency pruning,
  skipped-path traversal error ignore, source traversal error re-raise, focused
  pytest, changed validation, and pre-commit.
- `bug-hunter` - findings FIXED; required repo-root-relative skip checks and
  direct `onerror` regression coverage.
- `security-auditor` - PASS; required fail-closed source traversal behavior, no
  type ignores, no skips/xfails, no allowlists, no broad exception swallowing,
  and `followlinks=False`.

Post-open mandatory role sequence:

- `qa-engineer-agent` - PASS; no blockers, deterministic coverage accepted, and
  mapping artifact did not overclaim readiness.
- `bug-hunter` - PASS; no blockers after the branch was rebased onto current
  `origin/main`, with diff limited to the two intended files.
- `security-auditor` - PASS; no fail-closed weakening, no suppressions, no
  secrets, no workflow/dependency/runtime/OpenAPI changes, and no unsafe
  readiness claim.

Premortem:

- Skill: `pulseplate-premortem-risk-review`.
- Frame: 48 hours from now this CI hotfix made policy scanning less trustworthy.
- Decision: proceed with narrow changes.
- Closed as FIXED: false source skip from absolute parent path segments, broad
  traversal error swallowing, and stale-base risk after `main` moved during the
  lane.
- Remaining merge-time condition: current-head CI must pass on the latest PR
  head before any merge-readiness claim.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-c5dea592152e.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-c5dea592152e.json`
- Result: accepted.
- Mode: `oracle_only_governance_reviewer`.
- Oracle: `python -m pytest -q tests/test_repo_policy_guards.py`.
- Evidence: oracle returned 0 with `17 passed`,
  `source_diff_applied=true`,
  `source_diff_paths=["tests/test_repo_policy_guards.py"]`, and
  `shared_tree_untouched=true`.
- Attribution: the accepted oracle evidence shaped the implementation decision,
  and implementation commit `6c05ec31cfb9b62af970e27f4791424f9486fcbc`
  includes the canonical
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path tests/test_repo_policy_guards.py`
  passed.
- `python3 scripts/orchestration/check_agent_consistency.py` passed.
- `.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py` passed:
  `17 passed`.
- `make validate-changed` passed: selected `tests/test_repo_policy_guards.py`,
  `17 passed`.
- `pre-commit run --all-files` passed.
- Pre-push hooks passed: applicable formatting, lint, secrets/workflow checks,
  backend pre-push pytest, full-repo Bandit, and docker build path filtering.
- `.venv/bin/python -m pytest tests/test_pr_review_report.py -q` passed:
  `9 passed`.
- `pulseplate-pr-review` dry-run report completed after the rebase onto current
  `origin/main`: clean context, 2 changed files, and no deterministic findings.

## Security Review Evidence

- Codex Security diff scan / finding discovery completed locally against the
  scoped PR diff.
- Reviewed surfaces: `tests/test_repo_policy_guards.py` and
  `docs/review/PR_1878_FIXED_MAPPING.md`.
- Result: no technically plausible security candidates, no reportable findings,
  and final markdown/HTML report generation passed local validation.

## Full Verify / Machine-Heavy Disposition

- Full local `make verify` was not run by operator direction for this narrow
  main-CI guard lane.
- Local proof is limited to startup governance, focused guard tests,
  `make validate-changed`, `pre-commit run --all-files`, pre-push hooks, and
  Experiment Runner oracle-only evidence.
- Current-head GitHub CI remains required before any merge-readiness claim.

## Current CI / Merge Readiness

- Current-head CI is pending for PR #1878.
- Specifically confirm `test-main (3.11, 60)`, `test-main (3.12, 90)`, and
  `test-main (3.13, 90)` on the latest PR head before merge readiness.
- Strict `check_merge_ready.py --require-auth`, unresolved review-thread checks,
  bot actionable disposition, and the mandatory wait-window remain pending.
- No merge-readiness claim is made by this artifact.
