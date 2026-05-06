# PR #1674 Fixed Mapping

## Summary

PR #1674 is a bounded visible frontend follow-up after merged PR #1608.

It tightens the public launch shell at `/` and `/marketing` without changing backend,
OpenAPI, auth, billing, iOS, `/tokens`, generated token mirrors, Figma, Canva, Storybook
configuration, or external reference intake.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

GitHub review threads were inspected and mapped below. Future CodeRabbit, Sourcery, Cubic,
human, or CI findings must be added here with disposition evidence before threads are
resolved.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1674#discussion_r3193941462 -> 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Disposition: FIXED
Commit: 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now says PR #1608 fixed mapping recorded the focused frontend tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1674#discussion_r3193946860 -> 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Disposition: FIXED
Commit: 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` keeps `ledger-p1-web-launch-design-polish-v1` open and records same-day docs-only closeout after PR #1674.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1674#discussion_r3193963595 -> 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Disposition: FIXED
Commit: 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Evidence: `docs/review/PR_1674_FIXED_MAPPING.md` now places the required checked boxes directly under `## Discussion Thread Pass`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1674#discussion_r3193963624 -> 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Disposition: FIXED
Commit: 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` keeps the web launch polish item open for docs-only closeout after this mixed-scope PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1674#pullrequestreview-4234339257 -> 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Disposition: FIXED
Commit: 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Evidence: Sourcery grammar finding addressed in `docs/roadmap/BACKLOG_LEDGER.md`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1674#pullrequestreview-4234373012 -> 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Disposition: FIXED
Commit: 9bc395ec2f76d9a69f559a456785ef295bc02bdc
Evidence: CodeRabbit actionable comments are mapped above with fix commit evidence.

## Internal Review Findings

### Pre-Open Review Findings

- Premortem: backlog closeout needed durable evidence instead of a branch assertion.
  - Disposition: FIXED
  - Commit: `58f36ee3b`
  - Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now cites PR #1608 merged on
    2026-04-30 with merge SHA `25d5cb954b11278700bf399434b98338b6a501b6`, PR #1608
    validation evidence, and this branch's route sanity evidence.

- Frontend/design review: mobile hero title override used viewport-based font scaling.
  - Disposition: FIXED
  - Commit: `58f36ee3b`
  - Evidence: `frontend/src/components/marketing/marketing.css` uses a stable
    `2.6rem` mobile hero title size.

### External Review Threads

None yet.

## Local Evidence

Passed locally:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open`
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review`
- `npm --prefix frontend run test -- --run src/components/marketing/__tests__/MarketingLaunchPage.test.tsx src/__tests__/App.test.tsx`
- `npm --prefix frontend run build`
- `npm --prefix frontend run test:accessibility`
- `make validate-changed`
- `make design-guard`
- `make tokens-check`
- `pre-commit run --all-files`
- Playwright route sanity for `/` and `/marketing`: title/H1 present,
  `marketing-page=1`, `tabBar=0`, `horizontalOverflowPx=0`, no page/console errors.
- Generated token mirror diff check returned empty output for:
  - `frontend/src/styles/tokens.css`
  - `frontend/src/styles/tokens.ts`
  - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`

Not run:

- Full local `make verify`, by operator machine-budget decision for this lane. Merge
  readiness must rely on current-head CI, review-bot pass/no-actionables, this fixed
  mapping artifact, thread dispositions, and the wait-window.

## Merge Readiness

Not claimed.

Current-head CI, external review bots, review-thread disposition, and mandatory wait-window
must complete before any merge-readiness claim.

## Deferred / Follow-Ups

- Design Intelligence PR-1 DESIGN.md generator remains separate.
- External reference manifest tooling remains separate.
- Screen evidence pack remains separate.
- Design scorecard remains separate.
- iOS visual parity remains separate.
