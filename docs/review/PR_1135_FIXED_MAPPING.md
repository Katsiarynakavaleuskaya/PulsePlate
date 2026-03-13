# PR 1135 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: 4a375a3c4170c44f7cb6412f567a91787d7fdfa3
Evidence: `docs/figma/ios_prototype_v2/bmi.html:79` keeps the BMI CTA on-page as a button instead of navigating away before the result block, and `docs/figma/ios_prototype_v2/bmi.html:95` splits the malformed class token into the canonical `status-grid single-column` pair so the single-column layout rule applies.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924157885 -> 4a375a3c4170c44f7cb6412f567a91787d7fdfa3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924165845 -> 4a375a3c4170c44f7cb6412f567a91787d7fdfa3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184146 -> 4a375a3c4170c44f7cb6412f567a91787d7fdfa3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184161 -> 4a375a3c4170c44f7cb6412f567a91787d7fdfa3

Disposition: FIXED
Commit: 4a375a3c4170c44f7cb6412f567a91787d7fdfa3
Evidence: `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md:25` through `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md:32` now use the canonical `blocked_by_plan` status for every mapped screen while the workspace remains seat-blocked.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924157893 -> 4a375a3c4170c44f7cb6412f567a91787d7fdfa3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#pullrequestreview-3936032596 -> 4a375a3c4170c44f7cb6412f567a91787d7fdfa3

Disposition: FIXED
Commit: 4a375a3c4170c44f7cb6412f567a91787d7fdfa3
Evidence: `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md:110` now makes the BMI/onboarding recapture step explicitly conditional on future MCP node-id drift instead of listing already-completed work as pending.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184144 -> 4a375a3c4170c44f7cb6412f567a91787d7fdfa3

Disposition: NOT-A-BUG
Evidence: `git diff --name-only worktree/figma-ios-screen-polish...HEAD` shows the current stacked PR diff contains only `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md`, `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md`, `docs/figma/ios_prototype_v2/README.md`, `docs/figma/ios_prototype_v2/bmi.html`, `docs/figma/ios_prototype_v2/onboarding-value-usage.html`, `docs/figma/ios_prototype_v2/onboarding-welcome.html`, `docs/figma/ios_prototype_v2/styles.css`, `docs/review/PR_1135_FIXED_MAPPING.md`, and `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md`.
Reason: After changing PR `#1135` to base `worktree/figma-ios-screen-polish`, the old parent-diff comments on `.cursor/mcp.json.example`, `docs/figma/MCP_SETUP_GUIDE.md`, `docs/figma/ios_prototype_v2/weekly-plan-reader.html`, `docs/review/PR_1132_FIXED_MAPPING.md`, `docs/roadmap/BACKLOG_LEDGER.md`, and `docs/runbooks/FIGMA_MCP_RUNTIME_MATRIX.md` no longer apply to this isolated `BMI + Onboarding` slice; those files stay owned by the parent lanes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184138
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184171
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184177
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184180
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184183
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2924184187
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#pullrequestreview-3936064055

Disposition: FIXED
Commit: e5d974d8c72613030ec13940084c7628069b0d12
Evidence: `docs/review/PR_1135_FIXED_MAPPING.md:9`, `docs/review/PR_1135_FIXED_MAPPING.md:17`, `docs/review/PR_1135_FIXED_MAPPING.md:23`, and `docs/review/PR_1135_FIXED_MAPPING.md:39` now record full 40-character commit SHAs instead of abbreviated hashes, keeping the canonical artifact stable for later audit and review tooling.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#pullrequestreview-3943636463 -> e5d974d8c72613030ec13940084c7628069b0d12

Disposition: FIXED
Commit: c58693c76bdc292d6fd94c17216a1c92ceefea1d
Evidence: `docs/review/PR_1135_FIXED_MAPPING.md:44` now cites the actual `Commit:` declaration line in the same artifact, so the audit proof points to the full-SHA entry rather than an unrelated evidence row.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2930998589 -> c58693c76bdc292d6fd94c17216a1c92ceefea1d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#pullrequestreview-3943806426 -> c58693c76bdc292d6fd94c17216a1c92ceefea1d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2931006735 -> c58693c76bdc292d6fd94c17216a1c92ceefea1d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#pullrequestreview-3943816941 -> c58693c76bdc292d6fd94c17216a1c92ceefea1d

Disposition: FIXED
Commit: f3cac13cc77612b613ee5d0792d77b2e5d20b9c9
Evidence: `docs/review/PR_1135_FIXED_MAPPING.md:45` now points to the actual `Commit:` declaration line for the previous FIXED block, so the audit proof no longer references an `Evidence:` row by mistake.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#discussion_r2931083665 -> f3cac13cc77612b613ee5d0792d77b2e5d20b9c9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1135#pullrequestreview-3943904728 -> f3cac13cc77612b613ee5d0792d77b2e5d20b9c9

## Merge Readiness
- [ ] Local gates passed on current head
- [ ] All required checks green
- [ ] No unresolved review threads remain
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] Wait-window after latest bot/review activity observed
