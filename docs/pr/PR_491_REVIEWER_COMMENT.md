# PR-491: Reviewer Comment (для GitHub)

## Короткий комментарий для ревьюера

```text
Pure test reorganization following PR-490B. No production code changes.

These core BMI engine internal tests were temporarily colocated in
`test_bmi_visualization_spec.py` during PR-490B to ensure diff-cover visibility.
Now moving them to their canonical location in `test_bmi_engine_helpers.py`
for better test discoverability and separation of concerns.

**What changed:**
- Added `TestBMIBreakpointsFallback` and `TestBMIUpperFor` to `test_bmi_engine_helpers.py`
- Removed same tests from `test_bmi_visualization_spec.py` (lines 397-469)

**Verification:**
- All tests pass
- Coverage maintained (same lines covered)
- No behavior changes
```

---

## Альтернативный вариант (ещё короче)

```text
Test-only reorganization: moving core BMI engine internal tests from
visualization spec file to engine helpers file. No production code changes.

Follow-up to PR-490B where these tests were temporarily placed for diff-cover.
```
