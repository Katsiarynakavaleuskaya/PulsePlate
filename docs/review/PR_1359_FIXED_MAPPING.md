<!-- markdownlint-disable MD034 -->
# PR 1359 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: **FIXED** (evidence in `deploy/docker-compose.production.selfhosted.yaml`, `docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#discussion_r3039605502 -> ccfb52627b02d611616c6a7cdb0bf2effa530a6b
  Evidence: `deploy/docker-compose.production.selfhosted.yaml:56` (`--forwarded-allow-ips="caddy"`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#discussion_r3039634911 -> ccfb52627b02d611616c6a7cdb0bf2effa530a6b
  Evidence: same as above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#discussion_r3039614630 -> ccfb52627b02d611616c6a7cdb0bf2effa530a6b
  Evidence: `docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md` (restore example: `PROJECT_DIR` / `COMPOSE_FILE`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#discussion_r3039634907 -> ccfb52627b02d611616c6a7cdb0bf2effa530a6b
  Evidence: `deploy/docker-compose.production.selfhosted.yaml:49` (`DATABASE_URL` from `POSTGRES_*`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#discussion_r3039637437 -> ccfb52627b02d611616c6a7cdb0bf2effa530a6b
  Evidence: `deploy/docker-compose.production.selfhosted.yaml:82` (`PRODUCTION_DOMAIN` `:?`).

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green locally

<!-- markdownlint-enable MD034 -->
