# PR #1476 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after PR open per repo governance.
Record every new disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#discussion_r3106665311 -> 5650dcdb3
Disposition: FIXED
Commit: 5650dcdb3
Evidence: `frontend/src/pages/Pro/ProPaywallPage.tsx:40`, `frontend/src/pages/Pro/ProPaywallPage.tsx:44`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:88`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:194`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#discussion_r3106668204 -> 5650dcdb3
Disposition: FIXED
Commit: 5650dcdb3
Evidence: `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:47`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:52`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:205`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:223`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#discussion_r3106670831 -> 5650dcdb3
Disposition: FIXED
Commit: 5650dcdb3
Evidence: `frontend/src/pages/Pro/ProPaywallPage.tsx:40`, `frontend/src/pages/Pro/ProPaywallPage.tsx:44`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:88`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:194`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#pullrequestreview-4135809700
Disposition: NOT-A-BUG
Evidence: `frontend/src/pages/Pro/ProPaywallPage.tsx:40`, `ios/PulsePlate/Views/Components/SoftPaywallHookView.swift:9`, `ios/PulsePlate/Views/Components/SoftPaywallHookView.swift:12`, `ios/PulsePlate/Routing/PaywallRouter.swift:45`, `ios/PulsePlate/Routing/PaywallRouter.swift:53`
Reason: This Sourcery review is an aggregate surface. Its inline `triggerReason` defect is fixed in `5650dcdb3`, the advisory-only `nextBestAction` prop is already documented in `SoftPaywallHookView`, and `PaywallTarget.resolve` now uses an explicit nil-guarded NBA-surface branch before the intentional fail-closed fallback to `.pro`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#pullrequestreview-4135811955 -> 5650dcdb3
Disposition: FIXED
Commit: 5650dcdb3
Evidence: `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:47`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:52`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:205`, `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:68`, `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:80`, `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx:232`, `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx:248`, `ios/PulsePlate/Routing/PaywallRouter.swift:45`, `ios/PulsePlate/Routing/PaywallRouter.swift:53`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#pullrequestreview-4135813914
Disposition: NOT-A-BUG
Evidence: `frontend/src/pages/Pro/ProPaywallPage.tsx:40`, `frontend/src/pages/Pro/ProPaywallPage.tsx:44`
Reason: This cubic review is an aggregate wrapper for inline thread `#discussion_r3106670831`, which is fixed in `5650dcdb3`; it does not add a separate unresolved defect beyond that thread-level finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#discussion_r3106684929
Disposition: NOT-A-BUG
Evidence: `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:68`, `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:80`, `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx:232`, `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx:248`
Reason: cubic identified this on stale commit `7fae34e2`, but the current PR head already logs `triggerReason` into paywall analytics and asserts the derived advisory trigger in the focused web test. The current implementation is therefore already correct.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#pullrequestreview-4135824537
Disposition: NOT-A-BUG
Evidence: `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:68`, `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:80`, `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx:232`, `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx:248`
Reason: This later cubic review is an aggregate wrapper for inline thread `#discussion_r3106684929`, which points at a stale pre-fix commit. On the current head the derived `triggerReason` already flows into analytics, so no separate unresolved defect remains.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#discussion_r3106687203
Disposition: NOT-A-BUG
Evidence: `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:68`, `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:80`, `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx:232`, `frontend/src/components/SoftPaywallHook/__tests__/SoftPaywallHook.test.tsx:248`
Reason: The Codex connector comment also targets stale commit `7fae34e2`. On the current head the paywall analytics payload already uses the derived `triggerReason`, and the focused test asserts the propagated `targets_ready` advisory trigger.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#pullrequestreview-4135826334
Disposition: NOT-A-BUG
Evidence: `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:68`, `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:80`
Reason: This Codex review is an aggregate shell for inline thread `#discussion_r3106687203`, which points at stale pre-fix code. The current head already carries the analytics fix, so the shell does not add a separate unresolved defect.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1476#issuecomment-4275677779
Disposition: NOT-A-BUG
Evidence: `AGENTS.md:5`, `AGENTS.md:8`, `AGENTS.md:42`, `AGENTS.md:45`, `AGENTS.md:51`, `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:43`, `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:52`
Reason: The CodeRabbit docstring-coverage warning is advisory for this lane. The repo hard gates for merge readiness are `make verify`, current-head required checks, and dispositioned actionable review comments; docstring coverage is not a canonical merge-blocking contract here.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head

## Validation Snapshot

- [x] `python3 scripts/orchestration/check_preflight.py`
- [x] `python3 scripts/orchestration/check_agent_consistency.py`
- [x] `pre-commit run --all-files`
- [x] `git diff --check`
- [x] focused web tests for BMI / soft-paywall / pro-paywall hint consumption
- [x] `cd frontend && npm run build`
- [x] focused iOS `xcodebuild build-for-testing`
- [ ] full `make verify`
- [ ] full `make diff-cov`

Note: this PR intentionally carries focused web+iOS validation evidence for the
PR-3 slice. Full repo-wide coverage validation was not used as the gating
signal for this lane.
