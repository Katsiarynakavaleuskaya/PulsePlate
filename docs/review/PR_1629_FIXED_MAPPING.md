# PR #1629 Fixed in Commit Mapping

## Summary

PR #1629 fixes the iOS build failure by handling `.consentRequired` in `AIInsightView.swift`.

## Scope

- `ios/PulsePlate/Views/AIInsightView.swift`
- `ios/PulsePlateTests/AIWellnessConsentTests.swift`
- `tests/ios/test_ai_insight_state_exhaustiveness_guard.py`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1629#discussion_r3177030442 -> 4454d3e36
  Disposition: FIXED
  Commit: 4454d3e36
  Evidence: docs/review/PR_1629_FIXED_MAPPING.md (mapping format corrected to canonical `- No actionable review comments`)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1629#discussion_r3177030443 -> c609d3b80
  Disposition: FIXED
  Commit: c609d3b80
  Evidence: docs/review/PR_1629_FIXED_MAPPING.md:12 (`## Discussion Thread Pass` section added)

## Validation

- `pytest -q tests/ios/test_ai_insight_state_exhaustiveness_guard.py` — PASS
- `pytest -q tests/ios/test_ai_wellness_consent_guard.py` — PASS
- `pytest -q tests/ios/` — PASS (32 tests)
- `pytest -q tests/guards/test_wellness_language_blockers_guard.py` — PASS
- `python3 scripts/orchestration/check_preflight.py` — PASS
- `python3 scripts/orchestration/check_agent_consistency.py` — PASS
- `pre-commit run --all-files` — PASS
- `git diff --check` — PASS
