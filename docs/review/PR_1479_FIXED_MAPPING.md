# PR #1479 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

This artifact is created immediately after PR open per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

Post-open local review findings (bug-hunter pass; no GitHub thread URLs yet):

1. Canonical `CI` workflow audited only `requirements.txt` and missed the new optional
   `requirements-rag-vector.txt` manifest.
   Disposition: FIXED
   Commit: `14c66968e`
   Evidence: `.github/workflows/ci.yml:416-468`; `tests/test_python_supply_chain_controls.py:409-418`

2. `requirements-lock.txt` still pinned optional rag-vector packages after the split,
   which widened the base lock surface beyond repo truth.
   Disposition: FIXED
   Commit: `14c66968e`
   Evidence: `requirements-lock.txt` no longer contains `pgvector==`, `sentence-transformers==`, `transformers==`, or `torch==`; enforced by `tests/test_python_supply_chain_controls.py:421-427`

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: `AGENTS.md:42-49`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:95-112`.
- [ ] Required checks complete (no pending jobs)
  Evidence: `AGENTS.md:46-49`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:155-163`.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: `AGENTS.md:43-45`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:95-112`.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: `AGENTS.md:44-45`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:95-112`.
- [x] Pre-commit green on latest pushed head
  Evidence: local `pre-commit run --all-files`; push gate output on branch head `c3b211a64`.
- [ ] `make verify` green on latest pushed head
  Evidence: `AGENTS.md:1-16`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:175-180`.

## Deferred / Follow-ups

- deploy-contract reconciliation starts only after PR #1479 merges, local `main` is re-synced, and this lane worktree/branch are cleaned up
- Dagger, signed provenance, SBOM/VEX, Cloudflare, runtime slimming, and image-budget telemetry remain out of scope for this slice
