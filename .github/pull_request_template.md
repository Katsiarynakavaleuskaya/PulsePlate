# Pull Request

## Summary

(Free-form description of changes, e.g., "Fix crash in BMI calculation when height is zero")

- [ ] I reviewed `docs/ENGINEERING_LESSONS.md` and followed repo policies (determinism, import hygiene, contracts).
- [ ] Select one change type:
  - [ ] Bug fix
  - [ ] Feature
  - [ ] Refactor
  - [ ] Docs
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

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping

- `<review-comment-url>` -> `<commit-sha>`
- No actionable review comments

## Deferred / Follow-ups

- [ ] Ledger item(s): <link to docs/roadmap/BACKLOG_LEDGER.md entry or "None">
- [ ] GitHub issue(s): <link> (if any)

## Notes

### For Simple Changes

Use this checklist to confirm the PR is truly simple:

- [ ] No database/schema/migration changes
- [ ] No public API contract changes (endpoints, request/response, events)
- [ ] Covered by existing tests (or adds ≤ 1-2 focused unit tests)
- [ ] < 50 LOC changed (excluding tests/docs)
- [ ] No performance or security impact

Example: Copy change in docs, minor log level tweak, small refactor of a pure function.

Rollback / Feature flag (brief):

- How to revert: describe the commit to revert or config to change
- Feature flag/toggle (if any): name and how to disable
- Owner for emergency contact: @username

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
