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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#pullrequestreview-4062157556 -> ccfb52627b02d611616c6a7cdb0bf2effa530a6b
  Evidence: same uvicorn/Caddy + restore/docs fixes as inline threads (Sourcery aggregate review).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#pullrequestreview-4062193213 -> ccfb52627b02d611616c6a7cdb0bf2effa530a6b
  Evidence: same as above (Cubic aggregate review).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#pullrequestreview-4062195935 -> ccfb52627b02d611616c6a7cdb0bf2effa530a6b
  Evidence: same as above (CodeRabbit aggregate review).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#discussion_r3039842094 -> 3e229558ee6e79bed1e76114b949006a17d9894d
  Evidence: same self-hosted compose + droplet runbook scope as prior threads (CodeRabbit follow-up).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#pullrequestreview-4062421496 -> 3e229558ee6e79bed1e76114b949006a17d9894d
  Evidence: same as above (CodeRabbit aggregate review, round 2).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#discussion_r3039852130 -> 3e229558ee6e79bed1e76114b949006a17d9894d
  Evidence: same as above (Cubic follow-up).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1359#pullrequestreview-4062432851 -> 3e229558ee6e79bed1e76114b949006a17d9894d
  Evidence: same as above (Cubic aggregate review, round 2).

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green locally

<!-- markdownlint-enable MD034 -->
