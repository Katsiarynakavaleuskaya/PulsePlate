# PR 1018 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 15662733
Evidence: app/security/agent_input_guard.py:236, app/security/agent_input_guard.py:239, tests/test_agent_input_guard.py:123

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900619090

Disposition: FIXED
Commit: 7eb0fdbb
Evidence: app/security/agent_input_guard.py:153, tests/test_agent_input_guard.py:238, tests/test_agent_input_guard.py:269

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900619091

Disposition: NOT-A-BUG
Evidence: mcp_pulseplate_server.py:395, mcp_pulseplate_server.py:429, app/security/agent_input_guard.py:39
Reason: Tool-level guard preserves the `-32602 Invalid params` contract, while helper-level guard keeps direct helper calls fail-closed outside `_call_tool`; broad install-token regexes are intentionally scoped to AI-agent control surfaces per this PR's security requirement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3909822861

Disposition: FIXED
Commit: 7eb0fdbb
Evidence: mcp_pulseplate_server.py:351, app/security/agent_input_guard.py:151, tests/test_mcp_pulseplate_server_coverage.py:701, tests/test_agent_input_guard.py:248

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3909867179
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900626191
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900626196

Disposition: FIXED
Commit: 885a2aee
Evidence: app/security/agent_input_guard.py:20, app/security/agent_input_guard.py:236, tests/test_agent_input_guard.py:142

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634713

Disposition: FIXED
Commit: dce0daac
Evidence: mcp_pulseplate_server.py:345, mcp_pulseplate_server.py:418, mcp_pulseplate_server.py:491, tests/test_mcp_pulseplate_server_coverage.py:639

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634720

Disposition: FIXED
Commit: 7eb0fdbb
Evidence: app/security/agent_input_guard.py:136, tests/test_agent_input_guard.py:47, tests/test_agent_input_guard.py:160

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634722

Disposition: FIXED
Commit: 885a2aee
Evidence: tests/test_mcp_pulseplate_server_coverage.py:816, tests/test_mcp_pulseplate_server_coverage.py:936

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634729

Disposition: FIXED
Commit: 24565a7a
Evidence: AGENTS.md:246, AGENTS.md:248, AGENTS.md:249

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634715

Disposition: FIXED
Commit: 916cb676
Evidence: app/security/agent_input_guard.py:302, legacy_app.py:2182, legacy_app.py:2344, app/routers/cbt_insight.py:32, app/routers/cbt_insight.py:253

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#discussion_r2900634717

Disposition: NOT-A-BUG
Evidence: AGENTS.md:246, app/security/agent_input_guard.py:236, legacy_app.py:2182
Reason: `#pullrequestreview-3909901909` is an aggregate wrapper for inline findings already dispositioned individually above; it does not introduce a separate standalone defect once those inline comments are mapped.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3909901909

## Merge Readiness
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
