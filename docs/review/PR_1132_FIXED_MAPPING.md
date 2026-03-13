# PR 1132 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 4293a136
Evidence: `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md:41-75` now adds auditable `file:line` anchors for the runtime/design claims, `docs/figma/ios_prototype_v2/shopping-list.html:89` renders `Weekly Plan` with `<code>`, `docs/figma/ios_prototype_v2/styles.css:22` quotes `"BlinkMacSystemFont"`, and `docs/review/PR_1132_FIXED_MAPPING.md:18-22` keeps every merge-readiness box unchecked pending the final merge cycle.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924019950 -> 4293a136
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924019977 -> 4293a136
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924019983 -> 4293a136
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924019996 -> 4293a136

Disposition: FIXED
Commit: 6e85ddec
Evidence: `docs/runbooks/FIGMA_MCP_RUNTIME_MATRIX.md:25-44` and `docs/runbooks/FIGMA_MCP_RUNTIME_MATRIX.md:67-97` add evidence/ADR/ledger anchors for the March 12 baseline and `reference_only` seam, `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:146` is now an `H2`, `docs/roadmap/BACKLOG_LEDGER.md:1091` adds the deterministic ledger anchor, and `docs/figma/ios_prototype_v2/onboarding-welcome.html:19` makes the skip affordance a real link.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924020010 -> 6e85ddec
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924020015 -> 6e85ddec

Disposition: FIXED
Commit: 19248410
Evidence: `docs/figma/ios_prototype_v2/README.md:30-39` now matches the canonical node registry already recorded in `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md:23-30` and `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:245-254`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924008149 -> 19248410
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924019966 -> 19248410

Disposition: FIXED
Commit: 6d3d182a
Evidence: `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md:52-55` now uses a polished-node example (`nodeId="11:2"`) that matches the activation-ready inventory table above instead of the stale pre-polish `4:2` value.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#pullrequestreview-3942510454 -> 6d3d182a

Disposition: FIXED
Commit: 1c6ae6b0
Evidence: `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md:52-55` now uses the first inventory entry (`nodeId="1:2"`) for the activation example, and `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md:67-70` now lists `Shopping List` before `Weekly Plan` so step 4 matches the activation-ready inventory ordering.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#pullrequestreview-3942641049 -> 1c6ae6b0

Disposition: NOT-A-BUG
Evidence: `docs/figma/ios_prototype_v2/README.md:1-22` defines the tracked `.html` files as MCP capture sources rather than deployable runtime assets, and `AGENTS.md` forbids local-only artifacts such as `worktrees/`, `.venv/`, caches, coverage outputs, `dist/`, and `build/`, but does not forbid repo-tracked static capture sources under `docs/figma/`.
Reason: The PR is a governed Figma capture-source lane, not a markdown-only docs PR. The tracked `.html` files are the implementation input for MCP capture and stay intentionally versioned in-repo.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924019960

Disposition: NOT-A-BUG
Evidence: `git diff --name-only origin/main...HEAD` on the current branch scope no longer lists `docs/review/PR_1125_FIXED_MAPPING.md`, so PR `#1132` no longer modifies PR `#1125`'s canonical review artifact.
Reason: PR `#1125` was merged into `main` on 2026-03-13 (`96c13ca0`); against that merged base, the current `#1132` branch scope keeps only the PR `#1132` governance artifact as its active review source of truth.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#discussion_r2924019992

Disposition: NOT-A-BUG
Evidence: The actionable inline comments from review `3935879095` are mapped individually above, and the rebased branch scope is now auditable via `git diff --name-only origin/main...HEAD`.
Reason: The review summary comment is aggregate-only; the actual merge-governance proof lives in the per-thread dispositions above rather than in a separate code change.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1132#pullrequestreview-3935879095

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
