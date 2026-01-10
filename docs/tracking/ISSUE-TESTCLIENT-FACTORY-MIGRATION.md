# Tracking Issue: Migrate legacy tests to `tests._client.get_client()`

**Owner:** @Katsiarynakavaleuskaya
**Target:** 2026-03-31

## Problem

Some legacy/coverage-boost tests still create `TestClient(app*.app)` directly.
This bypasses canonical bootstrap (`app.main:app`), which can cause:

- `/metrics` 404 in tests
- Missing middleware/observability wiring
- Hard-to-debug import/env ordering issues

## Goal

Replace direct TestClient construction in excluded patterns with one of:

- `tests._client.get_client()`
- Canonical conftest fixtures (e.g., `client`, `test_client`, `client_with_vip_access`)

## Done when

- `tests/test_no_direct_testclient.py` no longer needs `COVERAGE_BOOST_PATTERNS` exclusions
- No remaining `TestClient(app.app)` / `TestClient(app_mod.app)` patterns outside the allowlist

## Notes

- Keep changes mechanical and behavior-preserving.
- Prefer per-test client creation/closure to avoid shared state.
