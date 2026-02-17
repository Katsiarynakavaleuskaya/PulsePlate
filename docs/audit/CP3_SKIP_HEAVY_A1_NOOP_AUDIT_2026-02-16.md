# CP3 Skip-Heavy A1 Audit Memo (No-Op)

## Scope

- In scope:
  - `tests/test_remaining_modules.py`
  - `tests/test_zero_coverage_modules.py`
- Out of scope:
  - Runtime modules (`app/`, `core/`)
  - Other test suites
  - Ledger/process updates outside CP3 planning

## Finding

A1 found no skip-protocol drift in the two scoped files.

- All current skip-gating callsites use `require_feature_or_raise(...)`.
- No ad-hoc `pytest.skip(...)` calls were found.
- Skip reasons are emitted via canonical `feature_disabled:<key>`.

## Evidence

Command:

```bash
pytest -q -rs tests/test_remaining_modules.py \
  tests/test_zero_coverage_modules.py | \
  rg -n "SKIPPED|feature_disabled:"
```

Observed output lines:

- `SKIPPED [1] ... feature_disabled:weekly_plan_helpers ...`
- `SKIPPED [3] ... feature_disabled:utils_pack ...`
- `SKIPPED [3] ... feature_disabled:sports_disclaimers_lifestage ...`
- `SKIPPED [5] ... feature_disabled:exports_recipes_products ...`

Command:

```bash
rg -n "require_feature\\(|require_feature_or_raise\\(" \
  tests/test_remaining_modules.py tests/test_zero_coverage_modules.py
```

Observed output lines:

- `tests/test_remaining_modules.py:40` (and subsequent matches) -> `require_feature_or_raise(...)`
- `tests/test_zero_coverage_modules.py:47` (and subsequent matches) ->
  `require_feature_or_raise(...)`

Command:

```bash
rg -n "pytest\\.skip|skip\\(" tests/test_remaining_modules.py \
  tests/test_zero_coverage_modules.py
```

Observed output lines:

- no matches

## File:line anchors

- `tests/test_remaining_modules.py:40`
- `tests/test_remaining_modules.py:116`
- `tests/test_remaining_modules.py:219`
- `tests/test_zero_coverage_modules.py:47`
- `tests/test_zero_coverage_modules.py:92`
- `tests/test_zero_coverage_modules.py:315`

## Decision

- A1 remediation in the current narrow scope is a no-op.
- Do not force synthetic rewrites in these two files.
- Move to CP3 plan hardening with explicit hypotheses, KPI baselines,
  and next-scope stop/go rules before opening any code-changing
  execution PR.

## Risk notes

- Main risk is false progress (rewriting already-canonical code).
- Main control is evidence-first progression: only promote to execution
  PR if expanded audit finds non-canonical skips or contract drift.
