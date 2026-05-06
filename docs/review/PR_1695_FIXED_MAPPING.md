# PR 1695 Fixed in Commit Mapping

## PR

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1695

## Summary

Fixes the BMI guard false positive where `normalized_score >= 0.85` in design scorecard tooling was incorrectly detected as BMI/WHR threshold context.

## Fixed in Commit Mapping

- Guard context matching made token-aware and separator-aware: `8f7b2e11b`
- Regression coverage for design scorecard `normalized_score` false positive and real BMI/WHR threshold examples: `f82ade615`
- Sourcery mixed-case / number-before-context BMI regression coverage: `843b66c1e`

## Review Dispositions

- Disposition: FIXED
- Evidence:
  - `tests/test_no_bmi_math_outside_core.py` now uses explicit BMI/WHR threshold context matching.
  - `tests/test_no_bmi_math_outside_core.py` covers `normalized_score >= 0.85` as non-BMI scorecard context.
  - `tests/test_no_bmi_math_outside_core.py` preserves real BMI/WHR examples, including snake_case identifiers.

## Premortem Findings

- Security/QA finding: identifier-style BMI/WHR thresholds such as `BMI_THRESHOLD = 25.0` and `WHR_THRESHOLD: float = 0.90` must not bypass the guard.
- Disposition: FIXED
- Commit: `f82ade615`
- Evidence: focused regression cases in `tests/test_no_bmi_math_outside_core.py`.

## Bot Review Findings

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1695#pullrequestreview-3449071804 -> `843b66c1e`
  - Disposition: FIXED
  - Evidence: `tests/test_no_bmi_math_outside_core.py` adds number-before-context and mixed-case BMI threshold examples.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 -m pytest -q tests/test_no_bmi_math_outside_core.py::test_no_bmi_thresholds_outside_core` via repo `.venv`
- `python3 -m pytest -q tests/test_no_bmi_math_outside_core.py` via repo `.venv`
- `python3 -m pytest -q tests/design/test_design_scorecard.py` via repo `.venv`
- `python3 scripts/design/design_scorecard.py score docs/design/screen_evidence/examples/web_marketing.sample.json` via repo `.venv`
- `python3 scripts/design/design_scorecard.py score docs/design/screen_evidence/examples/ios_home.sample.json` via repo `.venv`
- `make validate-changed`
- `make design-guard`
- `make tokens-check`
- `pre-commit run --all-files`

Full `make verify` was not run for this narrow main-hotfix lane.

## Deferred / Follow-ups

- PR-6 iOS visual parity audit remains separate and must not start until this main fix is merged.
- Any future BMI guard tuning must preserve the One BMI Engine invariant.
