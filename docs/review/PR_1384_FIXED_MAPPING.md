# PR 1384 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 6a287324d
Evidence: `tools/agentguard/scan_text.mjs:3`, `tools/agentguard/scan_text.mjs:131`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1384#discussion_r3064221691 -> 6a287324d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1384#pullrequestreview-4089576004 -> 6a287324d

Disposition: FIXED
Commit: bdaf54d04
Evidence: `docs/security/GHSA-f886-m6hf-6m8v-brace-expansion.md:51`, `tests/test_root_npm_dependency_guards.py:25`, `tools/agentguard/scan_text.mjs:3`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1384#discussion_r3064250154 -> bdaf54d04
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1384#discussion_r3064250155 -> bdaf54d04
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1384#discussion_r3064250158 -> bdaf54d04

Disposition: NOT-A-BUG
Evidence: `tests/test_root_npm_dependency_guards.py:111` intentionally keeps the current cspell runtime chain explicit while still enforcing the security invariant that `path-to-regexp` is absent; the concrete actionable inline comments from this aggregate review were fixed in `bdaf54d04` and are mapped above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1384#pullrequestreview-4089605073

Disposition: NOT-A-BUG
Evidence: `app/security/goplus_agentguard_bridge.py:69` sends JSON (`json.dumps({"text": text, "filename": filename})`) to the Node scanner, so `tools/agentguard/scan_text.mjs:92` consuming JSON stdin matches the live bridge contract and the outside-diff warning is incorrect for this repo.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1384#pullrequestreview-4089664456

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
Notes: Initial post-open state recorded after draft PR creation. Bot output at this point is informational only (`review skipped` / reviewer guide) and does not create actionable review debt. Merge-readiness checkboxes remain open until the post-open reviewer lane and strict wrapper pass complete.
