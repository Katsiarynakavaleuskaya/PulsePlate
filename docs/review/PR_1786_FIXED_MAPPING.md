# PR #1786 Fixed in Commit Mapping

## Scope

This PR hardens Phase2 PR-body gate commit-range handling so option-like
inputs fail closed while valid git revision ranges still drive Experiment
Runner co-author diagnostics.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Review comments were inspected after PR open and before thread resolution.
- Mapping updates follow the code/test fix commit.
- New review comments must be dispositioned as `FIXED`, `NOT-A-BUG`, or
  `DEFERRED` before resolution.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1786#discussion_r3279667137 -> 1f25e18a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1786#discussion_r3279667139 -> 1f25e18a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1786#pullrequestreview-4335178706 -> 1f25e18a5
Disposition: FIXED
Commit: 1f25e18a5
Evidence: `scripts/ci/check_pr_body_phase2_gates.py` uses `--end-of-options` before the revision/range, and `tests/test_pr_body_phase2_gates.py` asserts exact argv ordering plus direct and argparse validator coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1786#pullrequestreview-4335150463
Disposition: NOT-A-BUG
Evidence: Sourcery reported a weekly rate-limit notice only and did not provide actionable code findings for this PR.
Reason: No code, test, security, or governance change was requested by this review.

## Implementation Evidence

- Commit: `1f25e18a5`
- Evidence:
  - `scripts/ci/check_pr_body_phase2_gates.py` rejects option-like
    `--commit-range` and `--commit-range-fallback` values before invoking git.
  - `_git_commit_messages` calls git without a shell, with an absolute git
    binary, `--end-of-options`, the validated revision/range, and a trailing
    pathspec separator.
  - `tests/test_pr_body_phase2_gates.py` covers fallback behavior, no-fallback
    behavior, exact git argv ordering, valid input, direct invalid input, and
    argparse invalid-input wiring.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-da9fceb8f915.json

The accepted oracle-only governance reviewer result records `mutated_paths: []`,
`promotion_ready: false`, `contribution_kind: commit_decision`, and
`coauthor_required: true`. It was advisory evidence only and did not mutate
`scripts/ci/**`.

## Premortem / Role Findings

| Finding | Disposition | Evidence |
| --- | --- | --- |
| Bare `--` before the revision makes git treat the range as a pathspec and can silently return empty commit messages. | FIXED | Commit `1f25e18a5` uses `--end-of-options` before the validated revision/range. |
| The new regression test only asserted separator presence and would not catch the broken argv order. | FIXED | Commit `1f25e18a5` asserts the exact safe argv tail. |
| Validator coverage proved only the direct failure path, not success or argparse wiring. | FIXED | Commit `1f25e18a5` adds valid-input and argparse invalid-input tests. |
| Missing canonical mapping artifact blocked Phase2 and merge-readiness gates. | FIXED | This artifact records dispositions and proof for the actionable review comments. |

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review`
- `.venv/bin/python -m pytest -q tests/test_pr_body_phase2_gates.py -k "git_commit_messages or commit_range_arg"`
- `.venv/bin/python -m pytest -q tests/test_pr_body_phase2_gates.py`
- `.venv/bin/flake8 scripts/ci/check_pr_body_phase2_gates.py tests/test_pr_body_phase2_gates.py`
- `git diff --check`
- Experiment Runner oracle-only result:
  `artifacts/orchestration/experiments/results/exp-da9fceb8f915.json`

## Merge Readiness

Not claimed. Current-head CI, strict review-thread disposition, PR body mirror,
and merge-readiness checks are still required before merge.
