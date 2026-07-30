# Tracking Issue: Complete the managed TestClient migration in PR-TC2

**Owner:** @Katsiarynakavaleuskaya
**Target PR:** PR-TC2
**Review-by:** 2026-08-31
**Status:** Open after TC1 foundation

## Problem

TC1 establishes `tests._client.open_test_client(...)` and moves shared fixture
ownership to `tests/conftest.py`. Legacy and coverage-only tests still create
`TestClient(app*.app)` directly. Those callers remain behind the single
test-environment compatibility patch until PR-TC2 and can still cause:

- `/metrics` 404 in tests
- Missing middleware/observability wiring
- Hard-to-debug import/env ordering issues

## Goal

PR-TC2 mechanically replaces direct construction with one of:

- `tests._client.open_test_client(...)`
- Canonical conftest fixtures (e.g., `client`, `test_client`, `client_with_vip_access`)

## Done when

- `tests/test_no_direct_testclient.py` no longer needs `COVERAGE_BOOST_PATTERNS` exclusions
- No remaining `TestClient(app.app)` / `TestClient(app_mod.app)` patterns outside the allowlist
- The root `MetricsAwareTestClient` compatibility assignment is removed
- Deprecated `make_test_client()` and `get_client()` are removed
- The final whole-tree AST guard permits construction only in `tests/_client.py`

## Notes

- Keep changes mechanical and behavior-preserving.
- Prefer per-test client creation/closure to avoid shared state.
- TC1's four-provider AST guard is intentionally finite; it is not a
  whole-tree migration claim.
- TC1 credits only the direct module-qualified fixture call and the direct
  local helper call. CPython `symtable` owns lexical-name stability; this guard
  does not model dynamic imports, reflection, or arbitrary runtime mutation.
  PR-TC2 owns the final whole-tree guard after the compatibility bridge is
  removed.
