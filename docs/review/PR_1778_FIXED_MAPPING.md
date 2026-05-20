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

Disposition: FIXED
Commit: b5f97d430
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: Codex flagged that Experiment Runner co-author diagnostics were still too broad around `Not applicable` evidence, artifact mentions outside the canonical evidence section, artifacts requiring co-author verification, and missing local artifacts. Phase2 now scopes artifact scanning to `## Experiment Runner Evidence`, emits no broad warning when no artifact is referenced, checks commit messages only for artifacts with `coauthor_required: true`, and still warns when a referenced artifact is unavailable even if a canonical trailer is present.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274554204 -> b5f97d430
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274554211 -> b5f97d430
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274554222 -> b5f97d430
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274554228 -> b5f97d430

Disposition: FIXED
Commit: f36f266db
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: Codex flagged that readable but schema-invalid Experiment Runner artifacts could silently bypass co-author diagnostics. Phase2 now validates artifact contribution/co-author metadata through the shared Experiment Runner contract and emits an advisory warning when the payload is non-object or malformed, including invalid `coauthor_required` values.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3274733388 -> f36f266db

Disposition: FIXED
Commit: 6027b1f31
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: CodeRabbit flagged that referenced Experiment Runner artifact reads followed symlinks and could escape the repository root. Phase2 now resolves the candidate path, verifies it remains under the resolved repo root before reading, and emits the existing unverifiable-artifact advisory for missing, escaping, unreadable, or non-file paths.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#pullrequestreview-4329418077 -> 6027b1f31

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1778_FIXED_MAPPING.md`
Reason: CodeRabbit's later review was a low-value prose nit about using `co-author` in human-readable mapping text while preserving code field identifiers such as `coauthor_required`. The mapping text now follows that convention; no product or governance behavior change was required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#pullrequestreview-4329507361

Disposition: FIXED
Commit: 0d8d187ae
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: CodeRabbit flagged that `Path.resolve(strict=True)` can raise `RuntimeError` on symlink loops. Phase2 now treats symlink-loop resolution failures as unverifiable Experiment Runner artifacts and emits the advisory warning instead of crashing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3275018977 -> 0d8d187ae
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#pullrequestreview-4329738482 -> 0d8d187ae

Disposition: FIXED
Commit: fd94d2c25
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: Codex flagged two Phase2 advisory false-signal paths: artifact-first mode still inspected non-authoritative PR body Experiment Runner evidence, and co-author trailer checks used raw substring matching. Phase2 now uses the canonical mapping artifact for Experiment Runner evidence when `--pr-number` is present and matches the canonical co-author line only inside commit trailer blocks.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3275163925 -> fd94d2c25
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3275163929 -> fd94d2c25

Disposition: FIXED
Commit: 50836edcd
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: Codex flagged that a local footer scan still accepted prose ending in a trailer-looking line. Phase2 now delegates trailer parsing to `git interpret-trailers --parse`, so only real Git trailer blocks satisfy the Experiment Runner co-author diagnostic.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3276881473 -> 50836edcd

Disposition: FIXED
Commit: e1f2fde6f
Evidence: `scripts/ci/check_pr_body_phase2_gates.py`, `tests/test_pr_body_phase2_gates.py`
Reason: Codex flagged that raw commit-message text from `git log %B` can contain divider-like `---` lines that `git interpret-trailers` treats as end-of-input by default. Phase2 now passes `--no-divider` and keeps trailer parsing accurate for raw commit bodies.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1778#discussion_r3277019165 -> e1f2fde6f

## Post-Open Review Queue

Initial coordinator, architecture, cursor-specialist, security-auditor,
qa-engineer-agent, and bug-hunter passes are complete. Any later actionable bot
or human review must be fixed or dispositioned here before merge readiness is
claimed.

## Merge Readiness

Not claimed. Current-head CI, bot-review disposition, strict merge-readiness
checks, and the required wait-window remain pending.
<!-- markdownlint-enable MD034 -->
