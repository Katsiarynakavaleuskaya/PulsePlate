# PR 1799 Fixed Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1799#discussion_r3293190928
Disposition: NOT-A-BUG
Evidence: tests/test_no_bmi_math_outside_core.py:325, tests/test_no_bmi_math_outside_core.py:357, tests/test_no_bmi_math_outside_core.py:383, tests/test_no_bmi_math_outside_core.py:419, tests/test_no_bmi_math_outside_core.py:441, tests/test_no_bmi_math_outside_core.py:465, tests/test_no_bmi_math_outside_core.py:486; .venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null tests/test_no_bmi_math_outside_core.py -> Success: no issues found in 1 source file
Reason: Current-head test functions already include explicit `-> None` return annotations; the CodeRabbit comment was stale against the updated head.

## Local Findings Resolved Before PR Open

- Security-auditor pre-open false-green finding: traversal errors outside excluded/generated paths must fail closed.
  - Disposition: FIXED
  - Commit: ec532b4a9
  - Evidence: tests/test_no_bmi_math_outside_core.py:229, tests/test_no_bmi_math_outside_core.py:383
- Bug-hunter pre-open false-green finding: read-time source errors must fail closed.
  - Disposition: FIXED
  - Commit: ec532b4a9
  - Evidence: tests/test_no_bmi_math_outside_core.py:302, tests/test_no_bmi_math_outside_core.py:419
- Bug-hunter pre-open false-green finding: transient helper exception must be path-scoped, not basename-only.
  - Disposition: FIXED
  - Commit: 9473538d7
  - Evidence: tests/test_no_bmi_math_outside_core.py:219, tests/test_no_bmi_math_outside_core.py:441, tests/test_no_bmi_math_outside_core.py:465, tests/test_no_bmi_math_outside_core.py:486
- Premortem finding: generic basename pruning could hide future source under build/dist/coverage-like directories.
  - Disposition: FIXED
  - Commit: 9473538d7
  - Evidence: tests/test_no_bmi_math_outside_core.py:58, tests/test_no_bmi_math_outside_core.py:346

## Bounded Check Evidence

```text
python3 scripts/orchestration/check_preflight.py
PASS: All required SoT files present
PASS: worktrees/ not tracked
PASS: agent consistency check
```

```text
python3 scripts/orchestration/check_agent_consistency.py
OK: agent docs and files are consistent.
```

```text
.venv/bin/python -m pytest -q tests/test_no_bmi_math_outside_core.py
...........................                                              [100%]
```

```text
.venv/bin/python -m pytest -q tests/test_no_bmi_math_outside_core.py tests/test_repo_policy_guards.py
.........................................                                [100%]
```

```text
.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null tests/test_no_bmi_math_outside_core.py
Success: no issues found in 1 source file
```

```text
make validate-changed
✅ Diff-based validation completed
```

```text
.venv/bin/python -m pytest -q tests/test_no_bmi_math_outside_core.py::test_no_bmi_formula_outside_core
.                                                                        [100%]
```

```text
pre-commit run --all-files
black (format)...........................................................Passed
ruff (lint, local).......................................................Passed
backend tests (pytest, changed files)....................................Passed
ios syntax check (swift).................................................Passed
```

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-75a941efa308.json`

Status: generated but rejected in isolated oracle environment because allowlisted `python` did not have repo dependencies installed:

```text
ModuleNotFoundError: No module named 'fastapi'
```

## Deferred / Follow-ups

None.

## Merge Readiness

Not merge-ready yet. Current-head CI, post-open role pass, review-thread disposition guard, PR body Phase2 gate, strict merge-readiness wrapper, bot review disposition, and wait-window remain required.
