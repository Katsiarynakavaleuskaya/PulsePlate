# PR 1271 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- Internal post-open review lane completed on `28 марта 2026 года`:
  `qa-engineer-agent (Linnaeus) -> bug-hunter (Faraday)`.
- `qa-engineer-agent`: backup/restore helpers now honor non-default compose files via
  `PROJECT_DIR` + `COMPOSE_FILE` -> `0a3dc812`
  Evidence: `scripts/ops/postgres_backup.sh`, `scripts/ops/postgres_restore.sh`,
  `tests/test_deploy_contract_scripts.py`
- `qa-engineer-agent` + `bug-hunter`: production/staging deploy flow now enforces
  `postgres -> backup -> app -> migrations -> caddy -> /ready` instead of exposing
  traffic before migrations -> `0a3dc812`
  Evidence: `scripts/deploy.sh`, `scripts/deploy_production.sh`,
  `tests/test_deploy_contract_scripts.py`
- `qa-engineer-agent` + `bug-hunter`: production runbook no longer points operators
  at staging-only `deploy.sh` and now documents `deploy_production.sh` with the
  Postgres-first contract -> `0a3dc812`
  Evidence: `docs/deploy/PRODUCTION.md`

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
