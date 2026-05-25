# PR 1415 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#discussion_r3075824090 -> df6c2c5bc
Disposition: FIXED
Commit: df6c2c5bc
Evidence: `scripts/ci/emergency_python_wheels.json:73` and `scripts/ci/emergency_python_wheels.json:87` add the missing CPython `3.11`/`3.12` Pillow `12.2.0` Linux wheel entries required by the active CI matrix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#discussion_r3075858495 -> 38e8b87db
Disposition: FIXED
Commit: 38e8b87db
Evidence: `docs/security/PILLOW_12_2_0_PRIVATE_INDEX_ADVISORY.md:11` and `docs/security/PILLOW_12_2_0_PRIVATE_INDEX_ADVISORY.md:18` now make the supported `3.11`/`3.12`/`3.13` matrix and Linux `amd64` CI/Docker fallback scope explicit in a post-comment docs follow-through.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#discussion_r3075839393 -> 1d1b556dd
Disposition: FIXED
Commit: 1d1b556dd
Evidence: `docs/security/PILLOW_12_2_0_PRIVATE_INDEX_ADVISORY.md:11` and `docs/security/PILLOW_12_2_0_PRIVATE_INDEX_ADVISORY.md:37` update the advisory to the `3.11`/`3.12`/`3.13` matrix and keep the corrected fallback-reference context.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#discussion_r3075839370 -> f748ec1d0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#discussion_r3075839399 -> f748ec1d0
Disposition: FIXED
Commit: f748ec1d0
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:403` moves the removal task to `PR-TBD` follow-up tracking, while `tests/test_insight_rag_response_fields.py:362`, `tests/test_insight_rag_response_fields.py:399`, and `tests/test_insight_rag_response_fields.py:765` assert JSON content type before `resp.json()` on the affected collapse-path tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#pullrequestreview-4101969556
Disposition: NOT-A-BUG
Reason: This CodeRabbit review URL is the aggregate container for the already-dispositioned thread-level findings in this artifact and does not introduce a separate unfixed review-level delta.
Evidence: See the mapped FIXED entries for `discussion_r3075839393`, `discussion_r3075839370`, and `discussion_r3075839399` above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#pullrequestreview-4101989332
Disposition: NOT-A-BUG
Reason: This Cubic review URL only aggregates the same Pillow runtime-gap finding already fixed at thread level and does not require an additional code or docs change beyond that mapped thread.
Evidence: See the mapped FIXED entries for `discussion_r3075824090` and `discussion_r3075858495` above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#discussion_r3076040654 -> b1d7274f7
Disposition: FIXED
Commit: b1d7274f7
Evidence: `scripts/ci/emergency_python_wheels.json:22` is now the single remaining `pillow==12.2.0` emergency wheel entry; the duplicate block previously repeated at lines `77-83` has been removed so fallback staging cannot select the same wheel twice.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1415#pullrequestreview-4102176336
Disposition: NOT-A-BUG
Reason: This CodeRabbit review URL is the aggregate container for the already-dispositioned inline finding and does not introduce an extra unfixed delta beyond `discussion_r3076040654`.
Evidence: See the FIXED mapping for `discussion_r3076040654` above.

## Post-Merge Closeout

- State: `MERGED`
- Title: `feat(rag): harden degraded retrieval paths and keep contracts additive`
- PR #1415 merged at `2026-04-14T20:59:47Z`
- Merge commit: `146da0e0d269acea5ba946d239997705ebaf62c3`
- Original branch: `feat/rag-hardening-followthrough`
- Closeout scope: PR-A2 is landed historical runtime truth; this
  reconciliation does not duplicate implementation.
- Evidence boundary: deterministic tests and landed symbols prove the closeout
  state only. This artifact does not claim new benchmark results, accuracy
  gains, latency wins, or production RAG robustness.
- Boundary: semantic-cache markers remain `closed / false / false / true`.
  Semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence,
  public routes, OpenAPI, DTOs, provider integration, recursive learning,
  provider chain/tree-of-thought, and default activation remain out of scope.

## Historical Merge Readiness

This section is historical evidence only. PR #1415 is already merged, so this
closeout does not re-run or reassert the original readiness checklist. The
current A2 closeout PR must record its own validation evidence, operator-approved
narrow-gate deferral, PR body mirror, and fixed-mapping artifact after its PR
number exists.
