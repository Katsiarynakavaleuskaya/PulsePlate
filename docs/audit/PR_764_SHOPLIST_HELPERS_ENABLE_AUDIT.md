# PR-764 — shoplist_helpers minimal enable audit

## Scope

- Remove `shoplist_helpers` from feature TODO manifest.
- Ensure `core.shoplist` exports required compatibility symbols used by `tests/test_remaining_modules.py`.
- Keep change contract-only, with no added IO/DB/network behavior.

## Evidence (before)

### 1) Feature key usage

Command:

`rg -n 'require_feature_or_raise\(.*"shoplist_helpers"' -S tests`

Output:

- `tests/test_remaining_modules.py:40:            require_feature_or_raise(exc, "shoplist_helpers", reason=FEATURE_REASON)`
- `tests/test_remaining_modules.py:55:            require_feature_or_raise(exc, "shoplist_helpers", reason=FEATURE_REASON)`
- `tests/test_remaining_modules.py:93:            require_feature_or_raise(exc, "shoplist_helpers", reason=FEATURE_REASON)`

### 2) Skip reason in test summary

Command:

`pytest -q -rs tests/test_remaining_modules.py 2>&1 | rg -n "shoplist_helpers|ImportError|ModuleNotFoundError" -n -C 3`

Output:

- `SKIPPED [1] tests/feature_manifest.py:94: feature_disabled:shoplist_helpers (enable via PULSEPLATE_FEATURES=all or CSV). Feature not implemented yet; see BACKLOG_LEDGER (Target PR: PR-738+).`

### 3) Import contract expected by tests

Command:

`nl -ba tests/test_remaining_modules.py | sed -n '1,140p'`

Relevant imports:

- `core.shoplist.PackagingRule`
- `core.shoplist.ShoppingItem`
- `core.shoplist.create_shopping_list`
- `core.shoplist.group_by_category`
- `core.shoplist.optimize_packaging`

## Changes applied

1. `tests/feature_manifest.py`
   - Removed `shoplist_helpers` from `FEATURE_TODO_KEYS`.

2. `core/shoplist.py`
   - Added contract-only helper exports:
     - `create_shopping_list(...)`
     - `group_by_category(...)`
     - `optimize_packaging(...)`
   - Functions are pure helpers and do not introduce IO/DB/network calls.

## Evidence (after)

### 1) Targeted suite status

Command:

`pytest -q -rs tests/test_remaining_modules.py`

Output:

- `.....ssss                                                                [100%]`
- no `feature_disabled:shoplist_helpers` in summary

### 2) Marker absence check

Command:

`pytest -q -rs tests/test_remaining_modules.py 2>&1 | rg -n "feature_disabled:shoplist_helpers" && exit 1 || true`

Output:

- no matches

### 3) Pre-commit status

Command:

`pre-commit run --all-files`

Output:

- all hooks passed (after auto-format rerun)

### 4) Verify gate status

Command:

`make verify`

Observed:

- `flake8` passed
- `mypy` passed (`Success: no issues found in 202 source files`)
- `pytest --lf --maxfail=3 -q` reached ~84% and stalled in this environment during this run

Note:

- PR-764 scoped checks (`tests/test_remaining_modules.py` + skip-marker absence + pre-commit + mypy/lint) are green.
