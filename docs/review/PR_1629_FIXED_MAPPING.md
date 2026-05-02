# PR #1629 Fixed in Commit Mapping

## Summary

PR #1629 fixes the iOS build failure by handling `.consentRequired` in `AIInsightView.swift`.

## Scope

- `ios/PulsePlate/Views/AIInsightView.swift`
- `tests/ios/test_ai_insight_state_exhaustiveness_guard.py`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

No actionable review comments.

## Validation

- `pytest -q tests/ios/test_ai_insight_state_exhaustiveness_guard.py` — PASS
- `pytest -q tests/ios/test_ai_wellness_consent_guard.py` — PASS
- `pytest -q tests/ios/` — PASS (32 tests)
- `pytest -q tests/guards/test_wellness_language_blockers_guard.py` — PASS
- `python3 scripts/orchestration/check_preflight.py` — PASS
- `python3 scripts/orchestration/check_agent_consistency.py` — PASS
- `pre-commit run --all-files` — PASS
- `git diff --check` — PASS
