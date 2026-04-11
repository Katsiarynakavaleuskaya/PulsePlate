# PR 1391 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: `frontend/src/pages/Plate.stories.tsx` runtime-narrows `sessionState` instead of using an unchecked cast; `frontend/src/pages/Plate.storySupport.tsx` moves stub installation to `useLayoutEffect`, preserves explicit cleanup return for the follow-up review, uses `PRO_SESSION_PATH`, and restores `window.fetch` only when the installed stub still owns it; `frontend/src/pages/__tests__/Plate.storyHarness.test.tsx` asserts the accessible premium links without `hidden: true`; `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md` clarifies this lane is operationalization/evidence work rather than docs-only scope and tightens the reviewer wording; `docs/design/DESIGN_BRIDGE_FIRST_PARITY_PACK_2026-04-11.md` records the green iOS parity evidence on the pre-sync head and fixes the follow-up wording.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#pullrequestreview-4093734909 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#pullrequestreview-4093737310 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#pullrequestreview-4093741184 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#pullrequestreview-4093773991 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068014293 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068014294 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068019659 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068019660 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068057762 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#pullrequestreview-4094077543 -> 0aa92fedb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#pullrequestreview-4094078592 -> 0aa92fedb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#pullrequestreview-4094079985 -> 0aa92fedb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068417797 -> 0aa92fedb

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068013070 -> 7098293c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068013072 -> 7098293c0
Disposition: FIXED
Commit: 7098293c0
Evidence: `frontend/src/pages/Plate.storySupport.tsx` installs the session stub from `useLayoutEffect` before child effects run, and `frontend/src/pages/__tests__/Plate.storyHarness.test.tsx` now asserts the visible premium links without `hidden: true`, so the unlocked parity story fails closed if it regresses to the paywalled preview.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#discussion_r3068011020
Disposition: NOT-A-BUG
Evidence: `frontend/src/api/client.ts:176`, `frontend/src/api/client.ts:276`, and `frontend/src/api/__tests__/client.test.ts:198` show the only call site uses `normalizeApiUrl(getApiBase(), PRO_SESSION_PATH)` and the client test asserts the exact request URL `http://test-api.com/api/v1/pro/session`, so this Storybook stub does not receive query-string or trailing-slash variants on the governed parity path.
Reason: The concern identified by Sourcery is hypothetical for this lane, but the actual governed call path is exact and already regression-covered, so broadening the matcher here would add surface area without improving the representative parity contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1391#pullrequestreview-4094087253 -> d22f3c2d9
Disposition: FIXED
Commit: d22f3c2d9
Evidence: `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md:85-86` now keeps the parallel evidence bullets but removes the duplicated `explicitly`, addressing the wording nit identified by CodeRabbit without changing the packet contract.

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
Notes: PR #1391 remains draft-only. Canonical review mapping is now parser-valid on the latest pushed head, and a fresh current-head CI rerun is required after this artifact/body sync. Remaining blockers are the mandatory post-open `qa-engineer-agent -> bug-hunter` loop, unresolved review-thread disposition in GitHub UI, and a fresh successful `pre-commit run --all-files` plus `make verify` on the latest head.
