# PR 1581 Fixed in Commit Mapping

## PR

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581>
- Branch: `codex/design-accessibility-motion-state-contract`
- Base observed at draft open: `2266d37b2026098e970cec365f28e5f5a9930bc5`
- Implementation commit: `8211fe345`

## Local Validation

Disposition: FIXED
Commit: `8211fe345`
Evidence:

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `pytest -q tests/test_repo_policy_guards.py` PASS
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json` PASS
- `cd frontend && npm test -- --run src/components/ui/__tests__/Button.test.tsx src/components/ui/__tests__/Skeleton.test.tsx src/components/ui/__tests__/EmptyState.test.tsx src/components/ui/__tests__/ProgressIndicator.test.tsx` PASS, 26 tests
- `cd frontend && npm test -- --run src/components/ui/__tests__/EmptyState.test.tsx` PASS, 10 tests
- `cd frontend && npm run build` PASS
- `make ios-test IOS_DESTINATION='platform=iOS Simulator,id=3DA1887F-A91D-4D32-A49F-C96D82F7C4B6'` PASS, 90 tests
- `pre-commit run --all-files` PASS
- `make verify` PASS

## Base Gate Caveat

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`
Reason: Draft PR opening was operator-approved while live `main` canonical `CI`
for `2266d37b2026098e970cec365f28e5f5a9930bc5` was `failure`. This is not a
merge-readiness claim. Merge readiness remains blocked until current-head `main`
and PR CI are green and the strict merge wrapper passes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

CodeRabbit actionables were reviewed after the PR moved out of draft. New
human, CodeRabbit, Sourcery, or Cubic actionables must be added below with one
of: `FIXED`, `NOT-A-BUG`, or `DEFERRED`.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#issuecomment-4347346486 -> 63006f30b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#discussion_r3163753147 -> 63006f30b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#discussion_r3163753152 -> 63006f30b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#pullrequestreview-4200233929 -> 63006f30b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#pullrequestreview-4200620769 -> 9be23bc8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#discussion_r3164028059 -> 03ea929c1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#pullrequestreview-4200740579 -> 03ea929c1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#pullrequestreview-4200818100 -> a7e8f24d6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1581#discussion_r3164251798 -> a7e8f24d6

Disposition: FIXED
Commit: `a7e8f24d6`
Evidence: `docs/design/ACCESSIBILITY_MOTION_STATE_CONTRACT.md` uses `reduced-motion-aware`; `frontend/src/components/ui/Skeleton.tsx` preserves governed ARIA status props; `frontend/src/components/ui/EmptyState.tsx` only renders the `Start Tracking` CTA when `onStartTracking` is provided, uses an explicit retry handler, and avoids duplicate live-region attributes for `role="alert"`; `frontend/src/components/ui/__tests__/ProgressIndicator.test.tsx` uses `previousElementSibling`; `frontend/src/components/ui/__tests__/EmptyState.test.tsx` covers loading status semantics, container-scoped skeleton queries, and callback execution for built-in `Start Tracking` and `Retry` actions; this artifact includes `## Merge Readiness`.

## Merge Readiness

- [ ] No unresolved review threads
- [ ] Required checks PASS on the PR current head
- [ ] Current-head `main` CI PASS
- [ ] Strict merge wrapper PASS
- [ ] Required wait window observed
