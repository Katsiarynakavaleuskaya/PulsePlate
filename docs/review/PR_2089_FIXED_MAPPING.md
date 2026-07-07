# PR #2089 Fixed in Commit Mapping

## Summary

This PR adds a read-only local inventory and retention guard for creative-code
PR-2 / PR-3 artifacts. It remains orchestration/local-artifact only: no product
runtime, OpenAPI/client, iOS/frontend, DB, dependency, workflow, branch-write,
review-thread, fixed-mapping automation, merge, Slack/GitHub authority,
provider, semantic-cache, or graph-truth authority is added.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/51bba2e22975.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Operator override: current `main` monitoring handled by colleague; lane
  continued without treating main CI state as this PR's merge evidence.
- Role order preserved pre-open:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-18a69bccdc52.json`
- Status: accepted
- Mode: `oracle_only_governance_reviewer`
- Oracle: `python -m pytest tests/test_creative_code_artifact_inventory.py tests/test_creative_code_pr_promotion.py tests/test_creative_code_patch_generation.py -q`
- Mutation boundary: `mutated_paths=[]`, `source_diff_applied=true`,
  `shared_tree_untouched=true`
- Co-author: required (`contribution_kind=oracle_review`,
  `coauthor_required=true`)

## Post-Open Review Closure

- QA finding: promotion guard could false-pass when malformed generation or
  promotion receipts produced global read errors but could not be linked to a
  specific accepted patch run.
  - Disposition: FIXED
  - Commit: `12b68cee6`
  - Evidence:
    `scripts/orchestration/creative_code_artifact_inventory.py` now blocks
    `assert-ready-for-promotion` whenever inventory scanning records
    `read_errors`; regression tests cover malformed unlinked generation and
    promotion receipts in `tests/test_creative_code_artifact_inventory.py`.
- QA finding: Phase 2 governance artifact was missing after the initial PR
  open.
  - Disposition: FIXED
  - Evidence: this canonical artifact exists at
    `docs/review/PR_2089_FIXED_MAPPING.md` and the PR body is mirrored from it.
- QA finding: runtime artifact-ref validation was looser than the report schema.
  - Disposition: FIXED
  - Commit: `12b68cee6`
  - Evidence:
    `scripts/orchestration/creative_code_artifact_inventory.py` now uses the
    same closed artifact-ref pattern as the schema; regression coverage rejects
    traversal, empty path segments, hidden unsafe segments, spaces, and
    non-ASCII refs.
- Bug-hunter finding: PR-2 `patch_metadata.json` sidecars could carry
  unsupported or unsafe extra fields while the shared sidecar helper still let
  inventory promotion assertions and PR-3 planning pass.
  - Disposition: FIXED
  - Commit: `130a44a8a`
  - Evidence:
    `scripts/orchestration/creative_code_patch_contract.py` now exact-key
    validates PR-2 patch metadata sidecars, checks `changed_path_statuses`,
    and rejects unsafe metadata before inventory or PR-3 promotion can treat
    the run as valid. Regression tests cover both
    `assert-ready-for-promotion` and PR-3 `plan()` rejection.
- Security-auditor / CodeQL finding: artifact-ref regex contained a redundant
  optional dotted suffix that CodeQL flagged as inefficient backtracking risk.
  - Disposition: FIXED
  - Commit: `0b4ccb79e`
  - Evidence:
    `scripts/orchestration/creative_code_artifact_inventory.py` and
    `docs/orchestration/contracts/creative_code_artifact_inventory_report.v1.schema.json`
    now use the same bounded segment pattern without the nested optional dotted
    suffix.
- Security-auditor finding: `patch_metadata.changed_path_statuses` accepted
  tampered `A` / `M` values when keys matched.
  - Disposition: FIXED
  - Commit: `0b4ccb79e`
  - Evidence:
    `scripts/orchestration/creative_code_patch_contract.py` now derives
    changed-path statuses from `candidate.patch` and rejects sidecar status
    mismatches. Regression tests cover inventory and PR-3 planner rejection.
- Security-auditor / CodeRabbit finding: promotion artifact contract allowed
  `pull_request_number=0` and did not bind `head_branch` to the PR-3
  `experiment/*` branch contract.
  - Disposition: FIXED
  - Commit: `0b4ccb79e`
  - Evidence:
    runtime validation now rejects zero PR numbers and non-`experiment/*`
    branches; the JSON schema mirrors the same constraints.
- CodeRabbit finding: `test_missing_or_tampered_sidecar_fails_closed` used
  `Any` for a callable mutation parameter.
  - Disposition: FIXED
  - Commit: `2c456b995`
  - Evidence:
    `tests/test_creative_code_artifact_inventory.py` now annotates the parameter
    as `Callable[[Path], None]`.
- Codex Security superseded-head finding: unsupported PR-2
  `patch_metadata.json` key names could be echoed in validation errors before
  leak screening.
  - Disposition: FIXED
  - Commit: `a115be6d1`
  - Evidence:
    `scripts/orchestration/creative_code_patch_contract.py` and
    `scripts/orchestration/creative_code_patch_generation.py` now emit generic
    unsupported-field errors without untrusted field names; regression tests
    assert token-shaped key names and `raw_prompt` are not echoed.
- Codex Security superseded-head finding: inventory could mark an accepted
  run eligible when the result was self-consistent but lacked strict runner /
  oracle proof that PR-3 planning would require.
  - Disposition: FIXED
  - Commit: `a115be6d1`
  - Evidence:
    `scripts/orchestration/creative_code_artifact_inventory.py` now validates
    accepted runs with `require_accepted=True` in the shared PR-2 sidecar
    helper; regression coverage rejects accepted results with no oracle proof
    before `assert-ready-for-promotion` can pass.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Current GitHub review-thread actionables queried through GraphQL and mapped
  below. GitHub thread resolution remains pending until the fixed commits are
  pushed and review/bot state is rechecked.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 0b4ccb79ecdb2d8958034c98f67e59343639e174
Evidence: `docs/orchestration/contracts/creative_code_artifact_inventory_report.v1.schema.json` now requires `pull_request_number >= 1`; runtime validation also rejects zero PR numbers.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2089#discussion_r3532026922 -> 0b4ccb79ecdb2d8958034c98f67e59343639e174

Disposition: FIXED
Commit: 2c456b9958c6d451f28daf11cbb03cfb3bb715c8
Evidence: `tests/test_creative_code_artifact_inventory.py` now uses `Callable[[Path], None]` for the mutation callback parameter.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2089#discussion_r3532026935 -> 2c456b9958c6d451f28daf11cbb03cfb3bb715c8

Disposition: FIXED
Commit: 0b4ccb79ecdb2d8958034c98f67e59343639e174
Evidence: `scripts/orchestration/creative_code_artifact_inventory.py` and the inventory schema now use the bounded artifact-ref regex without the redundant optional dotted suffix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2089#discussion_r3533153971 -> 0b4ccb79ecdb2d8958034c98f67e59343639e174

Disposition: FIXED
Commit: 0b4ccb79ecdb2d8958034c98f67e59343639e174
Evidence: `scripts/orchestration/creative_code_patch_contract.py` now derives statuses from `candidate.patch` and rejects `patch_metadata.changed_path_statuses` mismatches.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2089#discussion_r3533209774 -> 0b4ccb79ecdb2d8958034c98f67e59343639e174

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python -m pytest tests/test_creative_code_artifact_inventory.py tests/test_creative_code_pr_promotion.py tests/test_creative_code_patch_generation.py -q` - PASS
- `make validate-changed` - PASS
- `pre-commit run --all-files` - PASS
- Initial `git push` pre-push hooks - PASS except MyPy, which found typed
  return/member issues in the new inventory/promoter code; fixed before push.
- `pre-commit run --hook-stage pre-push mypy` - PASS after the type fix.
- `git push` pre-push hooks - PASS after the type fix, including MyPy changed
  files, pip-audit, backend pre-push tests, full-repo Bandit, and docker build
  test.
- `python3 -m scripts.orchestration.creative_code_artifact_inventory status --format text` - PASS on this worktree with empty local creative-code artifacts.
- Post-QA/bug-hunter focused rerun:
  `python -m pytest tests/test_creative_code_artifact_inventory.py tests/test_creative_code_pr_promotion.py tests/test_creative_code_patch_generation.py -q` - PASS.
- Post-QA/bug-hunter `make validate-changed` - PASS.
- Post-QA/bug-hunter `pre-commit run --all-files` - PASS.
- Post-security focused rerun:
  `python -m pytest tests/test_creative_code_artifact_inventory.py tests/test_creative_code_pr_promotion.py tests/test_creative_code_patch_generation.py -q` - PASS.
- Post-security `python3 scripts/orchestration/check_preflight.py` - PASS.
- Post-security `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- Post-security `make validate-changed` - PASS.
- Post-security `pre-commit run --all-files` - PASS.
- Post-review typing fix:
  `python -m pytest tests/test_creative_code_artifact_inventory.py -q` - PASS.
- Post-review typing fix `make validate-changed` - PASS.
- Post-review typing fix `pre-commit run --all-files` - PASS.
- Post-Codex-Security-fix focused rerun:
  `python -m pytest tests/test_creative_code_artifact_inventory.py tests/test_creative_code_pr_promotion.py tests/test_creative_code_patch_generation.py -q` - PASS.
- Post-Codex-Security-fix `python3 scripts/orchestration/check_preflight.py` - PASS.
- Post-Codex-Security-fix `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- Post-Codex-Security-fix `make validate-changed` - PASS.
- Post-Codex-Security-fix `pre-commit run --all-files` - PASS.

## Merge Readiness

- [ ] Current-head GitHub CI terminal success confirmed after this artifact
  commit.
- [ ] Required post-open role sequence complete after all review fixes.
- [ ] Codex Security diff scan / finding discovery complete on current head.
- [ ] `pulseplate-pr-review` complete on current head.
- [ ] Strict review-thread disposition passes with auth.
- [ ] Strict merge-readiness guard passes with auth.
- [ ] Mandatory wait-window after latest bot/review activity completed.

## Deferred / Follow-ups

- PR-3 promotion remains separate and out of scope for this PR.
- After merge, restore or rerun PR-2 generation/evaluation and retain the
  resulting accepted `patch_runs/<run-id>` artifact before any PR-3 lane.
