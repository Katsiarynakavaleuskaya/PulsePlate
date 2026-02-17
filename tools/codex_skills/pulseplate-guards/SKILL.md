---
name: pulseplate-guards
description: Triage and fix PulsePlate guard failures for architecture, import hygiene, and thin-client policies.
---

# PulsePlate Guards

<!-- markdownlint-disable MD013 -->

## When to use

- Guard tests fail locally or in CI.
- You need quick diagnosis of policy violations.
- PR touches guard-sensitive areas (imports, BMI logic, client adapters).

## Inputs required

- Failing guard command output.
- Changed file list.
- Target stack area (backend/web/iOS/tests).

## Procedure (commands)

1. Run primary guard suite:

   ```bash
   pytest -q tests/test_repo_policy_guards.py
   ```

2. Run focused policy guards as needed:

   ```bash
   pytest -q tests/test_no_bmi_math_outside_core.py
   pytest -q tests/test_import_hygiene_guard.py
   cd frontend && npm test -- --run src/api/__tests__/thin-client-guards.test.ts && cd ..
   ```

3. Inspect common violation patterns:

   ```bash
   rg -n "sys\\.modules\\[|spec_from_file_location|exec_module\\(" app core tests providers
   rg -n "\\b(18\\.5|24\\.9|25|30|80|88|94|102|0\\.95|0\\.80|0\\.90|0\\.85)\\b" app legacy_app.py frontend ios
   ```

## Output format

- `Failed guards`: command + status.
- `Root causes`: grouped by policy category.
- `Pointers`: `file:line:error` list.
- `Fix plan`: minimal remediation steps.
- `Rerun`: exact guard commands.

## Guardrails

- Never skip or xfail required guard tests to get green.
- Never patch around architecture violations without root-cause fix.
- Never mutate `sys.modules` as a workaround.

## SoT links

- `tests/AGENTS.md`
- `AGENTS.md`
- `tests/test_repo_policy_guards.py`
- `tests/test_no_bmi_math_outside_core.py`
- `frontend/src/api/__tests__/thin-client-guards.test.ts`
