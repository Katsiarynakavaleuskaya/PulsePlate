# PR 1450 Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1450#pullrequestreview-4131529483 -> a76f7720c

Disposition: FIXED
Commit: a76f7720c
Evidence: `app/middleware/api_tiers.py` keeps `require_valid_api_key()` as a header-only dependency factory, `app/routers/feedback.py` depends on `require_valid_api_key()`, and `tests/test_api_tiers.py` / `tests/test_feedback_api.py` cover required-tier factory behavior plus missing, blank, unknown, cookie-only, and query-injected auth cases.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1450#pullrequestreview-4131535011

Disposition: NOT-A-BUG
Evidence: cubic reported "No issues found" for the reviewed PR state; no actionable fix was requested.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1450#issuecomment-4270678635

Disposition: NOT-A-BUG
Evidence: CodeRabbit comment was a rate-limit / review scheduling notice, not a code finding. The branch now includes a real follow-up commit and should be re-reviewed after push.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1450#pullrequestreview-4162761845 -> f1f103381

Disposition: FIXED
Commit: f1f103381
Evidence: `docs/review/PR_1450_FIXED_MAPPING.md` now keeps both Phase 2 checkboxes under `## Discussion Thread Pass` and removes the misplaced checked item from `## Merge Readiness`; `tests/test_feedback_api.py` keeps tier-guard tests status-only and moves auth error payload assertions into a dedicated contract test.

## Merge Readiness

- Local validation:
  - `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1450` passed for the canonical mapping artifact.
  - `. .venv/bin/activate && pytest -q tests/test_feedback_api.py tests/test_api_tiers.py` passed after the CodeRabbit follow-up fixes.
  - `pre-commit run --all-files` passed in the root branch after staging the detect-secrets baseline update.
  - `make verify` passed in sanitized clone `/tmp/pr1450_verify.wD6Uez` with `diff-cover` reporting `100%` coverage for changed lines.
