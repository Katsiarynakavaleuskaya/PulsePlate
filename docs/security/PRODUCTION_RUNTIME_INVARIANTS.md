# Production Runtime Invariants

PulsePlate treats `production`, `prod`, and `staging` as production-like
runtime environments. These environments must fail closed before serving traffic
when local/test security assumptions leak into runtime configuration.

## Enforced Invariants

`app.security.production_invariants.assert_production_runtime_invariants()`
runs from startup guards and from the synthetic CI checker.

Production-like runtime requires:

- `API_KEY_REQUIRED=true`
- `SUBSCRIPTION_DB_ENABLED=true`
- non-placeholder `SERVER_SALT`
- non-placeholder `APPLE_SHARED_SECRET`
- `PRIVATE_EXPORTS_ENABLED=true`
- non-placeholder `EXPORT_TOKEN_SECRET`
- valid PostgreSQL `DATABASE_URL`
- SlowAPI limiter, middleware, and exception handler available and enabled

Production-like runtime rejects:

- `DEBUG=true`
- `TESTING=true`
- `ALLOW_DEV_API_KEY=true`
- `ALLOW_ANONYMOUS_API_KEYS=true`
- `ENABLE_TEST_ROUTES=1`
- `ENABLE_DEBUG_ENDPOINT=true`
- `METRICS_TEST_BYPASS=true`

## CI Evidence

Run the synthetic guard without real production secrets:

```bash
python3 scripts/ci/check_production_runtime_invariants.py --synthetic-production
```

The script builds an in-memory synthetic production profile, verifies it passes,
then verifies representative unsafe toggles fail closed. It does not print
secret values or database URLs.

Evidence anchors:

- `app/security/production_invariants.py:110` defines the production runtime
  invariant entrypoint.
- `app/security/rate_limit.py:312` defines the production rate-limit readiness
  guard.
- `scripts/ci/check_production_runtime_invariants.py:112` runs the synthetic
  safe/unsafe posture checks used by CI.

## Rollback

If a deployment fails this guard, fix the runtime environment rather than
weakening startup behavior. Local/dev/test environments remain explicit
developer environments and may keep local ergonomics such as disabled rate
limiting or local API-key defaults.
