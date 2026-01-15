# fix(bmi): post-merge CodeRabbit findings (guards, typing, docs)

## What

This PR addresses CodeRabbit findings that arrived after PR #535 was merged.

## Scope

- **Guard completeness**: Expand WHR threshold regex to include simple-tier values (0.90/0.85)
- **Test typing compliance**: Add `-> None` return type annotation
- **Documentation accuracy**: Fix Pro tier imports in remediation patches doc
- **API contract clarification**: Document `interpret_wht_ratio` English-only policy
- **CI fix**: Fix GHCR login in cd-test workflow (use `repository_owner` instead of `actor`)

## Changes

### 1. Guard regex expansion (`tests/test_no_bmi_math_outside_core.py`)

- Added `0.90|0.85` to `BMI_THRESHOLDS_RE` pattern (simple-tier WHR thresholds)
- Improved docstring detection to skip multiline docstrings (prevents false positives)

### 2. Test typing (`tests/test_bmi_pro_adapter_coverage.py`)

- Added `-> None` return type to `test_adapt_pro_stage_to_response_stage_mapping`

### 3. Documentation fix (`docs/audit/PR_REMEDIATION_EXACT_PATCHES_CONSOLIDATED.md`)

- Updated doc snippet to use correct Pro tier imports from `core.bmi_extras`
- Removed incorrect `_compute_bmi` import example

### 4. API contract clarification (`core/bmi_extras.py`)

- Documented that `interpret_wht_ratio` description field is English-only by design
- Clarified that `lang` parameter is kept for API compatibility but not used for localization
- Added note that `category`/`risk` fields use English keys for stable identifiers

### 5. CI fix (`github/workflows/cd-test.yml`)

- Changed GHCR login username from `github.actor` to `github.repository_owner` (consistent with deploy)
- Added `set -euo pipefail` for better error handling
- Fixes "denied: denied" error when pulling from GHCR

## No Functional Regression

- No change to BMI Engine invariant
- No breaking API changes
- All existing tests pass
- Guard tests pass with improved docstring detection

## Related

- Supersedes: PR #534 (closed as superseded)
- Follow-up to: PR #535 (P0 remediation)
