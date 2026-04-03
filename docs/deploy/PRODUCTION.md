# Production Setup Guide (Redirect)

This document is retained only as a compatibility stub.

## Canonical Source

Use `deploy/PRODUCTION.md` for the live production contract.

That file is the source of truth for:

- production server bootstrap
- `PROD_DEPLOY_MODE`, `WEB_IOS_RELEASE_READY`, and `PRODUCTION_ENV_READY`
- ownership of `/srv/pulseplate-production/.env`
- compose/Caddy expectations
- post-merge release procedure

## Important

Do not follow older setup examples that may still appear in historical discussions or cached copies of this file.

In particular:

- GitHub Actions does **not** create `/srv/pulseplate-production/.env`.
- `/srv/pulseplate-production/.env` is a server-local bootstrap artifact created on the host by the infra/release owner.
- Canonical production uses the current contract documented in `deploy/PRODUCTION.md`, not legacy snippets that may reference outdated compose, Caddy, or database topology.

## Next Step

Open `deploy/PRODUCTION.md` and follow that document only.
