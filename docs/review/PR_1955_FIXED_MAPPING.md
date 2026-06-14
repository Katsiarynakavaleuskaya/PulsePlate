# PR 1955 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1955
Branch: `codex/fix-public-shadow-reads-vulnerability`
Local reviewed head: `ad43007d95f2e655d9df9626c168e0ac9b2eda67`
Task packet: `artifacts/orchestration/task_packets/257279560c6f.json`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1955#discussion_r3399232220 -> 979f999e882a7265513628238ecfe5bbfaae8762
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1955#pullrequestreview-4480674103 -> 979f999e882a7265513628238ecfe5bbfaae8762
Disposition: FIXED
Commit: 979f999e882a7265513628238ecfe5bbfaae8762
Evidence: `app/routers/restaurants.py` now protects shadow-read circuit state with `RLock`, records attempt-start timestamps, and only clears an older circuit; `tests/test_restaurants_router.py` covers stale success, longer cooldown preservation, search/menu circuit skips, and fail-open behavior; focused pytest and diff-cover passed.
Reason: cubic identified that a concurrent successful shadow read could clear a newer failure cooldown; the fix prevents stale success from nullifying the failure window while preserving SQLite as canonical.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1955#issuecomment-4685147271
Disposition: NOT-A-BUG
Evidence: The comment body says the Codex connector reached code-review usage limits and gives account/billing settings; it names no code path, file, line, test, or remediation request.
Reason: This is an external capacity notice, not an actionable code review finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1955#issuecomment-4685147525
Disposition: NOT-A-BUG
Evidence: The CodeRabbit comment states review limit reached and selected files for processing; it did not start a review and contains no concrete code finding.
Reason: This is a rate-limit/capacity notice. The optional finishing-touch checkboxes are not review findings and do not override the deterministic tests added in this PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1955#pullrequestreview-4480656944
Disposition: NOT-A-BUG
Evidence: Sourcery review body says the weekly diff-character rate limit was reached and asks to try later or upgrade; it contains no file/line/code finding.
Reason: This is a Sourcery capacity notice, not a code finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1955#issuecomment-4691107752
Disposition: NOT-A-BUG
Evidence: Codecov reported patch coverage at 99.01961%; current-head `codecov/patch` passed; current-head `diff-coverage` passed; focused local diff-cover reported `Coverage: 100%`.
Reason: This is a non-blocking partial-line coverage advisory above the repo threshold, not an actionable missing-test blocker for this PR.

## Internal Finding Dispositions

- Disposition: FIXED
  Source: `qa-engineer-agent` post-open review.
  Evidence: QA found diff-cover at 95% with uncovered changed lines in `app/routers/restaurants.py` and `app/services/restaurant_postgres_read.py`; commit `ad43007d95f2e655d9df9626c168e0ac9b2eda67` added deterministic coverage. Rerun evidence: diff-cover reported `Coverage: 100%` for 102 changed lines.
  Reason: Test coverage was expanded before mapping and before any readiness claim.

- Disposition: FIXED
  Source: `bug-hunter` post-open review.
  Evidence: Bug-hunter flagged missing CI-visible tail wrappers for the new circuit tests; commit `ad43007d95f2e655d9df9626c168e0ac9b2eda67` added tail wrappers for stale success preservation, longer cooldown preservation, and search circuit skip. Rerun evidence: bug-hunter PASS on local head `ad43007d9`.
  Reason: Route-shard false-green risk was closed with CI-visible test forwarding.

- Disposition: FIXED
  Source: `pulseplate-pr-review` dry-run report.
  Evidence: Initial dry-run reported missing `docs/review/PR_1955_FIXED_MAPPING.md`; this artifact supplies the canonical mapping and will be mirrored in the PR body.
  Reason: Governance artifact was intentionally created after code/test fixes and review passes.

## Role Dispatch Evidence

- Startup preflight passed with scoped paths:
  `python3 scripts/orchestration/check_preflight.py --path app/routers/restaurants.py --path app/services/restaurant_postgres_read.py --path tests/test_restaurant_postgres_read.py --path tests/test_restaurants_router.py --path tests/test_app_extended_coverage.py --path docs/review/PR_1955_FIXED_MAPPING.md`
- Agent consistency passed:
  `python3 scripts/orchestration/check_agent_consistency.py`
- Bootstrap packet created:
  `python3 scripts/orchestration/task_bootstrap.py --goal "PR 1955 post-open security rescue for restaurant PostgreSQL shadow reads and merge governance" --task-class security ... --pr-phase post_open_review`
- Dispatch manifest enforced non-parallel role order:
  `agent-coordinator -> backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`
- Pre-implementation role passes completed in order and found the same narrow scope.
- Post-open role passes completed on local head `ad43007d9`:
  `qa-engineer-agent` PASS, `bug-hunter` PASS, `security-auditor` PASS.

## Premortem And Security Evidence

- Premortem finding: stale success could clear newer failure circuit. Disposition: FIXED by `979f999e882a7265513628238ecfe5bbfaae8762`.
- Premortem finding: coverage-tail state leakage and stale test wrappers could hide regressions. Disposition: FIXED by `979f999e882a7265513628238ecfe5bbfaae8762` and `ad43007d95f2e655d9df9626c168e0ac9b2eda67`.
- Experiment Runner oracle result: `exp-9757993a7a1c`, status `accepted`; focused pytest and py_compile returned 0 in oracle-only governance reviewer mode.
- Codex Security diff scan: no findings; validated report at `/tmp/codex-security-scans/BMI-App_2025_clean/ad43007d9_20260612T113548Z/report.md`; rendered report at `/tmp/codex-security-scans/BMI-App_2025_clean/ad43007d9_20260612T113548Z/report.html`.
- `pulseplate-pr-review` initial dry-run produced only missing-mapping governance notes; this artifact closes that note.
- `pulseplate-pr-review` rerun after creating this artifact reported: `No deterministic findings from supplied context`.

## Local Validation Evidence

- PASS: `. .venv/bin/activate && pytest -q tests/test_restaurant_postgres_read.py tests/test_restaurants_router.py tests/test_app_extended_coverage.py::TestRestaurantShadowReadCoverageTail`
- PASS: `python3 -m py_compile app/routers/restaurants.py app/services/restaurant_postgres_read.py tests/test_restaurant_postgres_read.py tests/test_restaurants_router.py tests/test_app_extended_coverage.py`
- PASS: `git diff --check`
- PASS: `diff-cover /tmp/pr1955-coverage.xml --compare-branch=origin/main --fail-under=97` reported `Coverage: 100%`.
- PASS: `DEV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
- PASS: `PRE_COMMIT_HOME=/tmp/pre-commit-pr1955 pre-commit run --all-files`
- Pending before merge-readiness claim: PR body Phase2 gates after PR-body edit, review-thread disposition strict gate after thread resolution, merge-readiness strict gate, and current-head CI.

## Merge Readiness

- [x] Code/test fix landed before mapping.
- [x] Fixed-mapping artifact created after the code/test fix.
- [x] Full local `make verify` intentionally deferred per operator machine-heavy exception.
- [ ] PR body mirror updated after this artifact.
- [x] Required narrow local gates completed after mapping.
- [ ] Current-head CI green after push.
- [ ] Strict merge-readiness gate passes with `--require-auth`.
- [ ] No unresolved or actionable review threads remain.
