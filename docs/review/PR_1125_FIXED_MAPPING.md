# PR 1125 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#discussion_r2921386878 -> 6154efc9
Disposition: FIXED
Commit: 6154efc9
Evidence: `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:27`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#discussion_r2921394139 -> 6154efc9
Disposition: FIXED
Commit: 6154efc9
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:902`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#discussion_r2921400034
Disposition: NOT-A-BUG
Evidence: `.cursor/mcp.json.example:3`; `docs/figma/MCP_SETUP_GUIDE.md:21`; `docs/figma/MCP_SETUP_GUIDE.md:25`
Reason: The tracked template and setup guide intentionally align on the `figma` server alias in this repo; this is an explicit config-surface documentation choice, not accidental runtime drift.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#discussion_r2921400040 -> 6154efc9
Disposition: FIXED
Commit: 6154efc9
Evidence: `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md:72`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#discussion_r2921400042
Disposition: NOT-A-BUG
Evidence: `scripts/ci/pr_scope_guard.sh:103`; `scripts/ci/pr_scope_guard.sh:119`; `docs/figma/ios_prototype_v2/README.md:3`; `docs/figma/ios_prototype_v2/README.md:19`
Reason: The HTML files under `docs/figma/ios_prototype_v2/` are intentional Figma capture-source artifacts, not `docs/pr` planning docs or runtime Python/config drift; the enforced scope guard does not ban this path and the README explicitly marks them as capture inputs rather than product pages.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#discussion_r2921400043 -> 6154efc9
Disposition: FIXED
Commit: 6154efc9
Evidence: `docs/figma/ios_prototype_v2/index.html:1`; `docs/figma/ios_prototype_v2/README.md:19`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#discussion_r2921400048 -> 6154efc9
Disposition: FIXED
Commit: 6154efc9
Evidence: `docs/figma/ios_prototype_v2/profile.html:33`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#discussion_r2921400050 -> 6154efc9
Disposition: FIXED
Commit: 6154efc9
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:902`; `docs/roadmap/BACKLOG_LEDGER.md:906`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#pullrequestreview-3932987652
Disposition: NOT-A-BUG
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:902`; `docs/roadmap/BACKLOG_LEDGER.md:906`
Reason: This cubic summary review aggregates the backlog stale-item finding fixed above in `6154efc9`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1125#pullrequestreview-3932993112
Disposition: NOT-A-BUG
Evidence: `.cursor/mcp.json.example:3`; `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md:72`; `docs/figma/ios_prototype_v2/index.html:1`; `docs/figma/ios_prototype_v2/profile.html:33`; `docs/roadmap/BACKLOG_LEDGER.md:902`
Reason: This CodeRabbit summary review aggregates the inline findings dispositioned above; current head fixes the concrete doc/html issues in `6154efc9`, and the two remaining points are deliberate `NOT-A-BUG` decisions with evidence above.

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
