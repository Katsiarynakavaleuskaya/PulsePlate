# PR #1484 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is the source of truth for review dispositions on PR #1484.
Record every actionable human or bot review item here before resolving threads or
claiming merge readiness.

## Fixed in Commit Mapping

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane`
Reason: Sourcery's high-level request to split the runner into smaller modules
and fully deduplicate notebook/runner logic is valid follow-up architecture work,
but widening this PR beyond the bounded release-gates lane would violate the
approved packet scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139606616

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139611496`
Reason: The Codex connector review entry is only the review-shell notice for the
integration and does not introduce separate inline actionables beyond the items
already dispositioned elsewhere in this artifact.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139611496

Disposition: FIXED
Commit: `f9e730981`
Evidence: `.github/workflows/rag-release-gates.yml:36-54,84-96`;
`docs/roadmap/BACKLOG_LEDGER.md:1639-1667`;
`notebooks/pulseplate_rag_release_gates.ipynb`;
`scripts/evals/run_rag_release_gates.py:1788-1800`;
`tests/test_rag_release_gates_runner.py:520-706`
Reason: The aggregate CodeRabbit review shell is now satisfied by the
post-review fix series: weekly/manual dataset injection, explicit smoke timeout
and dependency install, tighter ledger seam governance, emitted-artifact notebook
parity coverage, notebook `TOP_K` / overlap corrections, notebook import cleanup,
and removal of the unused parquet fallback exception binding. Final closure
landed on commit `f9e730981`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139607755 -> f9e730981

Disposition: FIXED
Commit: `463692ea9`
Evidence: `.github/workflows/rag-release-gates.yml:84-96`;
`docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md:268-291`
Reason: The weekly/manual lane no longer hardcodes the missing
`data/evals/rag_weekly_500.jsonl` file. Instead it accepts an injected dataset
path via workflow input or repo variable, with deterministic sample-fixture
fallback and preserved strict flags.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360496 -> 463692ea9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110363640 -> 463692ea9

Disposition: FIXED
Commit: `d1fc36ed5`
Evidence: `.github/workflows/rag-release-gates.yml:36-54`;
`docs/roadmap/BACKLOG_LEDGER.md:1639-1667`
Reason: Smoke-job dependency installation and `timeout-minutes` are now explicit,
and the ledger entry now documents the canonical contract note plus concrete
blockers / exit criteria for the persistence seam.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360520 -> d1fc36ed5

Disposition: FIXED
Commit: `f9e730981`
Evidence: `notebooks/pulseplate_rag_release_gates.ipynb`
Reason: The notebook chunking loop now advances with the same overlap semantics
as the runner (`max(0, end - overlap)`) instead of the broken
`max(end - overlap, end)` update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360523 -> f9e730981

Disposition: FIXED
Commit: `f9e730981`
Evidence: `notebooks/pulseplate_rag_release_gates.ipynb`
Reason: The notebook now uses `TOP_K` instead of the undefined lowercase
`top_k` in `recall_at_effective_k`, so the analyst artifact matches the runner's
contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360527 -> f9e730981

Disposition: FIXED
Commit: `f9e730981`
Evidence: `scripts/evals/run_rag_release_gates.py:1788-1800`
Reason: The parquet-export fallback no longer binds an unused exception variable;
the CSV fallback behavior remains unchanged.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110456134 -> f9e730981

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending live runs on current head `f9e730981`
- [ ] Required checks complete (no pending jobs)
  Evidence: pending live runs on current head `f9e730981`
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending final post-push review sweep
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending final CodeRabbit / cubic post-push review sweep
- [ ] Pre-commit green on latest pushed head
  Evidence: pending final governance sync on latest pushed head
- [ ] `make verify` green on latest pushed head
  Evidence: not yet run for this lane

## Notes

- The lane packet remains the scope boundary for this PR; broader refactors and
  dashboard/persistence expansion stay out of scope until a separate governed
  follow-up exists.
  Evidence:
  `docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md:24-58`
- Current-head merge truth must come from the latest status checks on the latest
  pushed head, not from older cancelled or superseded runs.
  Evidence: `RUNBOOK_AGENT.md:448-450`;
  `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-163`
- Mandatory role-order evidence is not yet complete for a merge-ready claim:
  `qa-engineer-agent` and `security-auditor` still need an explicit final pass or
  a canonical no-actionable record on the latest head.
  Evidence:
  `docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md:26-37`
