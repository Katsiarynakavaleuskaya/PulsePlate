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

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- No GitHub review-thread actionables were mapped at artifact creation time.

## Fixed in Commit Mapping

- No actionable review comments

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
