# PR 1018 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: mcp_pulseplate_server.py:395, mcp_pulseplate_server.py:429, app/security/agent_input_guard.py:39
Reason: Tool-level guard preserves the `-32602 Invalid params` contract, while helper-level guard keeps direct helper calls fail-closed outside `_call_tool`; broad install-token regexes are intentionally scoped to AI-agent control surfaces per this PR's security requirement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1018#pullrequestreview-3909822861

## Merge Readiness
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
