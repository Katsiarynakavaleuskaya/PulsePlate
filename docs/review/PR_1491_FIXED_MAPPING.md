# PR #1491 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#pullrequestreview-4150691137 -> bc3f17550
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3120227129 -> bc3f17550
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3120227132 -> bc3f17550
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3120227139 -> bc3f17550
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3120227143 -> bc3f17550
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3120227148 -> bc3f17550

Disposition: FIXED (CodeRabbit degraded-bundle recomputation, deterministic artifact contract, finite/range rate guard, missing fail-closed regression coverage, and roadmap sequence sync)
Commit: see mapping entries below
Evidence: `core/rag/orchestration.py:370-446` now rebuilds admission bundles for post-format/redaction degradation paths; `core/verification/contracts.py:16-27` and `core/verification/registry.py:309-360` keep artifacts deterministic and reject non-finite/out-of-range analytical rates; `tests/test_insight_application_service.py:553-720`, `tests/test_philosophical_runtime.py:440-560`, and `tests/test_rag_orchestration.py:1427-1435` cover denied/missing bundle fail-closed paths; `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:661-666` inserts `PR-V1` into the condensed runtime sequence.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3120248974 -> 71e5910ee
Disposition: FIXED (Sourcery `RAGContext | None` typing alignment for recursive verification-call helper)
Commit: see mapping entries below
Evidence: `core/rag/orchestration.py:520-527` now types `_extract_recursive_verification_calls` to accept `RAGContext | None`, matching the live call site and helper semantics.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3122909859 -> ce47d77cb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3122909875 -> ce47d77cb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3122909887 -> ce47d77cb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#pullrequestreview-4153538455 -> ce47d77cb
Disposition: FIXED (CodeRabbit strict recursive verification-call extraction, fail-closed non-finite confidence guard, and canonical denied-bundle runtime test coverage)
Commit: see mapping entries below
Evidence: `core/rag/orchestration.py:546-553` now rejects boolean and negative `verification_calls` values; `core/verification/registry.py:199-223` fails closed on non-finite confidence input with `confidence_non_finite`; `tests/test_philosophical_runtime.py:534-544` now uses `knowledge_candidates_canonical=True`, so the denied verification-bundle gate is actually exercised.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#discussion_r3123053697 -> f4f9df610
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#pullrequestreview-4153688054 -> f4f9df610
Disposition: FIXED (CodeRabbit explicit return annotations for new verification-bundle test helpers)
Commit: see mapping entries below
Evidence: `tests/test_remaining_modules.py:22-25` now imports `VerificationBundle` for type-checking, and `tests/test_remaining_modules.py:591-613` plus `:786-810` declare explicit `-> "VerificationBundle"` return types on the new `_verification_bundle(...)` helpers without triggering runtime annotation evaluation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1491#pullrequestreview-4150713266
Disposition: NOT-A-BUG
Evidence: `AGENTS.md:317-323` and `docs/orchestration/WAVE6_V1_VERIFICATION_REGISTRY_PACKET_2026-04-21.md:21-32` define this lane as fail-closed knowledge admission from validated RAG evidence only; `core/verification/registry.py:248-255` intentionally marks recursive execution as non-canonical for `write` admission in PR-V1, so the review's recursive hard-deny concern is expected behavior, not a regression. The duplicated test helper note is advisory cleanup, not a correctness blocker for this bounded lane.
Reason: PR-V1 deliberately keeps recursive paths non-canonical and does not widen the lane into cross-suite test-helper refactors.

## Post-Merge Closeout

- State: `MERGED`
- PR #1491 merged at `2026-04-22T10:38:04Z`
- Merge commit: `ce024e7cdca3ec94bbffb095e050010a8198e792`
- Original branch: `codex/ai-verification-registry-v1`
- Closeout scope: PR-V1 is not re-opened and `core/verification/*`
  implementation is not duplicated.
- Boundary: semantic-cache gate remained closed; Redis/GPTCache, GraphRAG,
  ContextManifest, DB persistence, route/OpenAPI/DTO changes, and cache/action
  runtime enablement were not part of PR #1491.
- Reconciliation: the current closeout PR replaces the stale unchecked
  pre-merge readiness notes above with merged-state evidence while preserving
  the original review-thread dispositions.
