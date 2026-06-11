# PR #1954 Fixed in Commit Mapping

## Scope

This PR locks the legacy compatibility seam and local artifact validation
boundary with documentation, fail-closed static guards, and deterministic tests.
It does not change runtime behavior, OpenAPI/client contracts,
semantic-cache serving, FoodDB cutover policy, provider/LLM paths, auth,
entitlement, billing, or broad architecture ownership.

## Lane Start Provenance

- Packet: artifacts/orchestration/task_packets/9dfc444f9c68.json
- Starter: scripts/orchestration/start_pr_lane.sh
- Branch: `codex/legacy-seam-artifact-validation-boundary`
- Worktree: `worktrees/legacy-seam-artifact-validation-boundary`
- Base: `origin/main`
- Operator override: lane start was explicitly approved while current-head
  `main` CI was pending. This is a start override only, not a
  merge-readiness override.
- Declared pre-open role order:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> cursor-specialist-agent -> web-research-agent`
- Dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/9dfc444f9c68.json --mode runtime --implementation-owner qa-engineer-agent --implementation-owner security-auditor --pretty`
- Dispatch result: every declared pre-open role pass completed before
  implementation/push.
- Mandatory post-open role order:
  `qa-engineer-agent -> bug-hunter -> security-auditor`, then Codex Security
  diff scan / finding discovery, then `pulseplate-pr-review`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Review threads: none resolved by this artifact at PR open.
- Bot reviews/actionables: pending post-open review cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

- `49dff74637a247cdfdb2930ee6be6ca0c8b80747` - documents the accepted
  legacy compatibility seam and artifact validation boundary, adds
  fail-closed AST guards for `legacy_app.py` growth and runtime local artifact
  reads, and covers both guard contracts with deterministic tests.
- This commit includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because
  the accepted oracle-only Experiment Runner result shaped the commit decision.

## Premortem Evidence

- Skill: `pulseplate-premortem-risk-review`
- Mode: `pr-premortem`
- Artifact: `artifacts/orchestration/premortem/legacy-seam-artifact-validation-boundary-premortem.md`
- Decision: proceed with changes.
- Closure: findings are closed by the current docs, static guards,
  deterministic tests, semantic-cache gate evidence, and the explicit
  pending-main merge-readiness block.
- Closed risks: legacy guard false-green, runtime artifact back door, scope
  drift into runtime/semantic-cache/FoodDB behavior, and confusing a pending
  main start override with merge readiness.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-ef7d993bc3c7.json

- Mode: `oracle_only_governance_reviewer`
- Packet: `artifacts/orchestration/experiments/exp-ef7d993bc3c7.json`
- Result: `artifacts/orchestration/experiments/results/exp-ef7d993bc3c7.json`
- Status: accepted.
- Evidence: `mutated_paths=[]`, `shared_tree_untouched=true`,
  `source_diff_applied=true`, and 4/4 configured oracles returned `0`.
- Attribution: commit `49dff74637a247cdfdb2930ee6be6ca0c8b80747` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because
  the oracle review shaped validation and the commit decision.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 24 tests.
- `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- `.venv/bin/python scripts/ci/check_semantic_cache_gate.py` - PASS; all
  semantic-cache contracts remain closed.
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS after rebase; selected
  `tests/test_artifact_validation_boundary.py tests/test_legacy_growth_guard.py`.
- `pre-commit run --all-files` - PASS after rebase.
- Push pre-hook - PASS: mypy changed files, pip-audit, backend pre-push pytest,
  full-repo Bandit, and Docker build test.

## Current Main / Merge Readiness

- Current `origin/main` at PR open:
  `1090ae112b87a13448e71961d2ee582c1ef6b23e`.
- Main CI at PR open: `CI` run `27375084223` was still `in_progress`.
- Merge readiness remains blocked until current-head `main` is healthy, this
  PR's current-head CI is healthy, all review/bot actionables are dispositioned,
  this mapping artifact and the PR body mirror are current, strict
  merge-readiness passes, and the wait-window elapses.

## Post-open Role Findings

- `qa-engineer-agent`: pending.
- `bug-hunter`: pending.
- `security-auditor`: pending.
- Codex Security diff scan / finding discovery: pending.
- `pulseplate-pr-review`: pending.
