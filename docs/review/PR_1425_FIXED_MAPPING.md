# PR 1425 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `de6826c74d4fce5a2757170be75f8bbeeead6fd2` standardizes the repo-first vs historical Code Connect lane terminology in `docs/figma/README.md` and `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`, adds direct `file:line` evidence anchors in the runbook, and replaces `<FIGMA_MAKE_FILE_ID>` with `MrztJU3CQtxhADBbtAsWJ6` in `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1425#issuecomment-4244395862 -> de6826c74d4fce5a2757170be75f8bbeeead6fd2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1425#issuecomment-4244395260 -> de6826c74d4fce5a2757170be75f8bbeeead6fd2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1425#discussion_r3079948288 -> de6826c74d4fce5a2757170be75f8bbeeead6fd2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1425#pullrequestreview-4106442884 -> de6826c74d4fce5a2757170be75f8bbeeead6fd2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1425#discussion_r3080134403 -> de6826c74d4fce5a2757170be75f8bbeeead6fd2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1425#pullrequestreview-4106658910 -> de6826c74d4fce5a2757170be75f8bbeeead6fd2

Disposition: FIXED
Commit: see mapping entries below
Evidence: `a08fa057f5c3f373e809c0f6a51e305689e7c80c` aligns `docs/figma/README.md` recommended workflow order with the authority-first repo-first reading sequence already used by the active runbook.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1425#discussion_r3079942573 -> a08fa057f5c3f373e809c0f6a51e305689e7c80c

Disposition: FIXED
Commit: see mapping entries below
Evidence: `4c4b100bfade1f03257443d8170ab18cb0793073` records the README-order review-thread disposition in the canonical review artifact and keeps the PR body mirror synchronized with the current branch head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1425#pullrequestreview-4106426892 -> 4c4b100bfade1f03257443d8170ab18cb0793073

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [ ] `make verify` green
- Docs-only validation green: `git diff --check origin/main...HEAD` and docs-only diff check returned clean.
