# PR #1623 Fixed in Commit Mapping

## Summary

Hotfix for `tests/guards/test_wellness_language_blockers_guard.py` failure after PR #1621.
The fix adds `pulseplate-allow:blocker-example` inline marker to the exact intentional
forbidden-claim example lines in `APPSTORE_RELEASE_NOTES_TEMPLATE.md`.

## Root Cause

The wellness language blocker guard only skips lines containing the inline marker
`pulseplate-allow:blocker-example`. PR #1621 placed the marker in an HTML comment
above the forbidden-examples section, not on the individual example lines. The guard
therefore continued to scan those lines and failed on two matches:

- Line 172: `"Cure your metabolic issues"` (matched `cures? your`)
- Line 184: `"diagnose your health"` (matched `diagnoses? your`)

## Discussion Thread Pass

No actionable review comments.

## Fixed in Commit Mapping

No actionable review comments

## Validation

- `pytest -q tests/guards/test_wellness_language_blockers_guard.py` — PASS (3/3)
- `pre-commit run --all-files` — PASS (all hooks)
- Bug-hunter scan: no remaining unmarked blocker patterns in `docs/`

## Review Thread Disposition

No actionable review comments at time of artifact creation.
