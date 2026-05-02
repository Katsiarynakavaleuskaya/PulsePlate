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

- Line 172: `"Cure your metabolic issues"` (matched `cures? your`) <!-- pulseplate-allow:blocker-example -->
- Line 184: `"diagnose your health"` (matched `diagnoses? your`) <!-- pulseplate-allow:blocker-example -->

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1623#discussion_r3176619302 -> 58e686106
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1623#discussion_r3176621079 -> 58e686106
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1623#discussion_r3176621082 -> 58e686106
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1623#pullrequestreview-4214926544 -> 58e686106
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1623#pullrequestreview-4214930647 -> 58e686106
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1623#pullrequestreview-4214942234 -> 58e686106
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1623#pullrequestreview-4214943653 -> 58e686106

Disposition: FIXED
Commit: 58e686106
Evidence: docs/review/PR_1623_FIXED_MAPPING.md — artifact format corrected (checkboxes + canonical marker)

## Validation

- `pytest -q tests/guards/test_wellness_language_blockers_guard.py` — PASS (3/3)
- `pre-commit run --all-files` — PASS (all hooks)
- Bug-hunter scan: no remaining unmarked blocker patterns in `docs/`

## Review Thread Disposition

No actionable review comments at time of artifact creation.
