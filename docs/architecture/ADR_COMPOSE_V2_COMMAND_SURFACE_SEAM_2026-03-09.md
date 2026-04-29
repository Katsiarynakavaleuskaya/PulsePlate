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

1. Makefile targets use `docker compose`; evidence:
   `Makefile:33`, `Makefile:36`, `Makefile:39`, `Makefile:42`,
   `Makefile:52`, `Makefile:55`.
2. Active runbooks and operator docs no longer present legacy Compose v1 syntax
   as the target state; evidence: `scripts/QUICK_DIAGNOSTIC.md:76`,
   `scripts/QUICK_FIX_PRODUCTION.sh:47`,
   `scripts/diagnose_production.sh:46`.
3. Transitional wording is removed from `AGENTS.md` and
   `docs/runbooks/ENGINEER_QUICKPATH.md`; evidence: `AGENTS.md:1163`,
   `docs/runbooks/ENGINEER_QUICKPATH.md:74`.
4. Grep-based verification for lingering legacy command syntax is automated;
   evidence: `tests/test_repo_policy_guards.py:341`.

## Consequences

- Positive: operators get one active command surface.
- Positive: automated policy guards can distinguish command syntax from compose
  file names.
- Negative: hosts that only have the legacy standalone Compose v1 binary must
  install the Docker Compose v2 plugin before using active repo commands.
