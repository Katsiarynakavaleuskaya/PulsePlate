# PR #1496 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is the source of truth for review dispositions on PR #1496.
Record every actionable human or bot review item here before resolving threads
or claiming merge readiness.

## Fixed in Commit Mapping

- Review: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1496#pullrequestreview-4156146773
  - Disposition: FIXED
  - Commit: `88b92e02a5bf1383dfb8ab9263ce758cd0cb6d81`
  - Evidence:
    - `docs/orchestration/PULSEPLATE_SELECTIVE_GRAPHRAG_CONTRACT_TASK_PACKET_2026-04-22.md`
      now treats the ADR as the source of truth for selective-use and exclusion
      lists instead of duplicating them.
    - `docs/architecture/ADR_SELECTIVE_GRAPHRAG_CONTRACT_2026-04-22.md`
      now ties the starter graph boundary back to current PulsePlate
      nutrition/evidence surfaces and provenance requirements.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head

## Notes

- This PR is a docs-only selective GraphRAG contract lane.
- Canonical evaluation ownership remains under
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane`.
- Semantic cache remains deferred under
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`.
