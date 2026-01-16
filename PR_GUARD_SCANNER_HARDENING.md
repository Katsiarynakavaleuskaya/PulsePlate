# fix(tests): harden guard scanner docstring tracking and refactor regex

## What

This PR hardens the BMI guard scanner to prevent state-breakable docstring tracking and refactors the regex pattern to eliminate duplication.

## Problem

The previous docstring tracker used a simple toggle that broke on:
- Single-line docstrings: `"""summary"""` → incorrectly entered docstring state and never exited
- This could disable guard scanning for lines immediately after single-line docstrings

## Solution

### 1. Robust Docstring Tracking

Replaced simple toggle with parity-based tracking that:
- Counts triple-quote delimiters and uses parity (odd/even) to determine state changes
- Tracks quote type (`"""` vs `'''`) to prevent mismatched closing
- Handles single-line docstrings correctly (opened+closed same line = no state change)
- Updates docstring state BEFORE `SKIP_LINE_RE` check to ensure proper tracking

### 2. Regex Refactoring

Factored out numeric thresholds pattern to eliminate duplication:
- Created `_NUMERIC_THRESHOLDS` constant
- Used in `BMI_THRESHOLDS_RE` via f-string formatting
- Makes pattern maintenance easier

### 3. Explicit Tests

Added tests for:
- New WHR thresholds (0.90/0.85) — verify they are detected
- Near-miss values (0.89/0.86) — verify they are NOT detected
- Docstring edge cases — verify single-line and multiline docstrings don't break scanning

## Changes

### `tests/test_no_bmi_math_outside_core.py`

- **`_update_docstring_state()`:** New robust implementation with quote type tracking
- **`_scan()`:** Fixed order — update docstring state BEFORE `SKIP_LINE_RE` check
- **`BMI_THRESHOLDS_RE`:** Refactored to use `_NUMERIC_THRESHOLDS` constant
- **New tests:**
  - `test_docstring_tracker_single_line_does_not_disable_scan()`
  - `test_docstring_tracker_multiline_enters_and_exits()`
  - `test_bmi_thresholds_re_matches_new_whr_thresholds()`
  - `test_bmi_thresholds_re_does_not_match_nearby_non_whr_thresholds()`

### `AGENTS.md`

- Added guard scanner requirements:
  - Docstring tracking must not be state-breakable
  - Regex patterns must have explicit tests for new thresholds
  - Docstring state update order requirement

## Verification

- ✅ All guard tests pass
- ✅ New WHR threshold tests pass
- ✅ Near-miss tests pass (verify precision)
- ✅ Docstring tracking tests pass
- ✅ `make test-fast` passes

## Security: CVE-2026-0861 Suppression

Added temporary suppression for unfixed glibc CVE-2026-0861:
- **Status:** UNFIXED upstream in Debian bookworm
- **Suppression expires:** 2026-03-01
- **Documentation:** `docs/security/CVE-2026-0861-glibc.md`
- **Rationale:** System library vulnerability with no fix available. Documented as accepted risk with monitoring.

## Related

- Addresses CodeRabbit/Sourcery findings on guard completeness
- Hardens guard against docstring-based bypass attempts
- Improves maintainability of threshold regex pattern
- Documents unfixed distro CVE (CVE-2026-0861) with expiry
