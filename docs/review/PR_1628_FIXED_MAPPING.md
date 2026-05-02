# PR #1628 Fixed in Commit Mapping

## Summary

PR #1628 gates first iOS AI wellness insight request behind explicit user consent.

## Scope

- `AIWellnessConsentStore` (protocol + UserDefaults impl)
- `AIWellnessDisclosureSheet` (wellness-only disclosure view)
- `AIInsightViewModel` consent gate in `submit()`
- `AIInsightView` sheet for consent
- Localization keys `ai_consent.*` in en/ru/es
- `AIWellnessConsentTests` (Swift) + `test_ai_wellness_consent_guard.py` (Python)
- Epic doc + backlog ledger updates

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1628#discussion_r3176900098 -> daced8d44
  Disposition: FIXED
  Commit: daced8d44
  Evidence: docs/review/PR_1628_FIXED_MAPPING.md (mapping format updated per Cubic)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1628#discussion_r3176902038 -> daced8d44
  Disposition: FIXED
  Commit: daced8d44
  Evidence: docs/review/PR_1628_FIXED_MAPPING.md (evidence added per CodeRabbit)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1628#discussion_r3176902042
  Disposition: NOT-A-BUG
  Evidence: `awaitState` uses the same polling pattern as `AIInsightViewModelTests.awaitEventuallyState` (stable in CI). Both use 200-iteration yield loop with final sleep.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1628#discussion_r3176902043
  Disposition: NOT-A-BUG
  Evidence: Guard tests are structural (file scanning), not behavioral. Submit ordering is tested by `AIWellnessConsentTests.test_submit_withoutConsent_setsConsentRequired` (Swift).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1628#discussion_r3176902044 -> daced8d44
  Disposition: FIXED
  Commit: daced8d44
  Evidence: `tests/ios/test_ai_wellness_consent_guard.py:68` (now checks en/ru/es locales)

## Validation

- `pytest -q tests/ios/test_ai_wellness_consent_guard.py` — 7/7 PASS
- `pytest -q tests/ios/` — 33/33 PASS
- `pytest -q tests/guards/test_wellness_language_blockers_guard.py` — PASS
- `pre-commit run --all-files` — PASS
