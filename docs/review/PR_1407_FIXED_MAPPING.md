<!-- markdownlint-disable MD034 -->
# PR 1407 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070061715 -> 5fa1ebf7a
Disposition: FIXED
Commit: `5fa1ebf7a`
Evidence: `docs/figma/README.md` now scopes the Code Connect bypass explicitly to the current web/iOS reconciliation lane and points future explicit Code Connect activation work back to the dedicated runbook/bridge docs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#pullrequestreview-4095619557 -> 5fa1ebf7a
Disposition: FIXED
Commit: `5fa1ebf7a`
Evidence: `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` now references the coordinator-first source model, adds lane-role expectations, and adds a positive steady-state checklist in the acceptance contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070084351 -> ce398d846
Disposition: FIXED
Commit: `ce398d846`
Evidence: `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` now cites the exact `AGENTS.md:348-361` and `docs/orchestration/workflow.md:52-68` anchors in the reference model instead of generic document names.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070084356 -> ce398d846
Disposition: FIXED
Commit: `ce398d846`
Evidence: `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` now appends the requested ADR/session evidence to the February 19, March 7, and March 11-12 decision-log entries and records `PR #1407` on the April 11 entry.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#pullrequestreview-4095639528 -> ce398d846
Disposition: FIXED
Commit: `ce398d846`
Evidence: the authority packet now addresses the new CodeRabbit review summary by adding exact source anchors in the reference model and explicit supporting evidence references in the decision log while keeping scope docs-only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070097524 -> b7a0fea32
Disposition: FIXED
Commit: `b7a0fea32`
Evidence: `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` now records exact `file:line` anchors for the precedence-critical repo mirrors and lane packets, including the web `canonical_execution`, iOS `implementation_safe`, legacy `reference_only`, and `spec_index_only` evidence surfaces.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070099294 -> b7a0fea32
Disposition: FIXED
Commit: `b7a0fea32`
Evidence: `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` now cites `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:87-102` for the February 19 design/spec + stale `1:72` history claim, which is the repo source that actually records the `umcCk7TtO760DJ3N6M7mvh` capture lineage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#pullrequestreview-4095649482 -> b7a0fea32
Disposition: FIXED
Commit: `b7a0fea32`
Evidence: the latest CodeRabbit review summary is addressed by the same packet update: precedence bullets now carry exact `file:line` anchors, and the readability nit is resolved by shortening the hard-rule wording to `read-only for authority`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#pullrequestreview-4095651529 -> b7a0fea32
Disposition: FIXED
Commit: `b7a0fea32`
Evidence: cubic found the unverifiable February 19 citation; the packet now points that decision-log claim to `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:87-102`, which preserves direct evidence for the stale `1:72` / `umc...` history.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#pullrequestreview-4095660120 -> f496aeba5
Disposition: FIXED
Commit: `f496aeba5`
Evidence: `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` now upgrades the March 7 and March 11-12 decision-log citations from filename-only references to exact `file:line` anchors, matching the packet's evidence-driven citation contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#pullrequestreview-4095662684 -> 58df72145
Disposition: FIXED
Commit: `58df72145`
Evidence: cubic found that the Make/prototype `reference_only` citation relied on audit assumptions; `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` now points that lane to `docs/runbooks/FIGMA_MCP_RUNTIME_MATRIX.md:65-69` and `docs/audit/PR_781_HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md:166-167`, which record the normalized `reference_only` policy and the `MrztJU3CQtxhADBbtAsWJ6` blank-scaffold status directly.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#pullrequestreview-4095668818 -> 58df72145
Disposition: FIXED
Commit: `58df72145`
Evidence: cubic found that the March 11-12 anchor no longer covered every asserted fact; the packet now splits that decision-log entry into separate `file:line` citations for live metadata/design-push discovery, `ios prototype v2` normalization, and the Code Connect blocked/non-authoritative state.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070112628 -> 58df72145
Disposition: FIXED
Commit: `58df72145`
Evidence: the precedence section no longer relies on `docs/audit/HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md:110-115`; it now cites repo sources that explicitly support `MrztJU3CQtxhADBbtAsWJ6` as a `reference_only` / scaffold-only surface.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070116391 -> 58df72145
Disposition: FIXED
Commit: `58df72145`
Evidence: commit `58df72145` adds the requested `docs(agents): ...` entry to the PR history and its body names the affected lane roles (`agent-coordinator`, `figma-designer`, `prompt-engineer`, `ios-specialist`, `frontend-engineer`, `qa-engineer-agent`, `bug-hunter`) while tightening the packet's coordinator-owned authority guidance.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070117904 -> 58df72145
Disposition: FIXED
Commit: `58df72145`
Evidence: the March 11-12 decision-log sentence now uses split anchors instead of a single over-broad range, so each clause about MCP metadata, design push, `ios prototype v2`, and Code Connect blocker status is backed by the cited lines.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#pullrequestreview-4095667009 -> c51c9e38f
Disposition: FIXED
Commit: `c51c9e38f`
Evidence: the branch now contains the required `docs(agents): tighten figma authority evidence` commit and the packet's April 11 decision-log entry now cites `docs/review/PR_1407_FIXED_MAPPING.md:63-86`, giving the review summary both the required workflow-doc commit in history and the requested concrete fixed-mapping audit anchor.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1407#discussion_r3070116393 -> c51c9e38f
Disposition: FIXED
Commit: `c51c9e38f`
Evidence: `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md` now appends `docs/review/PR_1407_FIXED_MAPPING.md:63-86` to the April 11, 2026 entry, so the delivery-model lock references a concrete `file:line` evidence artifact instead of only `PR #1407`.

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
<!-- markdownlint-enable MD034 -->
