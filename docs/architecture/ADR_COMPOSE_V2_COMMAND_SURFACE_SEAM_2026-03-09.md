# ADR: Docker Compose v2 Command-Surface Migration (2026-03-09)

- Status: Retired
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-compose-v2-migration`

## Context

The repo previously carried a mixed command surface: new docs preferred
`docker compose`, while some active commands still used the legacy hyphenated
Compose v1 CLI. Operator guidance is clearest when active command examples and
Make targets use one canonical Compose command.

## Decision

Use `docker compose` v2 for active repo command surfaces. Compose file names
such as `docker-compose.production.yaml` remain unchanged because they are
artifact names, not command syntax.

## Closure criteria

The seam is retired when all are true:

1. Makefile targets use `docker compose`.
2. Active runbooks and operator docs no longer present legacy Compose v1 syntax
   as the target state.
3. Transitional wording is removed from `AGENTS.md` and
   `docs/runbooks/ENGINEER_QUICKPATH.md`.
4. Grep-based verification for lingering legacy command syntax is automated.

## Consequences

- Positive: operators get one active command surface.
- Positive: automated policy guards can distinguish command syntax from compose
  file names.
- Negative: hosts that only have the legacy standalone Compose v1 binary must
  install the Docker Compose v2 plugin before using active repo commands.
