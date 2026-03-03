# ADR: Staging TLS Fallback Seam (2026-03-04)

- Status: Accepted (temporary seam)
- Date: 2026-03-04
- Owner: @katsiaryna_kavaleuskaya

## Context

In build-only mode (`WEB_IOS_RELEASE_READY != true`) staging SSH deploy is intentionally skipped.
If `/srv/pulseplate-staging` stack is not running, the public staging hostname can fail TLS handshake.

## Decision

Production Caddy keeps a temporary fallback vhost for `STAGING_FALLBACK_DOMAIN`
(default `pulseplate-staging.duckdns.org`) and proxies to the running app container.

Implementation anchors:
- `deploy/Caddyfile.production`
- `deploy/docker-compose.production.yaml`
- `docs/deploy/STAGING.md`

## Consequences

Positive:
- Staging public URL keeps valid HTTPS transport in build-only periods.

Trade-offs:
- This is a transport seam, not a true staging runtime deploy.

## Exit Criteria

Remove fallback seam when ALL are true:
1. `WEB_IOS_RELEASE_READY=true` and staging SSH deploy is continuously enabled in CI.
2. `/srv/pulseplate-staging` compose stack is managed as primary staging runtime.
3. Staging healthcheck is served by staging stack directly (no production fallback dependency).

## Follow-up Tracking

Canonical backlog item:
- `docs/roadmap/BACKLOG_LEDGER.md` → `P1: Remove staging TLS fallback seam after full staging readiness`
