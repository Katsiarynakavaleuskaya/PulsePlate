# PulsePlate Deploy Web Diagnosis And Fix

**Date:** 2026-03-31
**Priority:** P0 deploy/runtime shell parity
**Status:** Active canonical diagnosis anchor for PR-2 (`fix(deploy): restore SPA routing and production web shell`)

## Executive Summary

PR-2 is narrower than the earlier broad deploy packet implied.

Current repo truth already shows the intended production model is:

1. Caddy serves the SPA from **`/srv/frontend`**, not `/app/frontend/dist`.
2. Deep-link fallback is already expressed with **`try_files {path} /index.html`**.
3. Dynamic surfaces are already explicitly separated from SPA routing via dedicated legacy and `@api` matchers.

The real gap for PR-2 is therefore not "invent a new production topology", but:

1. Formalize deterministic shell diagnosis (`scripts/diagnose_web.sh`).
2. Ensure operator workflows call that diagnosis after Caddy redeploy.
3. Reconcile deploy docs with the actual baked-shell contract and remove stale assumptions from this diagnosis file itself.

## Current Repo Truth

### Edge routing truth

`deploy/Caddyfile.production` already contains the expected split:

- Legacy POST/OPTIONS/GET dynamic surfaces are proxied to FastAPI.
- `@api` includes `/api*`, `/health*`, `/ready`, `/metrics`, `/ws*`, docs, and `/legacy*`.
- SPA fallback is handled by:

```caddyfile
handle {
    root * /srv/frontend
    try_files {path} /index.html
    file_server
}
```

### Frontend artifact truth

`frontend/Dockerfile.caddy-spa` is already the canonical artifact builder:

- build stage: Vite outputs `dist`
- runtime stage: copies `dist` into **`/srv/frontend`**

This means PR-2 should preserve `/srv/frontend` unless hard evidence disproves it.

### Compose/runtime truth

`deploy/docker-compose.production.yaml` already builds the `caddy` service from
`frontend/Dockerfile.caddy-spa` and does not depend on a shared `frontend_dist`
volume. This is consistent with the baked-shell image model and inconsistent
with the earlier draft diagnosis that assumed a shared runtime volume.

## Diagnosis

The earlier diagnosis packet mixed three different concerns:

1. SPA shell routing
2. staging/CD gate posture (`WEB_IOS_RELEASE_READY`, staging fallback host)
3. PostgreSQL production promotion

After PR-1, item 3 is already resolved in its own lane and must not be re-opened
in PR-2.

For PR-2, the remaining deploy-shell problem is best framed as **contract drift**:

- runtime config already encodes the correct SPA and API split
- operator evidence tooling was missing
- docs still described older or wider topologies

## In Scope For PR-2

PR-2 must do the following:

1. Keep the current Caddy routing split intact:
   - SPA deep routes return `200` and serve the shell
   - `/api*`, `/ws*`, `/health*`, `/ready`, docs, and legacy surfaces do not fall through to SPA
2. Preserve one canonical frontend artifact path centered on `/srv/frontend`
3. Add/formalize `scripts/diagnose_web.sh`
4. Update deploy/operator docs so they point to the real baked-shell model
5. Add deterministic repo-side verification for the diagnosis and redeploy flow

## Explicitly Out Of Scope For PR-2

The following are intentionally deferred and must not be mixed into this PR:

### Staging TLS fallback seam

The fallback staging vhost in `deploy/Caddyfile.production` remains a tracked
temporary seam. It is already recorded in the backlog:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-staging-tls-fallback-seam-after-full-staging-readiness`

PR-2 may document this seam, but must not broaden into removing it.

### Release gate / CD environment posture

`WEB_IOS_RELEASE_READY`, staging deploy enablement, and adjacent GitHub
environment policy remain separate release-ops concerns. They are not required
to land the shell diagnosis and routing contract.

### Broader production topology redesign

Do not replace the baked-shell Caddy image with:

- shared `frontend_dist` runtime volumes
- `/app/frontend/dist` root assumptions
- backend/frontend service renaming or CI redesign

unless hard deploy evidence proves the current model is wrong.

## Canonical Acceptance Checks

The PR-2 acceptance contract is:

1. `BASE_URL=https://$PRODUCTION_DOMAIN bash scripts/diagnose_web.sh`
2. `docker compose -f deploy/docker-compose.production.yaml build caddy`
3. Caddy config validation remains green
4. Repo-side tests cover the diagnosis/redeploy contract deterministically

Expected diagnosis outcomes:

- `GET /` -> SPA shell (`200`, `text/html`)
- `GET /bmi`, `/profile`, `/plate`, `/progress` -> SPA shell (`200`)
- `GET /health` and `GET /openapi.json` -> backend JSON surface
- `GET /plan` -> not SPA shell
- `/ws` upgrade probe -> not SPA shell

## File Set For This Lane

- `deploy/Caddyfile.production`
- `deploy/docker-compose.production.yaml`
- `frontend/Dockerfile.caddy-spa`
- `scripts/redeploy_caddy.sh`
- `scripts/diagnose_web.sh`
- `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md`
- `deploy/PRODUCTION.md`
- `deploy/WORKFLOW.md`
- `tests/test_deploy_contract_scripts.py`

## Decision Log

| Decision | Why |
|---------|-----|
| Preserve `/srv/frontend` as canonical shell root | It is already the consistent runtime truth across Caddy, compose, and the frontend Caddy image |
| Keep `try_files {path} /index.html` model | This already encodes the desired SPA deep-route behavior |
| Add diagnosis script instead of re-architecting deploy | The main missing capability was deterministic operator evidence, not a new topology |
| Keep staging/CD gate issues out of scope | They are separate seams and already backlog/governance tracked |

## Next Actions

1. Finish repo-side deterministic tests for the diagnosis/redeploy contract.
2. Run targeted script/deploy tests locally.
3. Run `pre-commit run --all-files`.
4. Run `make verify`.
5. Open PR-2 and continue the canonical post-open review loop.
