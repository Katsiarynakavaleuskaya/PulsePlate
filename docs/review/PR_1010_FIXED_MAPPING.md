# PR 1010 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#pullrequestreview-3909426981
Disposition: NOT-A-BUG
Evidence: AGENTS.md:103
Reason: Docs Phase1 gates explicitly require `file:line` evidence anchors, so replacing them with only section anchors would violate the current canonical docs contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900340993 -> d4e00cba
Disposition: FIXED
Commit: d4e00cba
Evidence: app/models/llm_quota_usage.py:17

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900340994 -> d4e00cba
Disposition: FIXED
Commit: d4e00cba
Evidence: docker-compose.yaml:19

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900340996 -> d4e00cba
Disposition: FIXED
Commit: d4e00cba
Evidence: tests/test_rag_contract_surface.py:1

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900347043 -> d4e00cba
Disposition: FIXED
Commit: d4e00cba
Evidence: docker-compose.yaml:22

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#pullrequestreview-3909433208 -> d4e00cba
Disposition: FIXED
Commit: d4e00cba
Evidence: docker-compose.yaml:22

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900356571 -> d4e00cba
Disposition: FIXED
Commit: d4e00cba
Evidence: docker-compose.yaml:22

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900356575 -> 6af727f5
Disposition: FIXED
Commit: 6af727f5
Evidence: docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md:1

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900356579 -> 6af727f5
Disposition: FIXED
Commit: 6af727f5
Evidence: docs/roadmap/BACKLOG_LEDGER.md:4079

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#pullrequestreview-3909442683
Disposition: NOT-A-BUG
Evidence: docker-compose.yaml:22; docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md:1; docs/roadmap/BACKLOG_LEDGER.md:4079; .env.example:63
Reason: This review summary aggregates inline findings already dispositioned above; the outside-diff `.env.example` note does not indicate a docs-only violation because PR #1010 intentionally includes runtime/config changes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900386318
Disposition: NOT-A-BUG
Evidence: PR #1010 body (`Select one change type` reclassified to `Refactor`; `Notes` explicitly list runtime/config scope)
Reason: The finding is valid only for a docs-only PR. PR #1010 is reclassified as a runtime/refactor change and no longer claims docs-only scope.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900386321 -> 3b77d30a
Disposition: FIXED
Commit: 3b77d30a
Evidence: docs/roadmap/BACKLOG_LEDGER.md:2079

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900386326 -> 3b77d30a
Disposition: FIXED
Commit: 3b77d30a
Evidence: docs/roadmap/BACKLOG_LEDGER.md:4042

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#pullrequestreview-3909480064
Disposition: NOT-A-BUG
Evidence: tests/test_rag_contract_surface.py:13; docs/roadmap/BACKLOG_LEDGER.md:2079; docs/roadmap/BACKLOG_LEDGER.md:4042; PR #1010 body (`Select one change type` reclassified to `Refactor`)
Reason: This review summary aggregates one inline test hardening fix, two backlog fixes, and one PR classification correction already dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#pullrequestreview-3909519747
Disposition: NOT-A-BUG
Evidence: AGENTS.md:103; scripts/orchestration/review_mapping_artifact.py:152; scripts/ci/check_pr_body_phase2_gates.py:136
Reason: This cubic review summary aggregates the inline artifact-format finding fixed below; once URL-only thread entries are canonical for NOT-A-BUG and DEFERRED, the summary itself needs evidence but no commit proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1010#discussion_r2900418091 -> 0ced797a
Disposition: FIXED
Commit: 0ced797a
Evidence: AGENTS.md:103; scripts/orchestration/review_mapping_artifact.py:152; scripts/ci/check_pr_body_phase2_gates.py:136
