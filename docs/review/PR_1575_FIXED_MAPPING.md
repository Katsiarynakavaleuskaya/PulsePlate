# PR 1575 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575
- Branch: `codex/evidence-graph-runtime-umbrella`
- Scope: PR-E0 docs/governance umbrella for Evidence Graph Runtime

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e7acb7bbe
Evidence: `docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md:1`
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:1942`
Evidence: `AGENTS.md:349`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575 -> e7acb7bbe

Disposition: FIXED
Commit: 64e5e401c
Evidence: `docs/review/PR_1575_FIXED_MAPPING.md` validation evidence now includes exit-code and stdout snippets for the local narrow gates.
Evidence: `docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md` now cites rail/source-of-truth evidence, marks the asset baseline as PR-E1+ proposed contract fields, links PR-E1..PR-E5 to the canonical ledger owner, adds Done-when criteria, cites the semantic-cache gate, tightens the validation search, and removes unverifiable operator backstory.
Evidence: `AGENTS.md` now points the Evidence Graph Runtime invariant to the canonical semantic-cache gate document.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575#pullrequestreview-4198010257 -> 64e5e401c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575#discussion_r3161965676 -> 64e5e401c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575#discussion_r3161965688 -> 64e5e401c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575#discussion_r3161965694 -> 64e5e401c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575#pullrequestreview-4198122665 -> 64e5e401c

Disposition: FIXED
Commit: 2dd05ef20
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now adds `Remove-by: 2026-06-30` to `ledger-p1-evidence-graph-runtime`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575#discussion_r3163775471 -> 2dd05ef20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1575#pullrequestreview-4200263134 -> 2dd05ef20

## Validation Evidence

Disposition: NOT-A-BUG
Evidence: Final rebased local narrow gates passed before draft PR creation:
`python3 scripts/orchestration/check_preflight.py` (exit code 0; stdout:
`PASS: All required SoT files present`; `PASS: worktrees/ not tracked`).
`python3 scripts/orchestration/check_agent_consistency.py` (exit code 0;
stdout: `OK: agent docs and files are consistent.`).
`rg -n "Evidence Graph Runtime|semantic cache|Rail A|Rail B1|Rail B2"` against
`AGENTS.md`, `docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md`, and
`docs/roadmap/BACKLOG_LEDGER.md` (exit code 0; expected anchors present).
`pre-commit run --all-files` (exit code 0; stdout included `Passed` for yaml,
secrets, cache, workflow, lint/security, frontend/backend, and iOS hooks).
`make validate-min` (exit code 0; stdout: `tests/test_repo_policy_guards.py:
14 passed`; `test-fast: passed`).
Evidence: Post-open full `make verify` passed before later clean trunk rebases, including verify-env, flake8, mypy, smoke tests, full pytest under coverage, coverage XML, and diff-cover; current-head CI remains the final post-rebase heavy signal.
Reason: PR-E0 is docs/governance only and intentionally does not change runtime code, public API, DB schema, OpenAPI, billing, providers, semantic cache, GraphRAG, or user-facing behavior.

## Deferred / Follow-ups

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-evidence-graph-runtime`
Reason: PR-E1/E2/E3/E4/E5 are intentionally separate downstream slices after the umbrella merges.

Disposition: DEFERRED
Backlog: `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
Reason: Semantic cache remains blocked until evidence asset lineage, replay-safe promotion, and metadata admission gates exist and a dedicated semantic-cache gate explicitly opens.

## Merge Readiness Notes

- This PR is draft until current-head PR CI, post-open review, bot review disposition, and strict merge-readiness checks complete.
- No merge-ready claim is made by this mapping artifact; the checked Phase 2 boxes only confirm that the PR body/mapping artifact contract has been populated.
- Local full `make verify` passed before the latest clean trunk rebase; current-head CI and strict merge readiness remain the final merge gates.
