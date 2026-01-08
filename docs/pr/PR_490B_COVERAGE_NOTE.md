# PR-490B: Coverage Note

## Note: Unrelated Coverage Tail

There is a small unrelated diff-coverage tail (2 lines) from the previously merged PR-490A. It is not a blocker for PR-490B and will be addressed in a tiny follow-up PR.

**Uncovered lines:** `core/bmi/engine.py:257-258, 261` (fallback branches in `_get_bmi_breakpoints()`)

**Follow-up:** PR-490C will add targeted tests for edge combinations that trigger these defensive fallback branches.
