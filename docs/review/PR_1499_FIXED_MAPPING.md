# PR #1499 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: `app/services/insight_application_service.py:166-171` now resolves `recursive_rollout_policy` via `getattr(..., None)` and calls `_legacy_recursive_rollout_policy(...)` only when the prepared runtime is missing that attribute.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158197463 -> 1067c5acd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#discussion_r3127164224 -> 1067c5acd

Disposition: FIXED
Commit: see mapping entries below
Evidence: `app/services/insight_runtime.py:81-96` now derives the base `rag` snapshot from `recursive_rollout_policy.use_rag` when a prepared policy is injected and `use_rag` is omitted, `tests/test_remaining_modules.py:1345-1365` guards both recursive env readers while proving the prepared policy owns the exported RAG snapshot, `docs/orchestration/WAVE6_A7_RECURSIVE_METHODS_W1_PACKET_2026-04-22.md:24-49` now attaches file:line anchors to every current-head truth bullet, `docs/orchestration/WAVE6_A7_TASK_ANALYSIS_2026-04-22.md:57-70` now cites concrete runtime-scope evidence, and `docs/roadmap/BACKLOG_LEDGER.md:2101-2102` names concrete `PR #1499`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158211717 -> d60326ac5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#discussion_r3127177474 -> 8152a92b6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#discussion_r3127177476 -> d60326ac5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#discussion_r3127177479 -> d60326ac5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#discussion_r3127177481 -> d60326ac5

Disposition: FIXED
Commit: see mapping entries below
Evidence: `app/services/insight_application_service.py:174-185` now passes `use_rag=recursive_rollout_policy.use_rag` into `generate_traced_insight(...)`, and `tests/test_insight_application_service.py:530-536` plus `:648-654` assert that downstream `use_rag` follows the resolved recursive rollout policy on the prepared-policy and prepared-policy-no-legacy paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158236666 -> bb22b11c0

Disposition: FIXED
Commit: see mapping entries below
Evidence: `app/services/insight_runtime.py:81-96` now uses the resolved recursive rollout policy as the single source of truth for the base `rag` snapshot, so the duplicate CodeRabbit review was closed by the same bounded runtime fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158268827 -> 8152a92b6

Disposition: FIXED
Commit: see mapping entries below
Evidence: `tests/test_remaining_modules.py:1345-1365` now covers prepared-policy fallback behavior through the public `insight_feature_flag_state(...)` seam, so the temporary `_legacy_recursive_rollout_policy(...)` helper no longer needs a direct unit anchor in `tests/test_insight_application_service.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158639077 -> b1bdeeb92

Disposition: FIXED
Commit: see mapping entries below
Evidence: `tests/test_remaining_modules.py:1223-1232` now guards both recursive env readers in `_traced_retrieve_and_validate_rag(...)`, and `tests/test_insight_application_service.py:478-517` plus `:587-626` now stub all philosophy and recursive env helpers so the two prepared-policy request-path tests stay deterministic and isolated from global feature-flag state.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158717729 -> b7d6b8f5e

## Post-Merge Closeout

- State: `MERGED`
- PR #1499 merged at `2026-04-23T01:37:29Z`
- Merge commit: `1e7166e55c54448c0d6475338e1b9984efd0caf1`
- Original branch: `codex/ai-recursive-methods-w1`
- Closeout scope: PR-A7 W1 is not re-opened and implementation is not duplicated.
- Parent scope: the broader recursive-methods P1 item remains open until the full recursive-framework DoD is separately proven.
- Boundary: semantic-cache gate remained closed. Redis/GPTCache rollout,
  GraphRAG, ContextManifest, DB persistence, public route, OpenAPI, DTO, and
  response-shape changes remained out of scope for this closeout.

## Historical Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

This section is historical evidence only. PR #1499 is already merged, so this
closeout does not re-run or reassert the original readiness checklist. The
current closeout PR owns fresh validation and merge-readiness evidence.

- Historical local proof: `pre-commit run --all-files` passed before pushing head `894dd6e9b8066fb5e8522931cae69233f9f39f8d`.
- Historical local proof: `make verify` passed earlier on branch head `3aa83b33779863e1c07d896e5398ee2a15388b49`.
