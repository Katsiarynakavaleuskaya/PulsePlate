# PR #1522 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact was created immediately after the draft PR opened per repo
governance. Record every actionable human/bot disposition here before resolving
threads on GitHub.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: CodeRabbit draft-skip status comment listed below.
Reason: CodeRabbit skipped review because the PR is draft; no code or documentation change was requested. Finishing-touch checkboxes are optional bot UI affordances, not actionable review findings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1522#issuecomment-4316327364

Disposition: FIXED
Commit: 2ea3f2ca5
Evidence: docs/review/PR_1522_FIXED_MAPPING.md:32; docs/orchestration/WAVE6_AI_RUNTIME_AND_ADVISORY_SERIES_PACKET_2026-04-13.md:97
Reason: Final merge-readiness checklist entries now stay unchecked while PR #1522 has an open verification blocker, and the Wave 6 Rail B2 section now links to the canonical PR-S0-B2 packet instead of duplicating family-placement truth.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1522#pullrequestreview-4173487116 -> 2ea3f2ca5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1522#discussion_r3140365549 -> 2ea3f2ca5

Disposition: FIXED
Commit: 08761111f
Evidence: docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:673; docs/orchestration/PLUGIN_CONTROL_PLANE_FAMILIES_UMBRELLA_S0_PACKET_2026-04-24.md:94
Reason: Karpathy epic family placement now links back to the canonical PR-S0-B2 umbrella packet, and the packet clarifies that its role order is lane-local execution order, not a replacement for global AGENTS/RUNBOOK governance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1522#pullrequestreview-4173728214 -> 08761111f

## Initial Implementation Commits

- `e5f0e2ff2` - `docs(roadmap): define plugin control-plane umbrella`
- `2ea3f2ca5` - `docs(review): address pr1522 bot comments`
- `a5da6c797` - `fix(food-sources): restore source preflight typing`
- `653d398be` - `fix(food-sources): support narrow mypy mode`

## Merge Readiness

Merge-readiness contract:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

Final merge-cycle checks intentionally remain unchecked until the final
current-head review/check pass after the typecheck-restoration exception lands.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete with no pending required jobs
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] After latest bot/review activity, perform a final check and wait at least
      one review cycle before merging
- [ ] `python3 scripts/orchestration/check_preflight.py`
- [ ] `python3 scripts/orchestration/check_agent_consistency.py`
- [ ] `git diff --check`
- [ ] Focused grep checks for Rail B2 advisory/control-plane wording, family
      mapping, semantic-cache deferral, product-runtime/public-response
      prohibition, and Rail B1 separation
- [ ] `pre-commit run --all-files`
- [ ] Commit hooks passed during
      `git commit -m "docs(roadmap): define plugin control-plane umbrella"`
- [ ] Pre-push hooks passed during
      `git push -u origin codex/plugin-control-plane-families-umbrella-s0`
- [ ] `make verify` green on latest pushed head
      Operator note: full local run is intentionally not repeated because it
      executes the full repo suite. Local proof for PR-owned scope is
      `make typecheck`, `tests/test_food_source_preflight.py`,
      `pre-commit run --all-files`, and `make validate-changed`; GitHub
      current-head CI is the heavy-suite signal.

## Scope Boundary Proof

- Governance lane plus one explicit typecheck-restoration exception in
  `core/food_sources/source_preflight.py`.
- Routes, OpenAPI, schema, DTOs, DB, authz, billing, and public responses are unchanged.
- Product runtime truth and product RAG replacement remain out of scope.
- Excludes semantic cache, Redis/GPTCache, embeddings, vector DB, GraphRAG, and
  ContextManifest work.
- External plugin implementations such as GitHub, Cloudflare, Figma, and Hugging Face are not touched.
- Rail B1 advisory wiki remains a separate sibling rail, not a child of Rail B2.
