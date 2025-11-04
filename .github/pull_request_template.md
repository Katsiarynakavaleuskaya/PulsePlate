# Pull Request

## Summary

(Free-form description of changes, e.g., "Fix crash in BMI calculation when height is zero")

- [ ] Change type: bug fix / feature / refactor / docs
- [ ] Linked issues/PRs: #

## Risk & Impact

(User-facing change? Data model/migration? Security- or Performance-sensitive?)

- [ ] User-facing change
- [ ] Data model/migration
- [ ] Security-sensitive
- [ ] Performance-sensitive

## Test Plan

(Unit: small isolated functions; Integration: endpoints/DB; Manual: steps to verify)

- [ ] Unit tests updated/added
- [ ] Integration/slow tests (if applicable)
- [ ] Manual verification steps

## CI Gates

(PR tests must pass; Diff coverage means tests cover changed lines ≥ threshold)

- [ ] PR tests green (lint, type, unit)
- [ ] Diff coverage ≥ 97% on changed lines

## Notes

### For Simple Changes

- How to roll back / feature flag (if needed)

### For Complex/High-Risk Changes

Please fill out the following sections if applicable:

#### Deployment Strategy

- [ ] Deployment order for multi-service changes (if services depend on each other)
- [ ] Feature flag configuration (enable/disable without redeploy)
- [ ] Blue-green / canary deployment plan (if applicable)

#### Database & Data Changes

- [ ] Database migrations required (Alembic version, backwards compatibility)
- [ ] Data migration/backfill steps (scripts, rollback procedures)
- [ ] Data cleanup steps (if removing deprecated data)
- [ ] Backwards compatibility guarantees (old clients still work)

#### Monitoring & Observability

- [ ] New monitoring/alerting rules to add (metrics, thresholds, SLOs)
- [ ] Dashboards to create/update (Grafana, DataDog, etc.)
- [ ] Logging changes (new log levels, structured logs, correlation IDs)
- [ ] Health check endpoints affected

#### Post-Deploy Verification

- [ ] Manual verification checklist (specific endpoints, user flows)
- [ ] Smoke tests to run (automated or manual)
- [ ] Performance benchmarks to verify (latency, throughput)
- [ ] Rollback triggers (what conditions require immediate rollback)

#### Additional Context

- [ ] Breaking changes (API contracts, response formats)
- [ ] Dependencies updated (requirements.txt, package versions)
- [ ] Configuration changes (env vars, secrets, feature toggles)
- [ ] Documentation updates needed (README, API docs, runbooks)
