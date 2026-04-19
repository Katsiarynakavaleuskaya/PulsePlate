# PR #1373 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub only after mapping per `AGENTS.md`.

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`

### Scope Notes

- This PR keeps the intended root security updates for `hono` and `@hono/node-server`.
- The branch no longer carries the accidental `frontend` `vite` 8 migration because it breaks `npm ci` against `@storybook/react-vite@8.6.17` peer constraints (`vite "^4 || ^5 || ^6"`).
- Scope remains a dependency-governance repair plus the required Phase 2 artifact/body synchronization for PR `#1373`.

### Local Verification

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `cd frontend && npm ci`
- `cd frontend && npm run build`
- `cd frontend && npm run test:accessibility -- --reporter=junit --outputFile=test-results/accessibility.xml`

## Deferred / Follow-ups

- None at artifact creation time. Add a ledger link here if new review actionables appear or if a follow-up `vite` / Storybook compatibility lane is intentionally deferred.
