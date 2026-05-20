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

Disposition: FIXED
Commit: 834539b23
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: Codex review flagged that a missing `origin/main..HEAD` range could silently degrade the co-author advisory into false warnings. Phase2 now accepts `--commit-range-fallback` and falls back to `HEAD` when the primary range is unavailable, with a regression test for the fallback path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274168917 -> 834539b23

Disposition: FIXED
Commit: 87224a955
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `scripts/orchestration/check_experiment_runner_identity.py`, `scripts/orchestration/render_codex_start_prompt.py`, `tests/test_pr_body_phase2_gates.py`, `tests/test_experiment_runner_identity_policy.py`, `tests/test_render_codex_start_prompt.py`
Reason: CodeRabbit flagged three valid review-governance issues: unverifiable local commit inspection was indistinguishable from a missing trailer, identity-policy exemptions allowed unexpected no-trailer cases, and starter prompts did not spell out the exact accepted `Artifact:` line. The guard now returns `None` when branch commits cannot be inspected and emits an unverifiable advisory, the identity checker requires an exact exemption set, and starter prompts require `Artifact: artifacts/orchestration/experiments/results/<id>.json`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274283459 -> 87224a955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274283479 -> 87224a955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274283491 -> 87224a955
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#pullrequestreview-4328897612 -> 87224a955

Disposition: FIXED
Commit: cc1fa47d2
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: CodeRabbit flagged that the default `HEAD` fallback could scan unrelated reachable history and hide missing Experiment Runner trailers. The Phase2 helper now leaves the fallback empty by default, scopes unverifiable commit-message warnings to artifacts that actually require co-author verification, and keeps explicit fallback ranges available only for operator-controlled local diagnostics.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274302534 -> cc1fa47d2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#pullrequestreview-4329061597 -> cc1fa47d2

## Post-Open Review Queue

Initial coordinator, architecture, cursor-specialist, security-auditor,
qa-engineer-agent, and bug-hunter passes are complete. Any later actionable bot
or human review must be fixed or dispositioned here before merge readiness is
claimed.

## Merge Readiness

Not claimed. Current-head CI, bot-review disposition, strict merge-readiness
checks, and the required wait-window remain pending.
<!-- markdownlint-enable MD034 -->
