# ADR: Docker Compose v2 Command-Surface Seam (2026-03-09)

- Status: Accepted (temporary seam)
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-compose-v2-migration`

## Context

The repo is in a mixed state: new docs prefer `docker compose`, while some
active command surfaces still use `docker-compose`. Operator guidance is only
truthful if this mixed state is documented as transitional.

## Decision

Treat remaining `docker-compose` usage as an explicit temporary seam. New or
edited commands should prefer `docker compose`, while repo docs link the
migration ledger item and this ADR until the command surface is fully
consolidated.

## Exit criteria

Retire this seam only when all are true:

1. Makefile targets use `docker compose`.
2. Active runbooks and operator docs no longer present `docker-compose` as the
   target state.
3. Transitional wording can be removed from `AGENTS.md` and
   `docs/runbooks/ENGINEER_QUICKPATH.md`.
4. Grep-based verification for lingering `docker-compose` usage is documented or
   automated.

## Consequences

- Positive: docs stop pretending the migration is already complete.
- Positive: operators get one explicit migration source of truth.
- Negative: temporary dual-command awareness remains until the follow-up lands.
