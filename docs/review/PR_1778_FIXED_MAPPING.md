<!-- markdownlint-disable MD034 -->
# PR #1778 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

- [x] Discussion-thread pass completed
- [x] Initial fixed mapping artifact created after PR number assignment
- [x] Fixed in commit mapping completed

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-688b8c58034a.json

The local oracle-only result artifact is intentionally gitignored. It records
`status=accepted`, `runner_mode=oracle_only_governance_reviewer`,
`mutated_paths=[]`, `promotion_ready=false`, `contribution_kind=oracle_review`,
and `coauthor_required=true`. Commit `9f07c9535` includes the canonical
Experiment Runner co-author trailer.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: f8fae1973
Evidence: `scripts/orchestration/experiment_contract.py`, `scripts/orchestration/experiment_runner.py`, `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_experiment_runner.py`, `tests/test_pr_body_phase2_gates.py`
Reason: Sourcery flagged duplicated contribution/co-author invariants and a fixed `origin/main..HEAD` advisory range. The invariant now lives in `validate_contribution_attribution(...)` and is reused by the runner and result validator; Phase2 accepts `--commit-range` for local advisory diagnostics. The same follow-up also closes the post-open bug-hunter false-green finding by warning when a referenced local Experiment Runner artifact is unavailable and the commit range lacks the canonical trailer.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274150100 -> f8fae1973
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#pullrequestreview-4328739221 -> f8fae1973

## Post-Open Review Queue

Initial coordinator, architecture, cursor-specialist, security-auditor,
qa-engineer-agent, and bug-hunter passes are complete. Any later actionable bot
or human review must be fixed or dispositioned here before merge readiness is
claimed.

## Merge Readiness

Not claimed. Current-head CI, bot-review disposition, strict merge-readiness
checks, and the required wait-window remain pending.
<!-- markdownlint-enable MD034 -->
