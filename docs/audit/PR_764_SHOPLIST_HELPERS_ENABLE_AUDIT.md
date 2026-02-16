# PR-764 — shoplist_helpers minimal enable audit

<!-- markdownlint-disable MD013 MD032 MD060 -->

## Scope (PR-764, historical)

- Enable `shoplist_helpers` contract path (minimal, contract-only).
- Ensure `core.shoplist` exports compatibility symbols consumed by `tests/test_remaining_modules.py`.
- No new IO/DB/network behavior.

## Scope width assessment

PR-764 was intentionally narrow and valid as a compatibility unblocker, but it is not a full user flow.
For follow-up delivery, scope should move from "helpers only" to one value package:
`plan -> shoplist` with contract + integration guarantees.

## Evidence (before)

### 1) Feature key usage

Command:

```bash
rg -n 'require_feature_or_raise\(.*"shoplist_helpers"' -S tests
```

Output:

```text
tests/test_remaining_modules.py:40: require_feature_or_raise(
    exc, "shoplist_helpers", reason=FEATURE_REASON
)
tests/test_remaining_modules.py:55: require_feature_or_raise(
    exc, "shoplist_helpers", reason=FEATURE_REASON
)
tests/test_remaining_modules.py:93: require_feature_or_raise(
    exc, "shoplist_helpers", reason=FEATURE_REASON
)
```

### 2) Skip reason in test summary

Command:

```bash
pytest -q -rs tests/test_remaining_modules.py 2>&1 | rg -n \
  "shoplist_helpers|ImportError|ModuleNotFoundError" -n -C 3
```

Output:

```text
SKIPPED [1] tests/feature_manifest.py:94:
feature_disabled:shoplist_helpers (enable via PULSEPLATE_FEATURES=all or CSV).
Feature not implemented yet; see BACKLOG_LEDGER (Target PR: PR-738+).
```

### 3) Import contract expected by tests

Command:

```bash
nl -ba tests/test_remaining_modules.py | sed -n '1,140p'
```

Relevant imports:

- `core.shoplist.PackagingRule`
- `core.shoplist.ShoppingItem`
- `core.shoplist.create_shopping_list`
- `core.shoplist.group_by_category`
- `core.shoplist.optimize_packaging`

## Changes applied

1. `tests/feature_manifest.py`
   - Kept `shoplist_helpers` in `FEATURE_TODO_KEYS` to preserve
     `require_feature_or_raise(...)` behavior on future import regressions.

2. `core/shoplist.py`
   - Added contract-only helper exports:
     - `create_shopping_list(...)`
     - `group_by_category(...)`
     - `optimize_packaging(...)`
   - Functions are pure helpers and do not introduce IO/DB/network calls.

## Evidence (after)

### 1) Targeted suite status

Command:

```bash
pytest -q -rs tests/test_remaining_modules.py
```

Output:

- `.....ssss                                                                [100%]`
- No `feature_disabled:shoplist_helpers` in summary.

### 2) Marker absence check

Command:

```bash
bash -lc 'set -o pipefail; pytest -q -rs \
tests/test_remaining_modules.py 2>&1 | \
rg -n "feature_disabled:shoplist_helpers"; echo "exit_code=$?"'
```

Output:

```text
# (no matches)
exit_code=1
```

### 3) Pre-commit status

Command:

```bash
pre-commit run --all-files
```

Output:

- All hooks passed (after auto-format rerun).

## Corrections and policy-aligned wording

1. Verify/test-fast wording:
   - Do not describe readiness via partial/legacy `pytest --lf` behavior.
   - Canonical readiness wording is: `make verify` (lint -> typecheck -> test-fast -> diff-cov).
   - `test-fast` is deterministic and must not rely on last-failed cache.

2. "Green" wording:
   - Do not claim "merge-ready" unless required gates are complete and review threads/actionables are closed.

3. Flow-level outcome:
   - PR-764 is correctly documented as contract-only enablement.
   - Full runtime value package (`plan -> shoplist`) is a separate follow-up and should include contract + integration + negative tests.

## Gap register for next work-package

- Flow-level contract assertions are not yet defined (`plan -> shoplist`).
- Integration coverage still requires one deterministic end-to-end happy path.
- A deterministic negative-path matrix for validation and auth/tier behavior is still pending.

## Follow-up recommendation

Use a single runtime work-package PR for flow stabilization with strict IN/OUT boundaries:

- IN: flow wiring, contract tests, integration happy path, negative tests, deterministic behavior.
- OUT: AI/RAG endpoints, unrelated frontend/iOS work, CVE/security suppression changes, broad refactors.

<!-- markdownlint-enable MD013 MD032 MD060 -->

- PR-764 scoped checks (`tests/test_remaining_modules.py` +
  skip-marker absence + pre-commit + mypy/lint) are green.

## Merge status

- Merged SHA: `48c87f39`
- CI: required checks passed at merge time for PR-764.
