# PR #1506 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the draft PR is opened per repo
governance. Record every actionable human/bot disposition here before resolving
threads on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: `19537b47f207e3b9dab7c47dd68169bc0034d3b1`
Evidence: `core/ai/insight_runtime.py` now uses `decision.needs_rag`
directly when available with a narrow route fallback;
`core/rag/recursive_retrieval.py` documents why explicit hint caps stop before
preparing an unused refined query; `tests/test_rag_orchestration.py` documents
why the CI-surface depth-cap anchor intentionally complements the
recursive-unit test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1506#pullrequestreview-4163433365 -> 19537b47f207e3b9dab7c47dd68169bc0034d3b1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1506#discussion_r3131650729 -> 19537b47f207e3b9dab7c47dd68169bc0034d3b1

## Initial Implementation Commits

- `cce682990` - `feat(ai-runtime): add recursive speed hints`
- `ded2c006f` - `docs(pr): add PR 1506 mapping`
- `19537b47f` - `fix(ai-runtime): address recursive speed review`

## Merge Readiness

Merge-readiness contract:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] After latest bot/review activity, perform a final check and wait at least
      one review cycle before merging
- [x] `pre-commit run --all-files` green on latest local head
      Local proof: passed before commit `19537b47f`.
- [ ] `make verify` green on latest pushed head
      Local proof: `make verify` passed `verify-env`, `lint`, `typecheck`, and
      `test-fast`, then was manually stopped during the long full
      coverage/diff-cover sweep. Do not mark merge-ready until this is
      completed or replaced by accepted current-head required CI evidence.
