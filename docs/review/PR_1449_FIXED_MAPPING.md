<!-- markdownlint-disable MD034 -->
# PR 1449 — Fixed in Commit Mapping

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-57`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-112`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This stale-branch recovery lane rebased the old router-level fix onto current
`main`, re-landed the runtime fix on the live `fitchef_runtime` seam, and maps
all current bot review surfaces before any merge-readiness claim.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1449#pullrequestreview-4131516546 -> 0bb4b3f4e30ea89c375d076e17d2b68cf2cd9ec9
Disposition: FIXED
Commit: 0bb4b3f4e30ea89c375d076e17d2b68cf2cd9ec9
Evidence: `app/services/fitchef_runtime.py:113-140`; `app/services/fitchef_runtime.py:873-884`; `tests/test_cbt_insight_api.py:896-975`; `tests/test_cbt_insight_api.py:1182-1230`
Reason: Sourcery requested a single timeout wrapper and support for providers whose sync `generate()` returns a coroutine. The recovery commit moved that fix onto the live runtime seam by factoring provider dispatch into `_await_provider_generate()` / `_generate_with_timeout()` and adding route-level regression tests for async providers, sync providers, sync providers returning coroutine objects, and real timeout coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1449#pullrequestreview-4131514505
Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1449#pullrequestreview-4131514505`
Reason: cubic found no issues in its review shell. It does not add a separate actionable delta once the live runtime fix and regression tests above are present.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1449#issuecomment-4270677375
Disposition: NOT-A-BUG
Evidence: `tests/test_cbt_insight_api.py:896-975`; `tests/test_cbt_insight_api.py:1182-1230`
Reason: The CodeRabbit issue comment is a rate-limit shell plus beta finishing-touch checkboxes, not a concrete correctness defect on the current head. The current branch already includes the requested unit coverage in the committed runtime/test fix, so no separate follow-up is required for this shell comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1449#issuecomment-4270679742
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1449_FIXED_MAPPING.md`
Reason: The Sourcery review-guide issue comment is informational documentation for reviewers and mirrors the stale router-level shape of the original PR. It does not introduce a separate actionable requirement beyond the concrete Sourcery review already fixed above.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:31-45`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: remote PR head is still stale until the rebased branch is force-pushed.
- [ ] Required checks complete (no pending jobs)
  Evidence: remote PR head is still stale until the rebased branch is force-pushed.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: GraphQL currently reports zero review threads, but final re-check is still required after push.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: this artifact now maps the live bot review surfaces; strict wrapper re-check is still pending.
- [x] Pre-commit green on latest local head
  Evidence: `pre-commit run --all-files` passed before commit `0bb4b3f4e30ea89c375d076e17d2b68cf2cd9ec9`.
- [ ] `make verify` green on latest local head
  Evidence: `make verify` reached `diff-cov` after passing `verify-env`, `lint`, `typecheck`, and `test-fast`, but the host terminated the full coverage rebuild with `make: *** [diff-cov] Terminated: 15`; rerun on the committed branch head remains required.
<!-- markdownlint-enable MD034 -->
