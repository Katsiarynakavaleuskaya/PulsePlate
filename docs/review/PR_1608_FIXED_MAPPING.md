<!-- markdownlint-disable MD013 -->
# PR 1608 Fixed in Commit Mapping

## PR

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1608>
- Branch: `codex/web-launch-design-polish-v1`
- Base branch: `main`
- Initial implementation commit: `a4a107590b7fe7801fdb988f32aea6b85539fb7b`
- Status: Ready for review

## Local Validation

Disposition: FIXED
Commit: `a4a107590b7fe7801fdb988f32aea6b85539fb7b`
Evidence:

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json` PASS
- `make tokens-check` PASS
- `npm test -- --run src/__tests__/App.test.tsx src/components/marketing/__tests__/MarketingLaunchPage.test.tsx` PASS
- `npm run build` PASS
- `pre-commit run --all-files` PASS
- commit hooks PASS
- push hooks PASS

## Heavy Gate Caveat

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-web-launch-design-polish-v1`
Reason: Operator-approved machine-heavy deferral for full local `make verify`.
This PR uses focused local web/design gates plus GitHub current-head CI as the
heavy signal. This is not a full local `make verify` pass and must not be
claimed merge-ready until current-head CI parity, review disposition, main
stability, and `check_merge_ready.py --require-auth` pass.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

New human, CodeRabbit, Sourcery, or Cubic actionables must be added below with
one of: `FIXED`, `NOT-A-BUG`, or `DEFERRED`.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1608#issuecomment-4353730237

Disposition: NOT-A-BUG
Evidence: CodeRabbit reported draft/rate-limit status plus optional generated-test checkboxes only; no code, docs, design, or test actionable was posted.
Reason: The PR already includes focused marketing tests and the current-head CodeRabbit status is success. After ready-for-review promotion, CodeRabbit reported `Review completed` with no actionable code, docs, design, or test comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1608#pullrequestreview-4206340444

Disposition: NOT-A-BUG
Evidence: Sourcery reported a weekly diff-character rate limit only; no code, docs, design, or test actionable was posted.
Reason: This is an external review-capacity note, not an implementation request.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1608#pullrequestreview-4206706626

Disposition: NOT-A-BUG
Evidence: Sourcery reported the same weekly diff-character rate limit after ready-for-review promotion; no code, docs, design, or test actionable was posted.
Reason: This is an external review-capacity note, not an implementation request.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1608#discussion_r3169374925 -> 33c2d04a478999f734cc43c0892354ada48d9766

Disposition: FIXED
Commit: 33c2d04a478999f734cc43c0892354ada48d9766
Evidence: `docs/review/PR_1608_FIXED_MAPPING.md` keeps all `## Merge Readiness` checklist boxes unchecked until the final merge cycle.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1608#discussion_r3169374953 -> 33c2d04a478999f734cc43c0892354ada48d9766

Disposition: FIXED
Commit: 33c2d04a478999f734cc43c0892354ada48d9766
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` DoD now explicitly includes CI parity, current-head CI, strict merge wrapper, and main-stability requirements.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1608#pullrequestreview-4206793395 -> 33c2d04a478999f734cc43c0892354ada48d9766

Disposition: FIXED
Commit: 33c2d04a478999f734cc43c0892354ada48d9766
Evidence: All actionable CodeRabbit review comments in this review are mapped to the same post-comment fix commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1608#discussion_r3169374957 -> 33c2d04a478999f734cc43c0892354ada48d9766

Disposition: FIXED
Commit: 33c2d04a478999f734cc43c0892354ada48d9766
Evidence: `frontend/src/components/marketing/__tests__/MarketingLaunchPage.test.tsx` disallowed-claim regex now catches `doctor-recommended` and `doctor recommended` variants.

## Merge Readiness

- [ ] Draft PR opened
- [ ] PR promoted to ready for review
- [ ] Local narrow web/design gates passed
- [ ] Machine-heavy local `make verify` deferral documented
- [ ] PR current-head CI complete after ready-for-review promotion
- [ ] Review/bot actionables disposed
- [ ] Strict merge wrapper PASS after ready-for-review promotion
