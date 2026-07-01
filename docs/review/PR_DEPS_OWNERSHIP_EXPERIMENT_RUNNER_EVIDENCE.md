# Dependency Ownership Experiment Runner Evidence

Branch: `codex/deps-ownership-pyarrow-cleanup`

Mode: `oracle_only_governance_reviewer`

## Zero-Network Attempt

- Experiment ID: `exp-732a3a092f3a`
- Result artifact: `artifacts/orchestration/experiments/results/exp-732a3a092f3a.json`
- Status: `rejected`
- Failure class: `infra_flake`
- Runner error: `Network-disabled sandbox requires unshare on PATH`
- Oracle commands executed: `0`

Disposition: local infrastructure blocker. The macOS host does not provide Linux `unshare`, so the zero-network sandbox could not execute any oracle command.

## Review-Required Fallback

- Experiment ID: `exp-7bcba836ae3b`
- Result artifact: `artifacts/orchestration/experiments/results/exp-7bcba836ae3b.json`
- Status: `accepted`
- Failure class: `null`
- Runner mode: `oracle_only_governance_reviewer`
- Network budget: `1`
- Shared tree untouched: `true`
- Contribution kind: `oracle_review`
- Co-author required: `true`

The accepted fallback used the same oracle-only governance intent and an explicit nonzero network budget to avoid the local `unshare` blocker. It is review-required evidence and does not replace local gates, current-head CI, post-open role passes, Codex Security, `pulseplate-pr-review`, or merge-readiness checks.

## Oracle Commands

All fallback oracle commands returned `0`:

- `python3 scripts/ci/check_python_dependency_surfaces.py`
- `python3 verify_requirements.py`
- `python3 -m pytest -q tests/test_python_dependency_surfaces.py tests/test_python_supply_chain_controls.py`

## Decision

Use `exp-7bcba836ae3b` as the pre-open Experiment Runner oracle-only evidence for this PR, with the local zero-network infra limitation disclosed.
