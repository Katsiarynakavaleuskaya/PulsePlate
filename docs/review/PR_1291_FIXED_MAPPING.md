# PR 1291 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

### FIXED
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1291#discussion_r3014934202` -> `1c20cb1a`
  - Evidence: `tests/test_app_lifespan_additional.py`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1291#discussion_r3014943491` -> `1c20cb1a`
  - Evidence: `.env.example`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1291#discussion_r3014961226` -> `1c20cb1a`
  - Evidence: `.env.example`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1291#discussion_r3014961259` -> `1c20cb1a`
  - Evidence: `docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1291#discussion_r3014961264` -> `1c20cb1a`
  - Evidence: `tests/test_app_lifespan_additional.py`

### DEFERRED
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1291#discussion_r3015018643`
  - Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-execution-doc-sot-reconciliation`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1291#discussion_r3015051066`
  - Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-execution-doc-sot-reconciliation`

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- PR-1 lane: canonical production/staging database foundation requires explicit Postgres `DATABASE_URL`; SQLite remains local/dev/test only.
