# Tracking Issue: Complete the managed TestClient train

**Owner:** @Katsiarynakavaleuskaya
**Target lanes:** PR-TC1b, then PR-TC2
**Review-by:** 2026-08-31
**Status:** Open after the PR-TC1a lifecycle foundation

## Problem

PR-TC1a establishes `tests._client.open_test_client(...)` and moves shared
client-fixture ownership to `tests/conftest.py`. Legacy and coverage-only tests
still create `TestClient(app*.app)` directly. Those callers remain behind the
single test-environment compatibility patch until PR-TC2 and can still cause:

- `/metrics` 404 in tests
- Missing middleware/observability wiring
- Hard-to-debug import/env ordering issues

## Goal

Keep the train mechanically separated:

- PR-TC1b adds opt-in function-scoped SQLite isolation without widening TC1a.
- PR-TC2 mechanically replaces direct construction with
  `tests._client.open_test_client(...)` or canonical conftest fixtures.

## Done when

- `tests/test_no_direct_testclient.py` no longer needs `COVERAGE_BOOST_PATTERNS` exclusions
- No remaining `TestClient(app.app)` / `TestClient(app_mod.app)` patterns outside the allowlist
- The root `MetricsAwareTestClient` compatibility assignment is removed
- Deprecated `make_test_client()` and `get_client()` are removed
- The final whole-tree AST guard permits construction only in `tests/_client.py`

## Notes

- Keep changes mechanical and behavior-preserving.
- Prefer per-test client creation/closure to avoid shared state.
- TC1a's four-provider guard is intentionally finite and direct-syntax only. It
  does not resolve arbitrary imports, aliases, reflection, or runtime mutation.
- Function-scoped database isolation belongs exclusively to PR-TC1b.
