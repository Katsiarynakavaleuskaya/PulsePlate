# PR #1775 - Fixed in Commit Mapping

## Scope

Experiment Runner PR participation advisory gate and threat-model-only bootstrap for
future validator-script mutation access.

## Implementation Commits

- `741b20708` - `chore(orchestration): add experiment runner PR evidence gate`

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-65d109111b8a.json

Local oracle-only artifact, gitignored and not committed. Runner mode:
`oracle_only_governance_reviewer`; `mutated_paths: []`; `promotion_ready: false`.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path <changed paths>` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/check_experiment_runner_identity.py` - PASS
- `python3 -m pytest -q tests/test_render_codex_start_prompt.py tests/test_local_session_bootstrap.py tests/test_pr_body_phase2_gates.py tests/test_start_pr_lane.py tests/test_experiment_runner.py tests/test_experiment_runner_identity_policy.py tests/test_orchestration_merge_ready.py` - PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS
- `PATH=.venv/bin:$PATH PRE_COMMIT_HOME=/tmp/pulseplate-precommit-experiment-runner-gate pre-commit run --all-files` - PASS
- Pre-push hook - PASS: changed-file mypy, pip-audit, backend pytest, full-repo Bandit, docker build test

## Role Review

- agent-coordinator: PASS - scope kept to governance/tooling, advisory evidence, and fail-closed mutation boundary.
- architecture-specialist: FIXED - starter prompt now separates requested role seed from the default PR review checklist.
- security-auditor: FIXED - governed identity policy requires `scripts/ci/` as a forbidden runner mutation surface.
- qa-engineer-agent: FIXED - starter prompt tests cover coordinator-first repo commands and non-draft default.
- bug-hunter: NOT-A-BUG - Experiment Runner evidence may be supplied by PR body or fixed-mapping artifact per approved Phase2 advisory contract.
- dev-operator: PASS - branch push and non-draft PR open path verified.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1775#pullrequestreview-4327750134 -> 1b2db1285
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1775#discussion_r3273330030 -> 1b2db1285
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1775#discussion_r3273330040 -> 1b2db1285
Disposition: FIXED
Commit: 1b2db1285
Evidence: scripts/ci/check_pr_body_phase2_gates.py routes Experiment Runner advisory warnings through checker results and reuses a shared markdown section extractor.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1775#pullrequestreview-4327886137 -> 8a4a1922d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1775#discussion_r3273437604 -> 8a4a1922d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1775#pullrequestreview-4327924616 -> 8a4a1922d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1775#discussion_r3273469191 -> 8a4a1922d
Disposition: FIXED
Commit: 8a4a1922d
Evidence: scripts/ci/check_pr_body_phase2_gates.py:136 stops mapping extraction before sibling h3 sections; tests/test_pr_body_phase2_gates.py:120 validates that sibling h3 content is not parsed as mapping. docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:67 clarifies advisory evidence wording. docs/review/PR_1775_FIXED_MAPPING.md:24 uses portable validation command paths. Validation: `python3 -m pytest -q tests/test_pr_body_phase2_gates.py` -> PASS.

## Deferred / Follow-ups

- Later PR: hard merge gate requiring Experiment Runner evidence for every non-trivial PR after advisory signal proves stable. Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-experiment-runner-pr-evidence-hard-gate
- Later PR: controlled validator-script mutation access threat model with allowlist, forbidden-surface tests, identity checks, and rollback notes. Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-experiment-runner-validator-mutation-threat-model

## Merge Readiness

Not claimed. Current-head PR CI, bot review, post-open review-thread disposition,
wait-window, and strict merge wrapper remain required before merge readiness.
