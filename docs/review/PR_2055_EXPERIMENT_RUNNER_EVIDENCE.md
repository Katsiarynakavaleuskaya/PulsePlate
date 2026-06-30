# PR #2055 Experiment Runner Evidence

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2055

Branch: `codex/fix-main-docker-trivy-acl-attr`

Mode: `oracle_only_governance_reviewer`

Result artifact:
`artifacts/orchestration/experiments/results/pr2055-docker-trivy-acl-attr-oracle-result-network1.json`

## Result

- Status: `accepted`
- Experiment ID: `exp-b3113fa85180`
- Failure class: `null`
- Shared tree untouched: `true`
- Mutated paths: `[]`
- Contribution kind: `fixed_mapping_review`
- Co-author required: `true`
- Co-author reason: Experiment Runner oracle-only evidence shaped PR #2055
  fixed-mapping and merge-readiness closeout.

## Oracle Commands

All oracle commands ran in the Experiment Runner checkout and returned 0:

- `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- `python3 -m pytest -q tests/test_docker_workflow_build_path_contract.py tests/test_trivy_ignore_policy_expiry.py`
- `python3 scripts/orchestration/check_agent_consistency.py`

## Local Runner Disposition

The first strict zero-network attempt was rejected as an infrastructure blocker
because the macOS host did not provide Linux `unshare` on `PATH`. The accepted
run used the repo Experiment Runner with the same oracle-only governance review
intent and left the shared worktree untouched.

## Decision

Use this artifact as PR #2055 Experiment Runner evidence for governance
mapping. It does not replace local gates, current-head CI, role-agent passes,
Codex Security, review-thread disposition, or strict merge readiness.
