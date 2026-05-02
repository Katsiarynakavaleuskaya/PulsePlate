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

- AI wellness consent runtime gate -> `afe86d91a`
- Consent tests/guards -> `afe86d91a`
- Release docs/backlog update -> `afe86d91a`

## Validation

- `pytest -q tests/ios/test_ai_wellness_consent_guard.py` — 7/7 PASS
- `pytest -q tests/ios/` — 33/33 PASS
- `pytest -q tests/guards/test_wellness_language_blockers_guard.py` — PASS
- `pre-commit run --all-files` — PASS

## Review Thread Disposition

Populate after CodeRabbit, Sourcery, and Cubic reviews complete.
