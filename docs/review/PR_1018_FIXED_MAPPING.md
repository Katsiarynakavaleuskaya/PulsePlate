# PR 1018 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900619090 -> 15662733
Disposition: FIXED
Commit: 15662733
Evidence: `app/security/agent_input_guard.py:236`, `app/security/agent_input_guard.py:239`, `tests/test_agent_input_guard.py:123`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900619091 -> 7eb0fdbb
Disposition: FIXED
Commit: 7eb0fdbb
Evidence: `app/security/agent_input_guard.py:153`, `tests/test_agent_input_guard.py:238`, `tests/test_agent_input_guard.py:269`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3909822861
Disposition: NOT-A-BUG
Evidence: `mcp_pulseplate_server.py:395`, `mcp_pulseplate_server.py:429`, `app/security/agent_input_guard.py:39`
Reason: Tool-level guard preserves the `-32602 Invalid params` contract, while helper-level guard keeps direct helper calls fail-closed outside `_call_tool`; broad install-token regexes are intentionally scoped to AI-agent control surfaces per this PR's security requirement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3909867179 -> 7eb0fdbb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900626191 -> 7eb0fdbb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900626196 -> 7eb0fdbb
Disposition: FIXED
Commit: 7eb0fdbb
Evidence: `mcp_pulseplate_server.py:351`, `app/security/agent_input_guard.py:151`, `tests/test_mcp_pulseplate_server_coverage.py:701`, `tests/test_agent_input_guard.py:248`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634713 -> 885a2aee
Disposition: FIXED
Commit: 885a2aee
Evidence: `app/security/agent_input_guard.py:20`, `app/security/agent_input_guard.py:236`, `tests/test_agent_input_guard.py:142`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634720 -> dce0daac
Disposition: FIXED
Commit: dce0daac
Evidence: `mcp_pulseplate_server.py:345`, `mcp_pulseplate_server.py:418`, `mcp_pulseplate_server.py:491`, `tests/test_mcp_pulseplate_server_coverage.py:639`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634722 -> 7eb0fdbb
Disposition: FIXED
Commit: 7eb0fdbb
Evidence: `app/security/agent_input_guard.py:136`, `tests/test_agent_input_guard.py:47`, `tests/test_agent_input_guard.py:160`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634729 -> 885a2aee
Disposition: FIXED
Commit: 885a2aee
Evidence: `tests/test_mcp_pulseplate_server_coverage.py:823`, `tests/test_mcp_pulseplate_server_coverage.py:836`, `tests/test_mcp_pulseplate_server_coverage.py:961`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900872888 -> 6ec34dd5
Disposition: FIXED
Commit: 6ec34dd5
Evidence: `tools/agentguard/scan_text.mjs:8`, `tools/agentguard/scan_text.mjs:20`, `tools/agentguard/scan_text.mjs:47`, `tools/agentguard/scan_text.mjs:56`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900869402 -> 915f0703
Disposition: FIXED
Commit: 915f0703
Evidence: `docs/review/PR_1018_FIXED_MAPPING.md:32`, `docs/review/PR_1018_FIXED_MAPPING.md:36`, `docs/review/PR_1018_FIXED_MAPPING.md:40`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634715 -> 916cb676
Disposition: FIXED
Commit: 916cb676
Evidence: `app/security/agent_input_guard.py:302`, `legacy_app.py:2182`, `legacy_app.py:2344`, `app/routers/cbt_insight.py:32`, `app/routers/cbt_insight.py:253`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634717
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3909901909
Disposition: NOT-A-BUG
Evidence: `AGENTS.md:246`, `app/security/agent_input_guard.py:236`, `legacy_app.py:2182`
Reason: `#pullrequestreview-3909901909` is an aggregate wrapper for inline findings already dispositioned individually above; it does not introduce a separate standalone defect once those inline comments are mapped.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3910121127 -> effb7946
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900841047 -> effb7946
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900841048 -> effb7946
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900841049 -> effb7946
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900841050 -> effb7946
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900841051 -> effb7946
Disposition: FIXED
Commit: effb7946
Evidence: `mcp_pulseplate_server.py:344`, `app/security/agent_input_guard.py:33`, `tools/agentguard/scan_text.mjs:8`, `tests/test_agent_input_guard.py:75`, `app/security/goplus_agentguard_bridge.py:77`, `tests/test_agent_input_guard.py:373`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900846638 -> effb7946
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900846640 -> effb7946
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900846645 -> effb7946
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900846646 -> effb7946
Disposition: FIXED
Commit: effb7946
Evidence: `AGENTS.md:250`, `app/security/goplus_agentguard_bridge.py:77`, `tests/test_agent_input_guard.py:313`, `tests/test_insight_error_hygiene.py:136`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900846643 -> 077bc06e
Disposition: FIXED
Commit: 077bc06e
Evidence: `app/routers/cbt_insight.py:202`, `frontend/src/api/openapi.json:7752`, `frontend/src/api/schema.ts:3949`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900846642
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3910129132
Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/review_mapping_artifact.py:31`, `scripts/orchestration/review_mapping_artifact.py:34`, `docs/review/PR_1018_FIXED_MAPPING.md:7`
Reason: The canonical artifact now uses the parser-required plain `- <url>` / `- <url> -> <sha>` format. The remaining aggregate CodeRabbit review does not add a standalone defect once its individual inline comments are dispositioned above.

## Merge Readiness
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
