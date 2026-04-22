# PR #1495 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `app/services/insight_runtime.py:123-191` declares `generate_traced_insight(...)` with a leading `*`, so all arguments are keyword-only and positional-call drift is impossible. The added `rollout_policy` parameter does not change positional compatibility because there is no positional call surface to preserve. The broader suggestion to hard-fail mixed `rollout_policy` plus legacy bool inputs is advisory future tightening, not a correctness blocker for this first-cut compatibility slice.
Reason: The reported “parameter reordering” breakage cannot occur on the live function signature, and the remaining high-level guidance does not identify a current behavioral regression in this bounded PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1495#discussion_r3123746307
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1495#pullrequestreview-4154439968

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophical-logic`
Reason: `PR-A6 W1` intentionally preserves legacy `philosophy_*` bool compatibility while making `PhilosophyRolloutPolicy` the prepared-runtime authority. The canonical in-repo app path passes only `rollout_policy`, so there is no live dual-authority bug on the shipped W1 path. A correct mixed-input conflict guard or deprecation wrapper requires a follow-up compatibility slice that can distinguish omitted legacy bools from explicitly conflicting values without widening W1.
Evidence: `docs/orchestration/WAVE6_A6_PHILOSOPHICAL_ROLLOUT_W1_PACKET_2026-04-22.md:133-139`; `app/services/insight_application_service.py:143-157`; `app/services/insight_runtime.py:123-142`; `core/insight/philosophical_runtime.py:386-415`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1495#pullrequestreview-4154591459

Disposition: FIXED
Commit: dd1035347
Evidence: `tests/test_insight_application_service.py` now pins the philosophy feature-flag readers in the prepare-kwargs assertion path, `core/insight/philosophical_runtime.py` exports `PhilosophyRolloutPolicy` via `__all__`, and `docs/orchestration/WAVE6_A6_TASK_ANALYSIS_2026-04-22.md` applies the requested wording cleanup without changing scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1495#pullrequestreview-4154609821

Disposition: NOT-A-BUG
Evidence: `PhilosophyRolloutPolicy.preview_router_enabled` is `router_enabled || linguistic_enabled`, while `public_metadata_enabled` is `any(router_enabled, phase12_enabled, linguistic_enabled, pragmatic_enabled)`, so every live path that can reach `_build_direct_result(...)` already implies public metadata is enabled. When metadata is disabled, `preview_route(...)` falls back to `DEEP_REASONING` and never reaches the direct SAFE_WELLNESS_DISCLAIMER / local direct-answer helper path. The helper docstring now states this invariant explicitly.
Reason: The reported metadata-bypass scenario is unreachable on the live W1 contract; direct-result paths do not bypass rollout metadata policy because they require preview-router activation first.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1495#pullrequestreview-4155227251

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [x] Current-head CI is green for PR branch head
  Evidence: `gh pr checks 1495` is fully green on head `99710dfd035f7cc182ba62ffde15f92e83ab89cb`, including `Merge readiness gate`, `coverage-pr`, `diff-coverage`, `lint`, `security`, and `test-pr (3.13)`.
- [x] Required checks complete (no pending jobs)
  Evidence: current-head required jobs are complete; the remaining entries are non-blocking `skipping` lanes only.
- [x] All review threads resolved on GitHub after disposition updates
  Evidence: `gh api graphql ... reviewThreads` returns only resolved threads for `PR #1495`, including the Sourcery inline thread `#discussion_r3123746307`.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: the actionable Sourcery and CodeRabbit review shells are mapped above, and `gh pr view 1495 --json latestReviews` shows no newer unmapped review after `#pullrequestreview-4154609821`.
- [x] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed on the merge-ready branch state before this artifact refresh commit.
- [x] `make verify` green on latest pushed head
  Evidence: `make verify` passed on the merge-ready branch state before this artifact refresh commit.
